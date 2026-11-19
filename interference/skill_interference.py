#!/usr/bin/env python3
"""skill-interference 1.0.0 (2026-11-19): does a new skill break the routing of the old ones?

Second module of skill-budget-meter. When a skill library grows, a new skill that looks like an old one can take
its place in the router's choice (SUBSTITUTION), and generic or duplicate skills can fill the few slots the router
picks from (CROWDING), even though neither the old skills nor the router changed.

IMPORTANT: every measure here is LEXICAL (TF-IDF cosine and BM25 over words). The probe is NOT Claude's skill
router, which is a language model reading names and descriptions. Use the numbers to compare two versions of your
own metadata (before and after a change), never as a certificate that routing works.

Method adapted from Zhang et al., "SKILL++: Towards Lifelong Agents via Routing-Aware Skill Refinement",
arXiv:2611.00544 (31 Oct 2026): the router stays frozen and only the metadata of the incoming skill is refined,
with three components:
  1) a description differentiated from the most similar existing skill g_t (Eq. 7);
  2) an exclusion clause ("Not for: ...") towards up to 3 neighbours G_t, chosen by the fused rank of three
     measures (Eq. 8, 14);
  3) a clarified name when it contains the "head" (first word) of an earlier skill's name (Eq. 9).
Adaptation: lexical measures replace the paper's embeddings.
  s1 = metadata of the skill vs typical queries (or, without queries, the body) of the neighbour;
  s2 = queries (or body) vs queries (or body);   s3 = metadata vs metadata (name + description).
No code from the paper is included.

Usage (python3 on macOS and Linux, py on Windows):
  python skill_interference.py [--library DIR]... [--cases FILE.jsonl] [--out REPORT.md] [--json]
  python skill_interference.py --new SKILL_DIR_OR_SKILL.md [--prompt-out FILE.txt] [--cap N] [--library DIR]...
  python skill_interference.py --try-descriptions FILE.json [--library DIR]... [--cases FILE.jsonl]
  python skill_interference.py --selftest
  --library DIR  folder searched recursively for SKILL.md files (repeatable). Default: <config>/skills, where
                 <config> is $CLAUDE_CONFIG_DIR or ~/.claude. The plugin prefix comes from the nearest
                 .claude-plugin/plugin.json above each skill, if any.
  --cases FILE   JSONL, one {"query": "...", "skills": ["name", ...]} per line (short name or plugin:name; the
                 keys "domanda"/"skill" are accepted too): runs the lexical probe (BM25 over name + description)
                 and reports Top@1, FC@5 (all expected skills in the top 5) and Recall@5, classifying each miss as
                 substitution or crowding.
  --new X        insertion mode (Algorithm 1 of the paper): skill X against the library. With --prompt-out it
                 writes one prompt asking a model for a refined name, description and exclusion clause. It never
                 rewrites a skill: it proposes.
  --cap N        characters for the refined description plus exclusions in that prompt (default 298, the
                 paper's metadata length).
  --try-descriptions F  JSON {short name: description}: measure alternative descriptions in memory; no skill
                 file is touched.
Thresholds [adaptation, tune them on your own library]: a pair is at risk if s3 >= 0.30 and neither skill has an
exclusion clause. Exclusion clauses are recognised in English and Italian. Lexical measures ignore sentences that
start with "Not", "Never", "Does not", "Non", "Mai": TF-IDF and BM25 cannot read negation.
Exit codes: 0 done · 1 (only with --new) risk found: shared name head, or a close neighbour and no exclusion ·
            2 usage error or fewer than 2 skills found.
Read-only (except --out and --prompt-out, written atomically and refused inside a library); no network;
Python 3.8+ standard library only.

Copyright (c) 2026 Gianluca Vega
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

VERSION = "1.0.0"
S3_THRESHOLD = 0.30
TOP_G = 3
K = 5
LMAX = 298  # characters of refined metadata (paper, App. A)
EXCLUSION = re.compile(r"\bnot for\b|does not cover|do not use for|not covered|\bexcept\b|≠|"
                       r"non cop|non per\b|non è per|non serve per|mai per|esclus", re.I)
NEGATION = re.compile(r"\b(?:Not|Never|Does not|Do not|Non|Mai)\b[^.]*\.\s*", re.I)
STOPWORDS = set("""the and for with from into this that use when your you are not all any can its only also
then than them they will what which who how about over under more most such each other some
alla alle allo agli anche come con cosa dal dalla dei del della delle dello degli dopo fra gli una uno per più
sono sul sulla tra che chi non nel nella nelle negli sempre ogni prima solo questa questo quando dove""".split())
SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def words(text):
    return [w for w in re.findall(r"[a-zà-öø-ÿ0-9]{3,}", text.lower()) if w not in STOPWORDS]


def head(name):
    """h(n): first lower-case segment of the short name (split on space, hyphen, dash, underscore); empty if <= 3 chars."""
    short = name.split(":")[-1].strip()
    seg = re.split(r"[\s\-—_]+", short.lower())[0] if short else ""
    return seg if len(seg) > 3 else ""


def frontmatter(text):
    """Minimal YAML front matter: top-level 'key: value' lines between the leading '---' fences."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fields = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            fields[m.group(1)] = v
    return fields, text[end + 4:]


