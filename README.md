# skill-budget-meter

How much of your Claude Code **skill listing** fits in its budget? This script measures it from the
transcripts already on your computer, names the skills that lost their description, and lets you simulate
shorter descriptions before you install anything.

One Python file · standard library only · read-only · no network.

> **Independent project, not affiliated with Anthropic.** The budget is described in the official Claude Code
> documentation, [Skill descriptions are cut short](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short):
> 1% of the model's context window. The default of 30,000 characters used here is the author's own
> measurement (13 November 2026) with models that have a 1M-token context window: with another model or other
> settings your cap is different, and any release may change the details.

[Leggimi in italiano](README.it.md)

> **Second module: [interference/](interference/).** Does a new skill take an old one's place in routing?
> A read-only lexical check of your skill names and descriptions, run before you install (method
> adapted from SKILL++, [arXiv:2611.00544](https://arxiv.org/abs/2611.00544)).

## Why it matters

When a session starts, Claude Code gives the model a listing of the available skills, one entry each:
`- name: description`. The model picks a skill by itself only when the description tells it what the skill
is for.

What the official documentation says (the section linked above, read on 13 November 2026):

- the listing has a character budget of **1% of the model's context window**;
- every skill name is always listed, but when the listing overflows Claude Code drops descriptions,
  **starting with the skills you invoke least**;
- each entry, `description` plus `when_to_use`, is capped at **1,536 characters**, whatever the budget;
- you can raise the budget with the `skillListingBudgetFraction` setting (for example `0.02` = 2%) or fix it
  in characters with the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable; the per-entry cap is
  `skillListingMaxDescChars`; a skill set to `"name-only"` in `skillOverrides` is listed without a
  description. Plugin skills are not affected by `skillOverrides`: manage them with `/plugin`.

Two consequences, in the author's reading: a skill you have just installed has never been invoked, so it is
likely to be among the first to lose its description; and a low-priority skill set to `"name-only"` leaves
its room to the others.

A skill listed with its name only is still installed, but the model sees only its name, so it is unlikely to
choose it on its own. It is easy not to notice.

## Alongside /doctor and /context

Claude Code itself estimates the listing's context cost and its biggest contributors in `/doctor`, shows what
each skill costs and how often it is used in `/skill-doctor` (v2.1.252 or later), reports the size of the
listing after the budget in the Skills row of `/context` (from v2.1.196; earlier versions counted every
description in full), and writes a warning to the debug log (`--debug`) when the listing exceeds its budget.
This script shows:

- the **names** of the skills shown without description right now;
- the size the listing **would have with every description**, so you know how much to cut;
- the room left for **your** skills, apart from plugin and built-in ones;
- the **history** of your listings and an estimated cap (`--history`);
- a **simulation** of new or shorter descriptions before you install or edit anything (`--simulate`).

## What was measured

The author's own sessions up to 13 Nov 2026, 18:18 UTC, read with this script (`--history --recent 0`) and
aggregated by the author:

| | |
|---|---|
| Listings examined | 166 initial listings, 23 Sep – 13 Nov 2026, Claude Code 2.1.280 – 2.1.321 (164 from the desktop app, 2 from the CLI) |
| Listings with at least one skill missing its description | 163, **all between 29,934 and 30,001 characters** (77–93 skills, 1–37 without description) |
| Listings where every description fit | 3, between 6,698 and 7,989 characters (15–17 skills) |
| 13 Nov 2026, 15:49 UTC | 30,001 characters, 91 skills, **37 without description** |
| Same day, 18:18 UTC, after shortening the author's own descriptions | 29,992 characters, 91 skills, **1 without description**; with every description the listing would be 30,065 characters |

The models used in these sessions have a context window of 1M tokens: about 30,000 characters is what the 1%
budget came to in this setup.

### What happened next: from 37 skills without description to 0

The same setup, including the later sessions, read with `--history --recent 0` on 19 Nov 2026 (Claude Code
2.1.321 to 2.1.326):

| When (UTC) | Listing | Skills | Without description |
|---|---|---|---|
| 13 Nov 2026, 15:49 | 30,001 characters | 91 | **37** |
| 13 Nov 2026, 18:18 | 29,992 characters | 91 | **1** |
| 13 Nov 2026, 19:23 | 28,553 characters | 86 | **0** |
| 18 Nov 2026, 23:12 | 28,895 characters | 89 | **0** |

What the author changed in between (the author's own account; the script shows only the result), in this order:
the descriptions were shortened to one line each, every change checked with `--simulate` before installing it,
which took the count from 37 to 1; five unused example skills were removed (91 → 86 skills); and
`skillListingBudgetFraction` was raised to `0.02`. The 81 listings from 13 Nov, 19:17 UTC to 18 Nov, 23:12 UTC
(27,654–29,327 characters, 74–90 skills) all kept every description, and all would have fit under the old budget
of about 30,000 characters as well: here the raised fraction is headroom, not what brought the count to 0.
One user's setup, not a promise for yours: run the script on your own transcripts.

## Quick start

Requires Python 3.10 or later. Download `skill_budget_meter.py`, then run:

```
python skill_budget_meter.py --top 5
```

On macOS and Linux use `python3 skill_budget_meter.py --top 5`; on Windows you can also use `py`. With
Python 3.7 to 3.9 the script says it needs 3.10 and stops; older versions stop with a syntax error. Example
output (synthetic data, produced by the script itself):

```
skill-budget-meter 1.1.0 · initial listing of 2026-01-15 09:00 UTC · Claude Code 2.1.0 (claude-desktop) · session demo0001
Actual listing: 29,620 characters (cap 30,000) · 90 skills · with description 84 · WITHOUT 6
  Without description: car-service, pet-care, gift-ideas, event-planner, letter-writer, project-diary
With every description: 31,335 characters · target 29,400 (cap 30,000 minus margin 600) · OVER by 1,935
  yours         20 skills ·   5,951 characters · without description 6
  third-party   55 skills ·  18,179 characters · without description 0
  built-in      15 skills ·   7,206 characters · without description 0
  Room for your skills: 4,016 characters; they use 5,951 today (cut 1,935)
Longest descriptions:
   1.  1,390  review-changes  (built-in)
   2.  1,180  chart-maker  (built-in)
   3.  1,150  schedule-runner  (built-in)
   4.    610  loop-runner  (built-in)
   5.    455  dev-kit:skill-08  (third-party)
Result: skills without description: 6. The model sees only their name, so it is unlikely to choose them on its own: shorten the longest descriptions and check with --simulate.
```

Messages follow your system language (English or Italian); force one with `--lang en` or `--lang it`.

## Options

Every option except `--json` has an Italian and an English name.

| Option | Default | What it does |
|---|---|---|
| `--simula` / `--simulate FILE` | | Simulate new, changed or removed descriptions (see below) |
| `--modello` / `--template` | | Print your skills and their current descriptions as JSON, ready to edit |
| `--storico` / `--history` | | One line per initial listing found, then the estimated cap (see Limits) |
| `--tetto` / `--cap N` | 30000 | Listing cap in characters. The budget is 1% of the context window, which is counted in tokens: measure your cap with `--history` instead of computing it |
| `--margine` / `--margin N` | 600 | Safety margin: the target is the cap minus the margin |
| `--max-voce` / `--entry-cap N` | 1536 | Cap of each entry, description plus `when_to_use`, as `skillListingMaxDescChars` |
| `--prime` / `--top N` | 10 | How many of the longest descriptions to show |
| `--mie` / `--mine PATTERN` | | Mark plugin skills as yours, for example `"my-plugin:*"` (repeatable; commas allowed) |
| `--cartella` / `--dir DIR` | | Extra folder where `SKILL.md` files are searched (repeatable) |
| `--trascrizioni` / `--transcripts DIR` | `<config>/projects` | Where the transcripts are |
| `--recenti` / `--recent N` | 40 | How many recent sessions to read (0 = all) |
| `--json` | | Machine-readable output |
| `--lingua` / `--lang it\|en` | system | Message language |
| `--versione` / `--version` | | Show the version |

`<config>` is `$CLAUDE_CONFIG_DIR` when it is set, otherwise `~/.claude`.

## Simulate before you install

1. `python skill_budget_meter.py --template > new.json` prints your skills with their current
   descriptions (every skill, if none is recognised as yours).
2. Edit `new.json`: shorten descriptions, add `"plugin:new-skill": "..."` for a skill you plan to install,
   set a skill to `null` to simulate removing it. See `examples/simulate.example.json`.
3. `python skill_budget_meter.py --simulate new.json` compares the simulated total with the target. The
   report names the skills it treats as new, so a misspelt name cannot silently become a new skill.

With `--simulate` the exit code reflects the simulation only: 0 within the target, 3 over, even when the
measured listing has skills without description.

A name without the plugin prefix matches the skill with that short name, as long as only one skill has it.
The file can be UTF-8 or UTF-16, as Windows PowerShell 5 writes it.

Example (same synthetic data, the user's 20 skills shortened to about 110 characters each; last lines of the
output):

```
Measured listing: skills without description: 6.
Simulation (new.json): 27,925 characters · changed 20 · new 0 · removed 0 · WITHIN, 1,475 left
Result of the simulation: within the target (exit code 0: it reflects the simulation only).
```

## Writing shorter descriptions

- One line: what the skill does and when to use it; trigger words at the end.
- Put the key use case first: past 1,536 characters (description plus `when_to_use`) the entry is cut anyway.
- No version numbers, dates or changelogs: they belong in the body of `SKILL.md`.
- Procedures, examples and details go in the body too: the model reads the body only after it has chosen
  the skill.
- Give more room to the skills you rely on most. The author's rule of thumb: about 170 characters for core
  skills, about 80 for the others.
- Measure again in a new session after installing: the listing is built when a session starts, and a new
  skill, never invoked yet, is likely to be among the first to lose its description.

## How it works

- It reads `<config>/projects/*/*.jsonl`, the transcripts Claude Code writes (the 40 most recent by default).
- It looks for attachments of type `skill_listing`. Only **initial** listings are measured: mid-session
  updates (`isInitial: false`) contain only the skills that changed, and measuring one would give a false
  "all good". Sub-agent listings are skipped.
- It takes the newest initial listing and splits it into skills with its `names` field: a description may
  span several lines. If that field does not match the text, it splits by the `- name:` pattern and says so.
- If the listing has skills without description but is shorter than 90% of the cap, the report warns that
  the cap is probably wrong for your model, or that those skills are name-only.
- For a skill shown without description it looks for the full text in `SKILL.md` files: under
  `<config>/skills`, the session project's `.claude/skills`, `<config>/plugins` and `--dir` (up to 7 levels
  down, following symbolic links, each folder once), and next to the skills loaded in recent sessions (their
  sibling skills and the skills of the plugins next to theirs). A `SKILL.md` with an empty description does
  not count. Otherwise it uses the most recent listing, from any session read on this computer, in which the
  skill was shown.
- An entry's full text is its `description`, a space and its `when_to_use`, cut at the per-entry cap.
- Classes: **yours** (personal and project skills, plus `--mine`), **third-party** (plugin skills),
  **built-in** (no plugin prefix and no `SKILL.md` found).

## Limits

- The transcript format is not a documented interface, so an update can change it. The script warns when
  it cannot rebuild the listing to the exact character.
- The cap depends on your model and settings: 30,000 is the author's measurement, not a constant. The context
  window is counted in tokens and the cap in characters, so measure the cap rather than computing it:
  `--history` gives an estimate from your own listings.
- That estimate holds only if none of your skills is name-only or lacks a description; across several models
  it is the highest cap seen.
- Which descriptions are dropped depends on how often you invoke each skill, which the script cannot see: it
  reports the skills hidden now and the full total, not which ones will be hidden next.
- The full total is an estimate when it uses `SKILL.md` text, which may differ from what the listing showed
  (edited since, or written differently): the report says how many shown descriptions differ from their
  `SKILL.md`. How the app joins `description` and `when_to_use` is not documented either: the script joins
  them with a space.
- Characters are counted as Unicode code points. If the app counts UTF-16 units, an emoji counts twice; the
  report shows both counts when they differ.
- Only sessions saved on this computer are read. The cap was observed in the desktop app; in the CLI the
  author never had enough skills to reach it.
- A hidden skill with no `SKILL.md` on disk and no earlier listing makes the full total an underestimate:
  the report names it.
- Tested on Windows 10 with Python 3.14; not yet tested on macOS or Linux. The tests also check that the
  syntax reads on Python 3.7, so that older versions reach the version check.

## Privacy

- It reads local files only, writes nothing and never uses the network. The tests check the source for
  network, process and file-writing calls.
- Skill folders are taken only from the app's own skill-loading messages, never from tool output or web pages
  that ended up in a transcript. UNC network paths found in transcripts (such as `\\server\share`, in any
  spelling) are ignored.
- The output contains your skill names, their descriptions (with `--template`) and the session id (in full
  with `--json`): look at it before you share it.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, nothing to report; also `--history` and `--template` when a listing is found |
| 1 | No initial listing found |
| 2 | Usage or input error |
| 3 | A skill without description in the measured listing, whatever the reason (budget, name-only, no description) |

With `--simulate` the exit code reflects the simulation only: 0 within the target, 3 over.

## Tests

```
python -m unittest discover -s tests -v
```

Use `python3` on macOS and Linux. The tests use synthetic transcripts only, including a mid-session update
that must be ignored; nothing reads your real Claude folder. The link test uses a symbolic link or, on
Windows without the right to create one, a junction; it is skipped only where neither is possible.

## Kit Regia

This tool comes from the author's **Kit Regia**, a personal set of skills and scripts that, before each
task, picks the right skills, model and effort and keeps costs down. Questions, ideas, or interest in the
kit: open an Issue in this repository.

## License

MIT, © 2026 Gianluca Vega: see [LICENSE](LICENSE).
