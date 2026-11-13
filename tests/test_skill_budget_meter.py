"""Tests for skill_budget_meter.py on synthetic transcripts (standard library only).

Run from the repository folder:   python -m unittest discover -s tests -v   (python3 on macOS and Linux)

Nothing here reads your real Claude folder: every test builds a fake Claude configuration in a temporary
directory and points the script at it with CLAUDE_CONFIG_DIR. Expected numbers are computed here, from the
fixture text, independently of the script's own functions.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True  # keep the repository free of __pycache__
SCRIPT = Path(__file__).resolve().parent.parent / "skill_budget_meter.py"
_SPEC = importlib.util.spec_from_file_location("skill_budget_meter", SCRIPT)
sbm = importlib.util.module_from_spec(_SPEC)
sys.modules["skill_budget_meter"] = sbm
_SPEC.loader.exec_module(sbm)

EMOJI = "\U0001F7E2"  # one character in Python, two UTF-16 units
BOM = chr(0xFEFF)  # byte order mark, written as chr() so that no editor can drop it unseen
T_OLD, T_NEW = "2026-11-10T09:00:00.000Z", "2026-11-13T10:00:00.000Z"
T_PARTIAL, T_SIDE = "2026-11-13T10:05:00.000Z", "2026-11-13T10:06:00.000Z"
MARKER = "Base directory for this skill: "

# The newest initial listing: every name below. The ones in SHOWN have their description; the others are hidden.
NAMES = ["my-plugin:report-writer", "pdf-tools:extract", "data-tools:extract", "team-notes", "docs-helper",
         "project-only", "multi-line", "other-plugin:slide-maker", "other-plugin:bullets", "classic-viewer",
         "ghost-plugin:phantom", "lure-plugin:sneaky", "deep-plugin:buried", "repo-skill"]
SHOWN = {
    "data-tools:extract": "Pull rows from spreadsheets.",
    "docs-helper": "Help with documents: drafts, edits and reviews " + EMOJI,
    "multi-line": "First line of a long description\nTRIGGER - read me first\nSKIP - when not needed",
    "other-plugin:bullets": "Line one\n- Not a skill name: a continuation line that starts with a dash",
}
FULL = {  # what the hidden skills' SKILL.md files (or an older listing) must give; "" = no usable source
    "my-plugin:report-writer": "Draft weekly reports.\nTrigger: report, weekly",
    "pdf-tools:extract": 'Extract text and tables from PDF files: use it for "read this PDF".',
    "team-notes": "Write and file meeting notes for the team wiki.",
    "project-only": "It's a project skill When the project needs it.",  # description, a space, when_to_use
    "other-plugin:slide-maker": "Build slide decks from an outline and speaker notes.",
    "classic-viewer": "Opens files in the classic viewer.",
    "ghost-plugin:phantom": "",  # its SKILL.md has an empty description, which is not a source
    "lure-plugin:sneaky": "",  # its folder is named only in untrusted places, so it is never read
    "deep-plugin:buried": "",  # deeper than */skills/*/SKILL.md next to a loaded plugin, so it is not searched
    "repo-skill": "A skill loaded from another repository.",  # from <repo>/.claude/skills: a project skill
}
DISK_SHOWN = {  # SKILL.md descriptions of skills the listing shows: the report compares them with the listing
    "docs-helper": SHOWN["docs-helper"],
    "data-tools:extract": "Pull rows from spreadsheets and CSV files.",  # differs from the listing text
}
HIDDEN = [n for n in NAMES if n not in SHOWN]
UNKNOWN = [n for n in HIDDEN if not FULL[n]]
OWN = [n for n in NAMES if n in ("team-notes", "docs-helper", "project-only", "repo-skill")]
BUILTIN = [n for n in NAMES if n in ("multi-line", "classic-viewer")]
THIRD = [n for n in NAMES if n not in OWN and n not in BUILTIN]
COMPARED = len(DISK_SHOWN)
EQUAL = sum(1 for n, d in DISK_SHOWN.items() if " ".join(d.split()) == " ".join(SHOWN[n].split()))


def line(name: str, description: str) -> str:
    return f"- {name}: {description}" if description else f"- {name}"


def text_of(name: str) -> str:
    return SHOWN.get(name, FULL.get(name, ""))


CONTENT = "\n".join(line(n, SHOWN.get(n, "")) for n in NAMES)
FULL_TEXT = "\n".join(line(n, text_of(n)) for n in NAMES)
OLD_NAMES = ["classic-viewer", "docs-helper", "multi-line"]
OLD_CONTENT = "\n".join([line("classic-viewer", FULL["classic-viewer"]), line("docs-helper", "Help with documents."),
                         line("multi-line", SHOWN["multi-line"])])


def cost(names: list, cap: int | None = None) -> int:
    return sum(len(line(n, text_of(n)[:cap])) + 1 for n in names)


def hidden_among(names: list) -> int:
    return sum(1 for n in names if n in HIDDEN)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def listing_record(names, content, stamp, initial=True, sidechain=False, cwd="", version="9.9.9", entry="cli"):
    return {"type": "attachment", "isSidechain": sidechain, "cwd": cwd, "version": version, "entrypoint": entry,
            "timestamp": stamp, "attachment": {"type": "skill_listing", "content": content, "names": names,
                                               "skillCount": len(names), "isInitial": initial}}


def loading_message(text: str) -> dict:
    """How the app loads a skill: a user record with isMeta true and one text block."""
    return {"type": "user", "isMeta": True, "timestamp": T_NEW, "message": {"role": "user", "content": [
        {"type": "text", "text": text}]}}


def run(config: Path, workdir: Path, *args, utf8: bool = True) -> tuple:
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config))
    command = [sys.executable, "-I"] + (["-X", "utf8"] if utf8 else []) + [str(SCRIPT), *args]
    done = subprocess.run(command, cwd=workdir, env=env, capture_output=True, timeout=120)
    return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8", "replace")


def build_fixture(root: Path) -> dict:
    """A fake Claude configuration with two sessions, SKILL.md files in every place the script looks."""
    config, project, store = root / "config", root / "demo-project", root / "app-data" / "store"
    write(config / "skills" / "team-notes" / "SKILL.md",
          "---\nname: team-notes\ndescription: >\n  Write and file meeting notes\n  for the team wiki.\n---\n# Notes\n")
    write(config / "skills" / "docs-helper" / "SKILL.md",
          f"---\nname: docs-helper\ndescription: {DISK_SHOWN['docs-helper']}\n---\n")
    cache = config / "plugins" / "cache" / "demo-market" / "pdf-tools" / "1.0.0"
    write(cache / ".claude-plugin" / "plugin.json", '{"name": "pdf-tools", "version": "1.0.0"}')
    write(cache / "skills" / "extract" / "SKILL.md", '---\nname: extract\ndescription: "Extract text and tables from '
          'PDF files: use it for \\"read this PDF\\"."\n---\n')
    data = config / "plugins" / "cache" / "demo-market" / "data-tools" / "2.0.0"
    write(data / ".claude-plugin" / "plugin.json", '{"name": "data-tools"}')
    write(data / "skills" / "extract" / "SKILL.md",
          f"---\nname: extract\ndescription: {DISK_SHOWN['data-tools:extract']}\n---\n")
    market = config / "plugins" / "marketplaces" / "demo-market" / "pdf-tools"
    write(market / ".claude-plugin" / "plugin.json", '{"name": "pdf-tools"}')
    write(market / "skills" / "extract" / "SKILL.md", "---\nname: extract\ndescription: OLD text that must not win\n---\n")
    newer = time.time() + 60  # the marketplace copy is newer, yet the installed cache copy must win
    os.utime(market / "skills" / "extract" / "SKILL.md", (newer, newer))
    write(project / ".claude" / "skills" / "project-only" / "SKILL.md",
          "---\nname: project-only\ndescription: 'It''s a project skill'\nwhen_to_use: When the project needs it.\n---\n")
    write(store / "plugin_A" / ".claude-plugin" / "plugin.json", '{"name": "my-plugin"}')
    write(store / "plugin_A" / "skills" / "report-writer" / "SKILL.md",
          "---\nname: report-writer\ndescription: |\n  Draft weekly reports.\n  Trigger: report, weekly\n---\n")
    write(store / "plugin_B" / ".claude-plugin" / "plugin.json", '{"name": "other-plugin"}')
    write(store / "plugin_B" / "skills" / "slide-maker" / "SKILL.md",
          "---\nname: slide-maker\ndescription: Build slide decks from an outline\n  and speaker notes. # note\n---\n")
    write(store / "plugin_C" / ".claude-plugin" / "plugin.json", '{"name": "ghost-plugin"}')
    write(store / "plugin_C" / "skills" / "phantom" / "SKILL.md", '---\nname: phantom\ndescription: ""\n---\n')
    deep = store / "deeper" / "plugin_D"
    write(deep / ".claude-plugin" / "plugin.json", '{"name": "deep-plugin"}')
    write(deep / "skills" / "buried" / "SKILL.md", "---\nname: buried\ndescription: Too deep to be searched.\n---\n")
    lure = root / "lure" / "plugin_L"
    write(lure / ".claude-plugin" / "plugin.json", '{"name": "lure-plugin"}')
    write(lure / "skills" / "sneaky" / "SKILL.md", "---\nname: sneaky\ndescription: Must never be read.\n---\n")
    repo_skill = root / "other-repo" / ".claude" / "skills" / "repo-skill"
    write(repo_skill / "SKILL.md", f"---\nname: repo-skill\ndescription: {FULL['repo-skill']}\n---\n")
    lure_dir = lure / "skills" / "sneaky"
    sessions = config / "projects" / "-demo-project"
    new_records = [
        {"type": "user", "timestamp": T_NEW, "message": {"role": "user", "content": "hello"}},
        loading_message(f"{MARKER}{store / 'plugin_A' / 'skills' / 'report-writer'}\n\n# Report writer"),
        {"type": "assistant", "timestamp": T_NEW, "message": {"content": [
            {"type": "text", "text": f'code: MARKER = "{MARKER}" + path'}]}},
        # untrusted places for a marker: an assistant message, a tool result, a line further down a loaded text
        {"type": "assistant", "timestamp": T_NEW, "message": {"content": [
            {"type": "text", "text": f"{MARKER}{lure_dir}"}]}},
        {"type": "user", "timestamp": T_NEW, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": f"Fetched page\n{MARKER}{lure_dir}\n"}]}},
        loading_message(f"# Some skill\nIts text quotes a marker:\n{MARKER}{lure_dir}"),
        loading_message(f"{MARKER}{root / 'does-not-exist'}"),
        loading_message(f"{MARKER}{root / 'app-data'}"),
        loading_message(f"{MARKER}{repo_skill}\n\n# Repo skill"),
        listing_record(NAMES, CONTENT, T_NEW, cwd=str(project)),
        listing_record(["team-notes"], "- team-notes: Updated short description", T_PARTIAL, initial=False),
        listing_record(["only-subagent"], "- only-subagent: Sub-agent listing", T_SIDE, sidechain=True),
    ]
    new_file, old_file = sessions / "session-new.jsonl", sessions / "session-old.jsonl"
    write(new_file, "\n".join(json.dumps(r, ensure_ascii=False) for r in new_records)
          + '\n{"type":"attachment","attachment":{"type":"skill_listing","content":"- broken\n')
    write(old_file, json.dumps(listing_record(OLD_NAMES, OLD_CONTENT, T_OLD, version="9.9.8")) + "\n")
    past = time.time() - 3600
    os.utime(old_file, (past, past))
    return {"config": config, "project": project, "store": store, "new": new_file, "old": old_file}


def snapshot(root: Path) -> dict:
    found = {}
    for current, _, files in os.walk(root):
        for name in files:
            path = Path(current) / name
            info = path.stat()
            found[str(path.relative_to(root))] = (info.st_size, info.st_mtime_ns)
    return found


class FrontmatterTests(unittest.TestCase):
    def description(self, text: str) -> str:
        return sbm.frontmatter(text).get("description")

    def test_plain_scalars(self):
        self.assertEqual(self.description("---\nname: a\ndescription: Simple text\n---\n"), "Simple text")
        self.assertEqual(self.description("---\ndescription: Use it: now\n---"), "Use it: now")
        self.assertEqual(self.description("---\ndescription: First part\n  second part # comment\n---"),
                         "First part second part")

    def test_quoted_scalars(self):
        self.assertEqual(self.description('---\ndescription: "Say \\"hi\\"\\tthen \\u00e8 done"\n---'),
                         'Say "hi"\tthen è done')
        self.assertEqual(self.description("---\ndescription: 'It''s fine'\n---"), "It's fine")
        self.assertEqual(self.description('---\ndescription: "two\n  lines"\n---'), "two lines")

    def test_block_scalars(self):
        self.assertEqual(self.description("---\ndescription: |\n  line one\n  line two\n---"), "line one\nline two")
        self.assertEqual(self.description("---\ndescription: >-\n  folded one\n  folded two\n\n  new paragraph\n---"),
                         "folded one folded two\nnew paragraph")

    def test_windows_file_with_byte_order_mark_and_other_keys(self):
        meta = sbm.frontmatter(BOM + "---\r\nname: x\r\ndescription: Windows file\r\nmetadata:\r\n  v: 1\r\n---\r\n")
        self.assertEqual((meta["name"], meta["description"]), ("x", "Windows file"))

    def test_when_to_use_is_read(self):
        meta = sbm.frontmatter("---\nname: x\ndescription: What it does\nwhen_to_use: When asked\n---\n")
        self.assertEqual((meta["description"], meta["when_to_use"]), ("What it does", "When asked"))

    def test_missing_or_unclosed(self):
        self.assertEqual(sbm.frontmatter("# just a title\n"), {})
        self.assertEqual(sbm.frontmatter("---\nname: x\n"), {})


class ParseListingTests(unittest.TestCase):
    def test_names_delimit_entries_and_continuations(self):
        preamble, entries, mismatch = sbm.parse_listing(CONTENT, NAMES)
        self.assertEqual((preamble, mismatch), ([], False))
        self.assertEqual([e.name for e in entries], NAMES)
        self.assertEqual({e.name: e.shown for e in entries if e.shown}, SHOWN)
        self.assertEqual(sbm.listing_length(preamble, [(e.name, e.shown) for e in entries]), len(CONTENT))

    def test_fallback_without_names(self):
        _, entries, mismatch = sbm.parse_listing(CONTENT, [])
        self.assertEqual([e.name for e in entries], NAMES)  # the "- Not a skill name: ..." line stays a continuation
        self.assertFalse(mismatch)  # no names field: nothing to line up

    def test_names_that_do_not_line_up_fall_back(self):
        _, entries, mismatch = sbm.parse_listing(CONTENT, NAMES[:3] + ["not-there"] + NAMES[3:])
        self.assertEqual([e.name for e in entries], NAMES)
        self.assertTrue(mismatch)


class NetworkPathTests(unittest.TestCase):
    NETWORK = ["\\\\server\\share\\skills\\x", "//server/share/skills/x",
               "/\\server\\share\\skills\\x", "\\/server/share/skills/x"]  # the last two: mixed slashes

    def test_local_path_rejects_network_and_relative_paths(self):
        for text in self.NETWORK + ["relative/skills/x", "", "   "]:
            self.assertIsNone(sbm.local_path(text), text)
        here = Path(tempfile.gettempdir()).resolve()
        self.assertEqual(sbm.local_path(f" {here} "), here)

    def test_skill_roots_never_touch_network_or_relative_paths(self):
        listing = sbm.Listing("", [], "", "", "", "", "/\\server\\share\\repo", (0.0, 0))
        bases = self.NETWORK + ["relative/skills/x"]
        with mock.patch.object(Path, "is_file", side_effect=AssertionError("a network or relative path was read")):
            roots = sbm.skill_roots(Path(tempfile.gettempdir()) / "config", listing, [], bases)
        self.assertEqual([kind for _, kind, _ in roots], ["personal", "plugin"])  # no project root from a UNC cwd

    def test_marker_counts_only_at_the_start_of_a_text_block(self):
        self.assertEqual(sbm.MARKER_RE.match(f"{MARKER}/opt/skills/x\n\n# X").group(1), "/opt/skills/x")
        self.assertIsNone(sbm.MARKER_RE.match(f"# A skill\n{MARKER}/opt/skills/x"))


class LinkTests(unittest.TestCase):
    def link(self, target: Path, link: Path) -> None:
        """A symbolic link or, on Windows without the right to create one, a junction; otherwise skip the test."""
        try:
            os.symlink(target, link, target_is_directory=True)
            return
        except (OSError, NotImplementedError) as exc:
            reason = type(exc).__name__
        if os.name == "nt":
            try:
                import _winapi
                _winapi.CreateJunction(str(target), str(link))
                return
            except (ImportError, AttributeError, OSError) as exc:
                reason = type(exc).__name__
        self.skipTest(f"this system allows no symbolic links or junctions here ({reason})")

    @staticmethod
    def remove(link: Path) -> None:
        try:
            os.unlink(link)
        except OSError:
            os.rmdir(link)

    def test_linked_skills_are_found_once_even_with_a_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skills, target = root / "config" / "skills", root / "elsewhere" / "linked-skill"
            write(target / "SKILL.md", "---\nname: linked-skill\ndescription: Reached through a link.\n---\n")
            skills.mkdir(parents=True)
            links = [skills / "linked-skill", target / "back-to-skills"]
            try:
                self.link(target, links[0])
                self.link(skills, links[1])  # a loop: the linked skill links back to the skills folder
                write(root / "config" / "projects" / "-p" / "s.jsonl",
                      json.dumps(listing_record(["linked-skill"], "- linked-skill", T_NEW)) + "\n")
                code, out, err = run(root / "config", root, "--json")
                self.assertEqual((code, err), (3, ""))
                report = json.loads(out)
                self.assertEqual([(s["source"], s["class"]) for s in report["skills"]], [("skill_md", "own")])
                self.assertEqual(report["full"]["chars"], len(line("linked-skill", "Reached through a link.")))
            finally:
                for link in reversed(links):
                    if os.path.lexists(link):
                        self.remove(link)


class CommandLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "fixture"
        cls.paths = build_fixture(cls.root)
        cls.workdir = Path(cls.temp.name) / "empty-cwd"
        cls.workdir.mkdir()
        cls.inputs = Path(cls.temp.name) / "inputs"
        cls.inputs.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_script(self, *args, utf8=True, config=None):
        return run(config or self.paths["config"], self.workdir, *args, utf8=utf8)

    def changes_file(self, name: str, data, encoding="utf-8") -> str:
        path = self.inputs / name
        path.write_bytes(data.encode(encoding) if isinstance(data, str) else json.dumps(data).encode(encoding))
        return str(path)

    def measure(self, *args, config=None):
        code, out, err = self.run_script("--json", *args, config=config)
        self.assertEqual(err, "")
        return code, json.loads(out)

    def test_measure_counts_and_full_size(self):
        code, report = self.measure()
        self.assertEqual(code, 3)  # skills without description
        listing, full = report["listing"], report["full"]
        self.assertEqual((listing["timestamp"], listing["session"]), (T_NEW, "session-new"))
        self.assertEqual((listing["app_version"], listing["entrypoint"]), ("9.9.9", "cli"))
        self.assertEqual(listing["chars"], len(CONTENT))
        self.assertEqual(listing["utf16_units"], len(CONTENT) + 1)
        self.assertEqual(listing["rebuilt_chars"], len(CONTENT))
        self.assertFalse(listing["names_mismatch"])
        self.assertEqual((listing["skills"], listing["with_description"]), (len(NAMES), len(SHOWN)))
        self.assertEqual(listing["without_description"], HIDDEN)
        self.assertEqual(full["chars"], len(FULL_TEXT))
        self.assertEqual((full["cap"], full["margin"], full["target"], full["entry_cap"]), (30000, 600, 29400, 1536))
        self.assertEqual(full["room"], 29400 - len(FULL_TEXT))
        self.assertEqual(full["over_entry_cap"], [])
        self.assertEqual(full["unknown_full_description"], UNKNOWN)
        self.assertEqual(full["from_older_listings"], ["classic-viewer"])

    def test_listing_far_below_the_cap_is_flagged(self):
        _, report = self.measure()
        self.assertTrue(report["listing"]["cut_well_below_cap"])  # a tiny listing lost descriptions at cap 30,000
        _, fitted = self.measure("--tetto", str(len(CONTENT) + 10), "--margine", "0")
        self.assertFalse(fitted["listing"]["cut_well_below_cap"])  # a cap that matches the listing: no warning

    def test_sources_classes_and_budget(self):
        _, report = self.measure()
        sources = {s["name"]: s["source"] for s in report["skills"]}
        self.assertEqual(sources["pdf-tools:extract"], "skill_md")  # installed cache copy, not the marketplace one
        self.assertEqual(sources["other-plugin:slide-maker"], "skill_md")  # sibling of a loaded skill's plugin
        self.assertEqual(sources["team-notes"], "skill_md")  # SKILL.md wins over the later partial update
        self.assertEqual(sources["project-only"], "skill_md")  # description and when_to_use
        self.assertEqual(sources["classic-viewer"], "older_listing")
        self.assertEqual(sources["docs-helper"], "listing")
        classes = {s["name"]: s["class"] for s in report["skills"]}
        self.assertEqual(sorted(n for n, c in classes.items() if c == "own"), sorted(OWN))
        self.assertEqual(sorted(n for n, c in classes.items() if c == "builtin"), sorted(BUILTIN))
        self.assertEqual(sorted(n for n, c in classes.items() if c == "third_party"), sorted(THIRD))
        by_class = report["by_class"]
        for key, names in (("own", OWN), ("builtin", BUILTIN), ("third_party", THIRD)):
            self.assertEqual(by_class[key], {"skills": len(names), "chars": cost(names),
                                             "without_description": hidden_among(names)}, key)
        self.assertEqual(report["own_budget"], 29400 - (len(FULL_TEXT) - cost(OWN)))
        self.assertEqual(report["skill_md_check"], {"compared": COMPARED, "equal": EQUAL})
        full_lengths = {n: len(text_of(n)) for n in NAMES}
        expected_top = sorted(NAMES, key=lambda n: (-full_lengths[n], n))[:3]
        _, top3 = self.measure("--prime", "3")
        self.assertEqual([item["name"] for item in top3["longest"]], expected_top)

    def test_skill_folders_come_only_from_skill_loading_messages(self):
        _, report = self.measure()
        sources = {s["name"]: s["source"] for s in report["skills"]}
        classes = {s["name"]: s["class"] for s in report["skills"]}
        self.assertEqual(sources["my-plugin:report-writer"], "skill_md")  # its folder opens a loading message
        self.assertEqual(sources["lure-plugin:sneaky"], "unknown")  # only in untrusted places
        self.assertEqual((sources["repo-skill"], classes["repo-skill"]), ("skill_md", "own"))  # <repo>/.claude/skills
        self.assertTrue((self.paths["store"] / "deeper" / "plugin_D" / "skills" / "buried" / "SKILL.md").is_file())
        self.assertEqual(sources["deep-plugin:buried"], "unknown")  # next to a loaded plugin, only */skills/*/SKILL.md

    def test_skill_md_with_empty_description_is_not_a_source(self):
        self.assertTrue((self.paths["store"] / "plugin_C" / "skills" / "phantom" / "SKILL.md").is_file())
        _, report = self.measure()
        self.assertEqual({s["name"]: s["source"] for s in report["skills"]}["ghost-plugin:phantom"], "unknown")
        _, out, _ = self.run_script("--lang", "en")
        warning = next(row for row in out.splitlines() if "hidden skills without a SKILL.md found" in row)
        self.assertIn(f"Warning: {len(UNKNOWN)} hidden skills", warning)
        self.assertIn("ghost-plugin:phantom", warning)

    def test_entry_cap_applies_to_full_total_and_simulation(self):
        cap = 20
        _, report = self.measure("--max-voce", str(cap))
        self.assertEqual(report["full"]["chars"], len("\n".join(line(n, text_of(n)[:cap]) for n in NAMES)))
        self.assertEqual(report["full"]["entry_cap"], cap)
        self.assertEqual(report["full"]["over_entry_cap"], [n for n in NAMES if len(text_of(n)) > cap])
        self.assertEqual(report["by_class"]["own"]["chars"], cost(OWN, cap))
        self.assertEqual(max(item["chars"] for item in report["longest"]), cap)
        equal_within_cap = sum(1 for n, d in DISK_SHOWN.items()
                               if " ".join(d[:cap].split()) == " ".join(SHOWN[n][:cap].split()))
        self.assertEqual(report["skill_md_check"], {"compared": COMPARED, "equal": equal_within_cap})
        changes = {"team-notes": "y" * 100}
        _, sim = self.measure("--entry-cap", str(cap), "--simulate", self.changes_file("cap.json", changes))
        texts = dict({n: text_of(n) for n in NAMES}, **changes)
        self.assertEqual(sim["simulation"]["chars"], len("\n".join(line(n, texts[n][:cap]) for n in NAMES)))
        _, out, _ = self.run_script("--max-voce", str(cap), "--lang", "en")
        self.assertIn(f"Over the per-entry cap of {cap} characters, counted up to the cap: ", out)

    def test_partial_update_and_subagent_are_not_measured(self):
        _, report = self.measure()
        self.assertNotEqual(report["listing"]["timestamp"], T_PARTIAL)
        self.assertNotEqual(report["listing"]["timestamp"], T_SIDE)
        self.assertEqual(report["listing"]["skills"], len(NAMES))  # an update would give 1 skill, 0 hidden

    def test_mine_patterns(self):
        _, report = self.measure("--mie", "other-plugin:*")
        mine = OWN + ["other-plugin:slide-maker", "other-plugin:bullets"]
        self.assertEqual(report["by_class"]["own"]["skills"], len(mine))
        self.assertEqual(report["by_class"]["own"]["chars"], cost(mine))
        _, same = self.measure("--mine", "other-plugin:slide-maker,OTHER-PLUGIN:BULLETS")
        self.assertEqual(same["by_class"]["own"]["skills"], len(mine))

    def test_text_output_in_both_languages(self):
        code, out, err = self.run_script("--lingua", "it")
        self.assertEqual((code, err), (3, ""))
        for text in ("Elenco reale: ", "(tetto 30.000)", f"SENZA {len(HIDDEN)}", "Spazio per le tue skill",
                     "ghost-plugin:phantom", "classic-viewer", "Il modello ne vede solo il nome",
                     "Avviso: l'elenco ha skill senza descrizione ma è ben sotto il tetto di 30.000",
                     f"Nota: {COMPARED - EQUAL} delle {COMPARED} descrizioni mostrate nell'elenco differiscono"):
            self.assertIn(text, out)
        self.assertTrue(out.rstrip("\n").splitlines()[-1].startswith(f"Esito: skill senza descrizione: {len(HIDDEN)}."))
        code, out, _ = self.run_script("--lang", "en")
        for text in ("Actual listing: ", "(cap 30,000)", f"WITHOUT {len(HIDDEN)}", "Room for your skills",
                     "so it is unlikely to choose them on its own",
                     "Warning: the listing has skills without description but is well below the cap of 30,000",
                     f"Note: {COMPARED - EQUAL} of {COMPARED} descriptions shown in the listing differ"):
            self.assertIn(text, out)
        self.assertTrue(out.rstrip("\n").splitlines()[-1].startswith(f"Result: skills without description: {len(HIDDEN)}."))

    def test_template(self):
        code, out, _ = self.run_script("--modello")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(list(data), OWN)
        self.assertEqual(data["team-notes"], FULL["team-notes"])
        self.assertEqual(data["project-only"], FULL["project-only"])
        self.assertEqual(data["docs-helper"], SHOWN["docs-helper"])

    def test_simulation_within_target(self):
        changes = {"team-notes": "Notes.", "ghost-plugin:phantom": None, "brand-new:skill": "New skill.",
                   "report-writer": "Reports.", "not-installed": None}
        code, report = self.measure("--simula", self.changes_file("sim.json", changes))
        self.assertEqual(code, 0)
        names = [n for n in NAMES if n != "ghost-plugin:phantom"] + ["brand-new:skill"]
        texts = dict({n: text_of(n) for n in NAMES}, **{
            "team-notes": "Notes.", "brand-new:skill": "New skill.", "my-plugin:report-writer": "Reports."})
        expected = len("\n".join(line(n, texts[n]) for n in names))
        sim = report["simulation"]
        self.assertEqual(sim["chars"], expected)
        self.assertEqual(sim["changed"], ["team-notes", "my-plugin:report-writer"])
        self.assertEqual((sim["added"], sim["removed"]), (["brand-new:skill"], ["ghost-plugin:phantom"]))
        self.assertEqual(sim["not_found"], ["not-installed"])
        self.assertTrue(sim["within_target"])
        self.assertEqual(report["exit_code"], 0)

    def test_simulation_text_names_new_skills_and_ends_with_its_result(self):
        path = self.changes_file("sim-text.json", {"team-notes": "Notes.", "brand-new:skill": "New skill.",
                                                   "typo-skil": "Oops."})
        code, out, err = self.run_script("--simulate", path, "--lang", "en")
        self.assertEqual((code, err), (0, ""))  # within the target, although skills are hidden in the listing
        lines = out.rstrip("\n").splitlines()
        self.assertEqual(lines[-1], "Result of the simulation: within the target (exit code 0: it reflects the "
                                    "simulation only). Check the cap warning above.")  # the fixture is far below 30,000
        self.assertIn(f"Measured listing: skills without description: {len(HIDDEN)}.", lines)
        self.assertIn("  New, i.e. not in the listing (check the spelling): brand-new:skill, typo-skil", lines)
        self.assertNotIn("Result: skills without description", out)
        code, out, _ = self.run_script("--simula", path, "--tetto", "300", "--margine", "0", "--lingua", "it")
        self.assertEqual(code, 3)
        last = out.rstrip("\n").splitlines()[-1]
        self.assertTrue(last.startswith("Esito della simulazione: oltre l'obiettivo di "))
        self.assertTrue(last.endswith("accorcia altre descrizioni."))  # the listing is not below this cap: no note

    def test_simulation_over_target_and_utf16_file(self):
        path = self.changes_file("sim16.json", json.dumps({"team-notes": "x" * 400}), encoding="utf-16")
        code, report = self.measure("--simula", path, "--tetto", "600", "--margine", "0")
        self.assertEqual(code, 3)
        self.assertFalse(report["simulation"]["within_target"])
        code, out, _ = self.run_script("--simulate", path, "--cap", "600", "--margin", "0", "--lang", "en")
        self.assertIn("Simulation (sim16.json)", out)
        self.assertIn("OVER by", out)

    def test_simulation_input_errors(self):
        code, _, err = self.run_script("--simula", self.changes_file("ambiguous.json", {"extract": "x"}))
        self.assertEqual(code, 2)
        self.assertIn("pdf-tools:extract", err)
        self.assertIn("data-tools:extract", err)
        code, _, err = self.run_script("--simula", self.changes_file("broken.json", "not json"))
        self.assertEqual(code, 2)
        code, _, err = self.run_script("--simula", self.changes_file("number.json", {"team-notes": 5}))
        self.assertEqual(code, 2)
        code, _, err = self.run_script("--simula", self.changes_file("list.json", ["team-notes"]))
        self.assertEqual(code, 2)
        code, _, err = self.run_script("--simula", str(self.inputs / "missing.json"))
        self.assertEqual(code, 2)

    def test_history(self):
        code, out, _ = self.run_script("--storico", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        rows = data["history"]
        self.assertEqual([r["timestamp"] for r in rows], [T_OLD, T_NEW])
        self.assertEqual([r["without_description"] for r in rows], [0, len(HIDDEN)])
        self.assertEqual([r["chars"] for r in rows], [len(OLD_CONTENT), len(CONTENT)])
        self.assertEqual(data["estimated_cap"], len(CONTENT))  # the longest listing that lost descriptions
        code, out, _ = self.run_script("--storico", "--json", "--recenti", "1")
        self.assertEqual([r["timestamp"] for r in json.loads(out)["history"]], [T_NEW])
        code, out, _ = self.run_script("--history", "--lang", "en")
        self.assertIn("Initial listings found: 2", out)
        self.assertIn(f"Estimated cap: {len(CONTENT):,} characters", out)
        self.assertIn("characters without description", out)  # one space, not two

    def test_all_descriptions_shown_exit_zero(self):
        other = Path(self.temp.name) / "only-old"
        target = other / "projects" / "-demo-project" / "session-old.jsonl"
        write(target, self.paths["old"].read_text(encoding="utf-8"))
        code, out, _ = self.run_script("--lingua", "it", config=other)
        self.assertEqual(code, 0)
        self.assertIn("Esito: tutte le skill hanno la descrizione.", out)
        code, out, _ = self.run_script("--storico", "--json", config=other)
        self.assertIsNone(json.loads(out)["estimated_cap"])
        code, out, _ = self.run_script("--storico", "--lingua", "it", config=other)
        self.assertIn("Tetto stimato: non disponibile", out)

    def test_names_that_do_not_line_up_are_reported(self):
        other = Path(self.temp.name) / "mismatch"
        names = NAMES[:3] + ["not-there"] + NAMES[3:]
        write(other / "projects" / "-p" / "s.jsonl", json.dumps(listing_record(names, CONTENT, T_NEW)) + "\n")
        _, report = self.measure(config=other)
        self.assertTrue(report["listing"]["names_mismatch"])
        self.assertEqual([s["name"] for s in report["skills"]], NAMES)  # split by the line pattern instead
        _, out, _ = self.run_script("--lang", "en", config=other)
        self.assertIn("  Warning: the listing's names field does not match its text", out)

    def test_no_listing_and_bad_options(self):
        empty = Path(self.temp.name) / "no-transcripts"
        empty.mkdir(exist_ok=True)
        code, out, err = self.run_script("--trascrizioni", str(empty), "--lingua", "it")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("Nessun elenco iniziale", err)
        self.assertEqual(self.run_script("--margine", "30000")[0], 2)
        self.assertEqual(self.run_script("--tetto", "0")[0], 2)
        self.assertEqual(self.run_script("--max-voce", "0")[0], 2)
        self.assertEqual(self.run_script("--entry-cap", "-5")[0], 2)
        self.assertEqual(self.run_script("--prime", "-1")[0], 2)
        self.assertEqual(self.run_script("--lingua", "fr")[0], 2)
        self.assertEqual(self.run_script("--unknown-option")[0], 2)

    def test_version_and_help(self):
        code, out, _ = self.run_script("--version")
        self.assertEqual((code, out.strip()), (0, f"skill-budget-meter {sbm.VERSION}"))
        for lang, words in (("it", ("--simula", "--max-voce", "1%")), ("en", ("--simulate", "--entry-cap", "1%"))):
            code, out, _ = self.run_script("--help", "--lingua", lang)
            self.assertEqual(code, 0)
            for word in words:
                self.assertIn(word, out)

    def test_works_without_utf8_mode(self):
        code, out, _ = self.run_script("--modello", utf8=False)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["docs-helper"], SHOWN["docs-helper"])

    def test_read_only(self):
        before = snapshot(Path(self.temp.name))
        sim = self.changes_file("readonly.json", {"team-notes": "Short."})
        after_inputs = snapshot(Path(self.temp.name))
        for args in ((), ("--json",), ("--storico",), ("--storico", "--json"), ("--modello",), ("--simula", sim),
                     ("--max-voce", "50"), ("--lingua", "en")):
            self.run_script(*args)
        self.assertEqual(snapshot(Path(self.temp.name)), after_inputs)
        self.assertEqual(set(after_inputs) - set(before), {str(Path("inputs") / "readonly.json")})
        self.assertEqual(list(self.workdir.iterdir()), [])


class SourceSafetyTests(unittest.TestCase):
    SOURCE = SCRIPT.read_text(encoding="utf-8")
    TREE = ast.parse(SOURCE)
    MODULES = {"__future__", "argparse", "dataclasses", "datetime", "fnmatch", "json", "locale", "os", "pathlib",
               "re", "string", "sys"}

    def test_imports_are_exactly_these_standard_modules(self):
        found = set()
        for node in ast.walk(self.TREE):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                found.add((node.module or "").split(".")[0])
        self.assertEqual(found, self.MODULES)  # no network, process or shell module can slip in
        standard = set(getattr(sys, "stdlib_module_names", self.MODULES)) | {"__future__"}
        self.assertTrue(self.MODULES <= standard)

    def test_no_writes_no_processes_no_dynamic_code(self):
        writing = {"write_text", "write_bytes", "unlink", "mkdir", "rmdir", "rename", "touch", "symlink_to",
                   "hardlink_to", "chmod"}
        os_calls = {"remove", "unlink", "rename", "replace", "makedirs", "mkdir", "rmdir", "system", "popen",
                    "symlink", "link", "chmod", "startfile", "kill"}
        found = []
        for node in ast.walk(self.TREE):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile", "__import__"):
                found.append(func.id)
            if isinstance(func, ast.Attribute) and func.attr in writing:
                found.append(func.attr)
            if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os"
                    and (func.attr in os_calls or func.attr.startswith(("exec", "spawn", "fork")))):
                found.append(f"os.{func.attr}")
            if isinstance(func, ast.Name) and func.id == "open":
                mode = node.args[1] if len(node.args) > 1 else next(
                    (k.value for k in node.keywords if k.arg == "mode"), None)
                if mode is not None and not (isinstance(mode, ast.Constant) and set(str(mode.value)) <= set("rbt")):
                    found.append("open for writing")
        self.assertEqual(found, [])

    def test_old_python_reaches_the_version_check(self):
        ast.parse(self.SOURCE, feature_version=(3, 7))  # 3.7 to 3.9 must read the file and stop politely
        self.assertRegex(self.SOURCE, r"(?m)^if sys\.version_info < \(3, 10\):\n    sys\.exit\(")

    def test_symbolic_links_are_followed(self):
        self.assertRegex(self.SOURCE, r"os\.walk\([^)\n]*followlinks=True")
        self.assertNotIn(BOM, self.SOURCE)  # the byte order mark is written as chr(0xFEFF), never as a raw character


if __name__ == "__main__":
    unittest.main()