def plugin_name(skill_dir, library):
    """Name in the nearest .claude-plugin/plugin.json between the skill folder and the library root."""
    root = Path(library).resolve()
    for d in [skill_dir, *skill_dir.parents]:
        pj = d / ".claude-plugin" / "plugin.json"
        if pj.is_file():
            try:
                return json.loads(pj.read_text(encoding="utf-8")).get("name", "")
            except (OSError, ValueError):
                return ""
        if d == root:
            break
    return ""


def read_skill(skill_dir, plugin=""):
    md = skill_dir / "SKILL.md"
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fields, body = frontmatter(text.replace("\r\n", "\n"))
    name = fields.get("name") or skill_dir.name
    return {"name": name, "plugin": plugin, "full": f"{plugin}:{name}" if plugin else name,
            "description": fields.get("description", ""), "body": body[:2600], "path": str(md)}


def load(libraries):
    """One entry per short name: the same skill seen twice (for example a plugin copy and a synced copy) is ONE
    skill, not a pair to separate; the copy with a plugin name wins."""
    by_name, dupes = {}, []
    for lib in libraries:
        lib = Path(lib)
        mds = [lib] if lib.is_file() and lib.name == "SKILL.md" else sorted(lib.rglob("SKILL.md"))
        for md in mds:
            if any(p in SKIP_DIRS for p in md.parts):
                continue
            s = read_skill(md.parent, plugin_name(md.parent, lib if lib.is_dir() else md.parent))
            if not s:
                continue
            first = by_name.get(s["name"])
            if first is None:
                by_name[s["name"]] = s
            else:
                dupes.append((s["name"], first["path"], s["path"]))
                if not first["plugin"] and s["plugin"]:
                    by_name[s["name"]] = s
    return list(by_name.values()), dupes


