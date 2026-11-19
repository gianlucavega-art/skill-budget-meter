# skill-interference

Does a new skill break the routing of the ones you already have? This script compares the names and
descriptions of your Claude Code skills, finds the pairs that look alike, and tells you before you install a
new skill whether it is likely to take an old one's place.

Second module of **skill-budget-meter**. One Python file · standard library only · read-only · no network.

> **Read this first: the probe is not Claude's router.** Claude picks a skill with a language model that reads
> names and descriptions. This script measures words (TF-IDF cosine and BM25). Its numbers are useful to
> compare two versions of *your own* metadata, before and after a change; they do not certify that Claude
> will pick the right skill. Low lexical overlap can still be confused by a model, and high overlap can be
> told apart by one.

> **Independent project, not affiliated with Anthropic.** The method is adapted from Zhang et al.,
> *SKILL++: Towards Lifelong Agents via Routing-Aware Skill Refinement*,
> [arXiv:2611.00544](https://arxiv.org/abs/2611.00544) (31 October 2026). No code from the paper is included;
> the lexical measures replace the paper's embeddings, and the thresholds are the author's own.

[Leggimi in italiano](README.it.md)

## What it measures

The paper names two ways a growing skill library fails, even when neither the old skills nor the router change:

- **Substitution**: a new skill similar to an old one takes the old one's place in the router's choice.
- **Crowding**: generic or duplicate skills fill the few slots the router picks from.

For every skill the script finds its closest neighbours with three measures, each between 0 and 1:

| | Compares |
|---|---|
| `s1` | the skill's name + description with the neighbour's body |
| `s2` | body with body |
| `s3` | name + description with name + description |

The neighbours are ranked on each measure and the ranks are fused (best rank first, then the sum), as in
Eq. 8 and 14 of the paper. It then reports:

- **pairs at risk of substitution**: `s3` ≥ 0.30 and neither skill has an exclusion clause
  ("Not for …", "Does not cover …"; Italian "Non per …", "Non copre …" are recognised too);
- **shared name heads**: a name that contains the first word (over 3 letters) of a neighbour's name, such as
  `invoice-audit` next to `invoice-checker` (Eq. 9);
- **copies** of the same skill in several folders (counted once);
- with `--cases`, a **lexical probe**: BM25 over name + description picks the top 5 skills for each test
  query, and the script reports Top@1, FC@5 (every expected skill in the top 5) and Recall@5, classifying
  each miss as substitution (a neighbour took the slot), crowding (other skills did) or no match.

Sentences that start with *Not*, *Never*, *Does not* (or *Non*, *Mai*) are left out of the lexical measures:
word counts cannot read negation, so "Not for invoices" would otherwise make a skill look *more* like an
invoice skill. Exclusion clauses are for the language-model router, not for the probe.

## Quick start

Requires Python 3.8 or later. Download `skill_interference.py`, then:

```
python skill_interference.py
```

reads every `SKILL.md` under `<config>/skills` (`<config>` is `$CLAUDE_CONFIG_DIR`, or `~/.claude`). Add more
folders, such as a project's `.claude/skills` or a plugin folder, with `--library DIR` (repeatable). On macOS and
Linux use `python3`; on Windows you can also use `py`.

## Example (real output on the synthetic library in `esempio/`)

`esempio/library` holds four made-up skills: two invoice skills that overlap on purpose, a meeting-notes skill
and a travel planner with a "Not for" clause. `esempio/incoming/invoice-audit` is a skill about to be installed.

**Audit the library and run the probe:**

```
$ python skill_interference.py --library esempio/library --cases esempio/probe_cases.jsonl
# Skill routing interference (SKILL++ method) - skill_interference.py 1.0.0

Skills read: 4 · pairs at risk (s3 >= 0.3, no exclusion): 1 · shared name heads among neighbours: 2 · skills with an exclusion clause: 1
  0.64 invoice-checker <-> invoice-review
- "who has to do what after the call, and by when" -> missing meeting-notes (no word in common with any skill); picked: -
Result: 4 skills · 1 pairs at risk · 2 shared heads · Top@1 83.3 % · FC@5 83.3 % on 6 cases
```

The miss on the meeting query shows the limit stated above: a language model would map "who has to do what"
to action items; a word count cannot. Add `--out report.md` for the full report with every skill's neighbours.

**Check a skill before installing it:**

```
$ python skill_interference.py --library esempio/library --new esempio/incoming/invoice-audit
new skill: invoice-audit · most similar: invoice-checker (s3 0.20)
  neighbour: invoice-checker rank 1 · s1 0.07 s2 0.21 s3 0.20
  neighbour: invoice-review rank 1 · s1 0.11 s2 0.19 s3 0.18
  neighbour: meeting-notes rank 3 · s1 0.04 s2 0.06 s3 0.04
  NAME HEAD shared with invoice-checker ("invoice")
  NAME HEAD shared with invoice-review ("invoice")
  exclusion clause: NO · metadata length 137/298
Result: RISK · 4 skills in the library
```

Exit code 1: refine the name or the description before installing. With `--prompt-out prompt.txt` the script
also writes one prompt you can give to any model, asking for a refined name, a differentiated description and
a "Not for" clause within `--cap` characters (default 298, the paper's metadata length). It never edits a skill.

**Try a new description in memory, without touching any file:**

```
$ python skill_interference.py --library esempio/library --cases esempio/probe_cases.jsonl --try-descriptions esempio/try_descriptions.json
TRY invoice-review: 128 -> 165 characters
# Skill routing interference (SKILL++ method) - skill_interference.py 1.0.0

Skills read: 4 · pairs at risk (s3 >= 0.3, no exclusion): 0 · shared name heads among neighbours: 2 · skills with an exclusion clause: 2
- "who has to do what after the call, and by when" -> missing meeting-notes (no word in common with any skill); picked: -
Result: 4 skills · 0 pairs at risk · 2 shared heads · Top@1 83.3 % · FC@5 83.3 % on 6 cases
```

The pair at risk is gone and the probe did not get worse: that before-and-after comparison is what the script
is for.

## Options

| Option | Default | What it does |
|---|---|---|
| `--library` / `--libreria DIR` | `<config>/skills` | Folder searched for `SKILL.md` files (repeatable). The plugin prefix comes from the nearest `.claude-plugin/plugin.json` |
| `--cases` / `--casi FILE` | | JSONL probe cases, one `{"query": "...", "skills": ["name"]}` per line; `#` lines are comments |
| `--new` / `--nuova SKILL` | | Insertion mode: a skill folder or `SKILL.md` against the library |
| `--prompt-out FILE` | | With `--new`: write the refinement prompt |
| `--cap` / `--tetto N` | 298 | Character cap written into that prompt |
| `--try-descriptions FILE` | | JSON `{"short-name": "new description"}` measured in memory |
| `--out` / `--uscita FILE` | | Write the full Markdown report |
| `--json` | | Machine-readable summary |
| `--selftest` | | Six built-in checks on synthetic skills |
| `--version` | | Show the version |

`--out` and `--prompt-out` are written atomically and refused inside a library folder.

## Writing probe cases

- Write queries the way you actually ask, not with the skill's own words: a probe that copies the description
  only proves that BM25 can match words.
- Add a few queries for each pair at risk, one per side, and keep them: they are your regression set.
- Change one description at a time and rerun: a fix for one pair must not break another case.

## Limits

- Lexical only. Synonyms, paraphrases and negation are invisible to it (see the example above).
- The 0.30 threshold and the 298-character cap are starting points: tune them on your own library.
- Only the first 2,600 characters of each body and 300 of each description are read.
- The front matter parser reads simple `key: value` lines; multi-line YAML values are not supported.
- Tested on Windows 10 with Python 3.14; not yet tested on macOS or Linux.

## Privacy

It reads local `SKILL.md` files only and never uses the network. It writes only the files you name with
`--out` or `--prompt-out`. The output contains your skill names and, in the prompt, excerpts of their
descriptions and bodies: look at it before you share it.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done (audit, probe, `--try-descriptions`, `--selftest` passed); with `--new`, no risk found |
| 1 | With `--new`: risk found (shared name head, or `s3` ≥ 0.30 and no exclusion clause); a failed `--selftest` |
| 2 | Usage error, missing library or file, fewer than 2 skills |

## Credits

Method: Zhang et al., *SKILL++: Towards Lifelong Agents via Routing-Aware Skill Refinement*,
arXiv:2611.00544 (2026). The idea of substitution and crowding, the three refinement components and the fused
neighbour rank are theirs; the lexical adaptation, thresholds and any mistakes are the author's.

## License

MIT, © 2026 Gianluca Vega: see [LICENSE](LICENSE).

## Support the project

If this tool saved you time, you can support its development on Ko-fi:
[ko-fi.com/gianlucavega](https://ko-fi.com/gianlucavega). Thank you!

**Illustrated guide.** How to use this module and `skill_budget_meter.py` together, with copy-ready description templates and a pre-install checklist, is explained in a PDF guide (English + Italian, 12 €): [get the guide](https://buy.stripe.com/3cI7sNcuX1121ZyeRDawo00). The code stays free under the MIT licence.