class Tfidf:
    def __init__(self, docs):
        self.n = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(words(d)))
        self.idf = {w: math.log((1 + self.n) / (1 + c)) + 1 for w, c in df.items()}

    def vector(self, text):
        tf = Counter(words(text))
        v = {w: c * self.idf.get(w, math.log(1 + self.n) + 1) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def meta(s):
    """Name + description for the LEXICAL measures, without exclusion sentences ("Not for invoices" would add the
    word "invoices"); exclusions are for the LLM router, not for the probe [adaptation]."""
    return f"{s['name']}. {NEGATION.sub('', s['description'])[:300]}"


def prepare(skills):
    tf = Tfidf([meta(s) + " " + s["body"] for s in skills])
    for s in skills:
        s["v_meta"] = tf.vector(meta(s))
        s["v_q"] = [tf.vector(s["body"])]
    return tf


def measures(t, s):
    s1 = max(cosine(q, t["v_meta"]) for q in s["v_q"])
    s2 = max(cosine(q, p) for q in s["v_q"] for p in t["v_q"])
    s3 = cosine(s["v_meta"], t["v_meta"])
    return s1, s2, s3


def neighbours(t, skills):
    """g_t (Eq. 7) and G_t (Eq. 8, 14): fused rank = (min of the ranks, sum of the ranks), 1 = most similar."""
    others = [s for s in skills if s is not t]
    if not others:
        return None, []
    m = {s["full"]: measures(t, s) for s in others}
    ranks = {s["full"]: [] for s in others}
    for k in range(3):
        for i, s in enumerate(sorted(others, key=lambda s: -m[s["full"]][k]), 1):
            ranks[s["full"]].append(i)
    fused = sorted(others, key=lambda s: (min(ranks[s["full"]]), sum(ranks[s["full"]])))
    g = max(others, key=lambda s: m[s["full"]][2])
    return (g, m[g["full"]]), [(s, m[s["full"]], min(ranks[s["full"]])) for s in fused[:TOP_G]]


def has_exclusion(s):
    return bool(EXCLUSION.search(s["description"]))


def head_conflicts(t, others):
    return [s for s in others if head(s["name"]) and head(s["name"]) in t["name"].lower() and s["name"] != t["name"]]


def bm25(skills, query, k1=1.2, b=0.75):
    docs = [words(meta(s)) for s in skills]
    avg = sum(map(len, docs)) / max(1, len(docs))
    df = Counter(w for d in docs for w in set(d))
    n, q, scores = len(docs), words(query), []
    for s, d in zip(skills, docs):
        tf, p = Counter(d), 0.0
        for w in q:
            if tf[w]:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                p += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
        scores.append((p, s))
    return [s for p, s in sorted(scores, key=lambda x: -x[0])[:K] if p > 0]


def find(skills, name):
    return next((s for s in skills if name in (s["full"], s["name"])), None)


def probe(skills, cases):
    lines, full_hits, recall, subst, crowd, nomatch, top1 = [], 0, 0.0, 0, 0, 0, 0
    for c in cases:
        picked = bm25(skills, c["query"])
        names = {s["full"] for s in picked}
        wanted = [find(skills, n) for n in c["skills"]]
        if picked and any(w is not None and w["full"] == picked[0]["full"] for w in wanted):
            top1 += 1
        elif picked:
            lines.append(f"- @1 \"{c['query']}\" -> first {picked[0]['name']} instead of {', '.join(c['skills'])}")
        missing = [n for n, s in zip(c["skills"], wanted) if s is None or s["full"] not in names]
        recall += 1 - len(missing) / max(1, len(c["skills"]))
        full_hits += not missing
        for n in missing:
            s = find(skills, n)
            _, gt = neighbours(s, skills) if s else (None, [])
            near = {x[0]["full"] for x in gt}
            if not picked:
                nomatch += 1
                kind = "no word in common with any skill"
            elif near & names:
                subst += 1
                kind = "substitution: " + ", ".join(sorted(near & names))
            else:
                crowd += 1
                kind = "crowding"
            lines.append(f"- \"{c['query']}\" -> missing {n} ({kind}); picked: "
                         f"{', '.join(s['name'] for s in picked) or '-'}")
    tot = max(1, len(cases))
    return {"cases": len(cases), "Top@1": round(100 * top1 / tot, 1), "FC@5": round(100 * full_hits / tot, 1),
            "Recall@5": round(100 * recall / tot, 1), "substitutions": subst, "crowding": crowd, "no_match": nomatch, "detail": lines}


def read_cases(path):
    cases = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        q, sk = d.get("query", d.get("domanda")), d.get("skills", d.get("skill"))
        if not q or not isinstance(sk, list):
            raise ValueError(f"line {i}: needs \"query\" and \"skills\" (a list)")
        cases.append({"query": q, "skills": sk})
    return cases


def write_atomic(path, text, libraries):
    p = Path(path).resolve()
    for lib in libraries:
        try:
            p.relative_to(Path(lib).resolve())
        except ValueError:
            continue
        raise SystemExit(f"ERROR: {p} is inside the library {lib}: refused")
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, p)


def audit(skills, cases, dupes):
    out, at_risk, heads = [], [], []
    for t in skills:
        (g, mg), gt = neighbours(t, skills)
        if mg[2] >= S3_THRESHOLD and not (has_exclusion(t) or has_exclusion(g)):
            at_risk.append((round(mg[2], 2), t, g))
        heads += [(t, s) for s in head_conflicts(t, [x[0] for x in gt])]
        t["_gt"] = gt
    pairs, seen = [], set()
    for v, t, g in sorted(at_risk, key=lambda x: (-x[0], x[1]["full"])):
        key = frozenset((t["full"], g["full"]))
        if key not in seen:
            seen.add(key)
            pairs.append((v, t, g))
    out.append(f"# Skill routing interference (SKILL++ method) - skill_interference.py {VERSION}\n")
    out.append(f"Skills read: {len(skills)} · pairs at risk (s3 >= {S3_THRESHOLD}, no exclusion): {len(pairs)} · "
               f"shared name heads among neighbours: {len(heads)} · skills with an exclusion clause: "
               f"{sum(has_exclusion(s) for s in skills)}\n")
    out.append("## Pairs at risk of SUBSTITUTION (suggestion: differentiate the newer description and add \"Not for ...\")\n")
    out += [f"- {v:.2f} · {t['full']} <-> {g['full']}" for v, t, g in pairs] or ["- none"]
    out.append("\n## Shared name heads among neighbours (suggestion: qualify the newer name)\n")
    out += [f"- {t['full']} contains the head \"{head(s['name'])}\" of {s['full']}" for t, s in heads] or ["- none"]
    out.append(f"\n## Copies of the same skill in several places (counted once): {len(dupes)}\n")
    out += [f"- {n}: {a} · {b}" for n, a, b in dupes[:40]] or ["- none"]
    out.append("\n## Neighbours per skill (G_t, fused rank; s1/s2/s3)\n")
    for t in sorted(skills, key=lambda s: s["full"]):
        v = "; ".join(f"{s['name']} ({m[0]:.2f}/{m[1]:.2f}/{m[2]:.2f})" for s, m, _ in t["_gt"])
        out.append(f"- {t['full']}{' [exclusion]' if has_exclusion(t) else ''}: {v}")
    res = None
    if cases is not None:
        res = probe(skills, cases)
        out.append(f"\n## Lexical probe (BM25 over name + description, K={K}) - NOT Claude's router\n")
        out.append(f"Cases {res['cases']} · Top@1 {res['Top@1']} % · FC@5 {res['FC@5']} % · Recall@5 {res['Recall@5']} % · "
                   f"misses: substitution {res['substitutions']}, crowding {res['crowding']}, no match {res['no_match']}\n")
        out += res["detail"]
    return "\n".join(out) + "\n", pairs, heads, res


def refine_prompt(t, g, gt, cap=LMAX):
    """The three SKILL++ tasks (description, exclusions, name) asked as ONE deliverable: a full metadata proposal."""
    near = "\n".join(f"- {s['name']}: {s['description'][:180]}" for s, _, _ in gt)
    return (f"You curate a library of agent skills. A NEW skill is entering a library where a router picks skills by "
            f"reading only their name and description.\n\nNEW SKILL\nname: {t['name']}\ncurrent description: "
            f"{t['description']}\nbody (excerpt):\n{t['body'][:1600]}\n\nMOST SIMILAR EXISTING SKILL\nname: {g['name']}\n"
            f"description: {g['description']}\nbody (excerpt):\n{g['body'][:1200]}\n\nOTHER NEIGHBOURS\n{near}\n\n"
            f"DELIVERABLE (just one): a metadata proposal in three lines:\n"
            f"NAME: the current name or, only if it contains the first word of a neighbour's name, a kebab-case name of "
            f"4-60 characters qualified by the topic or kind of guidance in the body.\n"
            f"DESCRIPTION: one line, no versions or dates, only capabilities present in the body, starting with what the "
            f"existing skill does not offer, without naming or alluding to it.\n"
            f"NOT FOR: one short lower-case phrase per neighbour, saying the work of that neighbour this skill does not "
            f"do, without naming it.\nCAP: DESCRIPTION + \" Not for: \" + phrases within {cap} characters in total; if "
            f"they do not fit, drop phrases from the end, never the description. Last line: TOTAL: <number of characters>.")


def selftest():
    a = {"name": "paper-writing", "plugin": "", "full": "paper-writing", "description": "Draft research manuscripts.",
         "body": "write AI ML papers related work latex", "path": "a"}
    b = dict(a, full="paper-writing-bio", name="paper-writing-bio", body="write biology wet lab papers", path="b")
    c = {"name": "latex-polisher", "plugin": "", "full": "latex-polisher", "description": "Polish LaTeX tables.",
         "body": "fix latex tables and figures", "path": "c"}
    sk = [a, b, c]
    prepare(sk)
    (g, _), _ = neighbours(b, sk)
    checks = [("most similar neighbour", g["name"] == "paper-writing"),
              ("name head", head("paper-writing") == "paper" and head("abc-pec") == ""),
              ("head conflict", bool(head_conflicts(b, [a]))),
              ("exclusion recognised", bool(EXCLUSION.search("Does X. Not for Y.")) and not EXCLUSION.search("Does X.")),
              ("negation ignored by the probe", "invoices" not in meta({"name": "x", "description": "Does X. Not for invoices."})),
              ("probe FC@5", probe(sk, [{"query": "polish latex tables", "skills": ["latex-polisher"]}])["FC@5"] == 100.0)]
    for n, ok in checks:
        print(("OK " if ok else "KO ") + n)
    print(f"Self-test: {sum(ok for _, ok in checks)}/{len(checks)}")
    return 0 if all(ok for _, ok in checks) else 1


def default_libraries():
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return [str(config / "skills")]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill_interference.py",
                                 description="Skill routing interference (SKILL++ method), lexical, read-only.")
    ap.add_argument("--library", "--libreria", action="append", metavar="DIR")
    ap.add_argument("--cases", "--casi", metavar="FILE")
    ap.add_argument("--out", "--uscita", metavar="FILE")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--new", "--nuova", metavar="SKILL")
    ap.add_argument("--prompt-out", metavar="FILE")
    ap.add_argument("--cap", "--tetto", type=int, default=LMAX)
    ap.add_argument("--try-descriptions", metavar="FILE")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=f"skill-interference {VERSION}")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    libraries = a.library or default_libraries()
    missing = [x for x in libraries if not Path(x).exists()]
    if missing:
        print("ERROR: library not found:", ", ".join(missing))
        return 2
    skills, dupes = load(libraries)
    if a.try_descriptions:
        try:
            alt = json.loads(Path(a.try_descriptions).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            print("ERROR try-descriptions:", e)
            return 2
        for s in skills:
            if s["name"] in alt:
                print(f"TRY {s['name']}: {len(s['description'])} -> {len(alt[s['name']])} characters")
                s["description"] = alt.pop(s["name"])
        if alt:
            print("ERROR: skills not found:", ", ".join(alt))
            return 2
    new = None
    if a.new:
        p = Path(a.new)
        d = p.parent if p.name == "SKILL.md" else p
        new = read_skill(d, plugin_name(d, d.parent.parent))
        if not new:
            print("ERROR: SKILL.md not found in", d)
            return 2
        skills = [s for s in skills if Path(s["path"]).resolve() != (d / "SKILL.md").resolve()] + [new]
    if len(skills) < 2:
        print("ERROR: fewer than 2 skills found in", ", ".join(libraries))
        return 2
    try:
        cases = read_cases(a.cases) if a.cases else None
    except (OSError, ValueError) as e:
        print("ERROR cases:", e)
        return 2
    prepare(skills)
    if new:
        (g, m), gt = neighbours(new, skills)
        conf = head_conflicts(new, [s for s in skills if s is not new])
        risk = (m[2] >= S3_THRESHOLD and not has_exclusion(new)) or bool(conf)
        print(f"new skill: {new['full']} · most similar: {g['full']} (s3 {m[2]:.2f})")
        for s, mm, r in gt:
            print(f"  neighbour: {s['full']} rank {r} · s1 {mm[0]:.2f} s2 {mm[1]:.2f} s3 {mm[2]:.2f}")
        for s in conf:
            print(f"  NAME HEAD shared with {s['full']} (\"{head(s['name'])}\")")
        print(f"  exclusion clause: {'yes' if has_exclusion(new) else 'NO'} · metadata length "
              f"{len(new['name']) + len(new['description'])}/{LMAX}")
        if a.prompt_out:
            write_atomic(a.prompt_out, refine_prompt(new, g, gt, a.cap), libraries)
            print("prompt written:", a.prompt_out)
        print(f"Result: {'RISK' if risk else 'OK'} · {len(skills) - 1} skills in the library")
        return 1 if risk else 0
    text, pairs, heads, res = audit(skills, cases, dupes)
    if a.out:
        write_atomic(a.out, text, libraries)
    if a.json:
        print(json.dumps({"skills": len(skills), "pairs": [[v, t["full"], g["full"]] for v, t, g in pairs],
                          "heads": [[t["full"], s["full"]] for t, s in heads],
                          "probe": {k: v for k, v in (res or {}).items() if k != "detail"}}, ensure_ascii=False))
        return 0
    print("\n".join(text.splitlines()[:3]))
    for v, t, g in pairs[:15]:
        print(f"  {v:.2f} {t['full']} <-> {g['full']}")
    if res:
        print("\n".join(res["detail"][:15]))
    probe_txt = f" · Top@1 {res['Top@1']} % · FC@5 {res['FC@5']} % on {res['cases']} cases" if res else ""
    print(f"Result: {len(skills)} skills · {len(pairs)} pairs at risk · {len(heads)} shared heads{probe_txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
