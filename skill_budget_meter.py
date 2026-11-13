#!/usr/bin/env python3
"""skill-budget-meter 1.1.0 (2026-11-13): how much of the Claude Code skill listing fits in its budget?

Claude Code gives the model a listing of the available skills, one "- name: description" line each. The
official documentation (https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short) says the
listing has a character budget of 1% of the model's context window: when it overflows, the descriptions of
the skills invoked least are dropped first, and each entry (description plus when_to_use) is capped at 1,536
characters. With the author's models, which have a 1M-token context window, the cut measured about 30,000
characters (13 Nov 2026). With another model, or with skillListingBudgetFraction or
SLASH_COMMAND_TOOL_CHAR_BUDGET set, your cap differs: the window is counted in tokens and the cap in
characters, so measure it with --storico rather than computing it, and pass it with --cap.

The script reads the transcripts Claude Code saves on this computer (<config>/projects/*/*.jsonl, where
<config> is $CLAUDE_CONFIG_DIR or ~/.claude), takes the latest INITIAL skill listing (mid-session updates
contain only the changed skills and are ignored) and reports its size, the skills shown without description,
the size the listing would have with every description, the longest descriptions and, on request, a
simulation of new descriptions. Full descriptions of hidden skills come from the SKILL.md files it can find.
It complements /doctor and /context: the names of the skills hidden now, the full total, the room per class,
the history of the listings and a simulation before installing.

Usage (python3 on macOS and Linux):
    python skill_budget_meter.py                     measure the latest initial listing
    python skill_budget_meter.py --simula new.json   simulate {"name": "new description" or null}
    python skill_budget_meter.py --modello           template for --simula with the current descriptions
    python skill_budget_meter.py --storico           one line per initial listing found, and the estimated cap
    Options: --tetto/--cap N, --margine/--margin N, --max-voce/--entry-cap N, --prime/--top N, --json,
             --lingua/--lang it|en, --mie/--mine PATTERN, --cartella/--dir DIR,
             --trascrizioni/--transcripts DIR, --recenti/--recent N

Guarantees: read-only (it writes no file), no network, Python 3.10+ standard library only (Python 3.7 to 3.9
stop with a message). Network (UNC) and relative paths found in transcripts are ignored.
Exit codes: 0 ok, 1 no initial listing found, 2 usage or input error, 3 a skill shown without description,
whatever the reason (budget, name-only, no description). With --simula the exit code reflects the simulation
only: 0 within the target, 3 over.

Copyright (c) 2026 Gianluca Vega
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import locale
import os
import re
import string
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("skill-budget-meter needs Python 3.10 or later")

VERSION = "1.1.0"
DEFAULT_CAP = 30000  # the author's measurement (13 Nov 2026, 1M-token context models), not an official figure
DEFAULT_MARGIN = 600
DEFAULT_ENTRY_CAP = 1536  # the documented per-entry cap (skillListingMaxDescChars): description + when_to_use
DEFAULT_TOP = 10
DEFAULT_RECENT = 40
OWN, THIRD, BUILTIN = "own", "third_party", "builtin"
MARKER = "Base directory for this skill: "
MARKER_RE = re.compile(re.escape(MARKER) + r"([^\r\n]+)")  # used with match(): only at the start of a text block
LINE_RE = re.compile(r"^- ([^\s:]+(?::[^\s:]+)?)(?::(?: .*)?)?$")
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:(?:[ \t]+(.*))?$")
PRUNE = {"node_modules", ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache"}
MAX_DEPTH = 7

MESSAGES = {
    "it": {
        "parser": "Misura l'elenco delle skill che Claude Code passa al modello: quanto pesa, quali skill restano "
                  "senza descrizione, quanto spazio resta. Sola lettura, nessuna rete.",
        "epilog": "Uscite: 0 tutto bene, 1 nessun elenco trovato, 2 errore d'uso o di input, 3 skill senza "
                  "descrizione. Con --simula l'uscita riflette solo la simulazione: 0 entro l'obiettivo, 3 oltre.",
        "h_simulate": "file JSON {\"nome\": \"descrizione nuova\" o null}: simula descrizioni cambiate, skill nuove "
                      "(nome assente dall'elenco) o tolte (null)",
        "h_cap": "tetto dell'elenco in caratteri (predefinito %(default)s: misura dell'autore con modelli da 1M di token "
                 "di contesto). Il budget è l'1%% della finestra di contesto, che si conta in token: misura il tuo "
                 "tetto con --storico invece di calcolarlo",
        "h_margin": "margine di sicurezza sotto il tetto (predefinito %(default)s)",
        "h_entry_cap": "tetto di ogni voce, descrizione più when_to_use (predefinito %(default)s, come "
                       "skillListingMaxDescChars)",
        "h_top": "quante descrizioni più lunghe mostrare (predefinito %(default)s)",
        "h_json": "uscita in JSON",
        "h_lang": "lingua dei messaggi: it o en (predefinita: quella del sistema)",
        "h_mine": "nome o modello delle TUE skill di plugin, per esempio \"mio-plugin:*\" (ripetibile, anche con "
                  "le virgole)",
        "h_dir": "cartella in più dove cercare i SKILL.md (ripetibile)",
        "h_transcripts": "cartella delle trascrizioni (predefinita: <config>/projects)",
        "h_recent": "quante sessioni recenti leggere (predefinito %(default)s; 0 = tutte)",
        "h_history": "una riga per ogni elenco iniziale trovato, più il tetto stimato",
        "h_template": "stampa un modello JSON per --simula con le descrizioni attuali",
        "h_version": "mostra la versione ed esce",
        "bad_number": "valore non valido per {opt}: {value}",
        "classes": {OWN: "tue", THIRD: "di terzi", BUILTIN: "integrate"},
        "header": "skill-budget-meter {version} · elenco iniziale del {when} · Claude Code {app} ({entry}) · "
                  "sessione {session}",
        "listing": "Elenco reale: {chars} caratteri (tetto {cap}) · {skills} skill · con descrizione {shown} · "
                   "SENZA {hidden}",
        "utf16": "  In unità UTF-16, come le conta JavaScript (un'emoji vale 2): {units}",
        "hidden_names": "  Senza descrizione: {names}",
        "parse_warning": "  Avviso: la ricostruzione dell'elenco dà {rebuilt} caratteri invece di {chars}: il "
                         "formato potrebbe essere cambiato.",
        "names_mismatch": "  Avviso: il campo names dell'elenco non corrisponde al testo; le skill sono state "
                          "divise con lo schema \"- nome:\" e i conteggi possono essere imprecisi.",
        "below_cap": "  Avviso: l'elenco ha skill senza descrizione ma è ben sotto il tetto di {cap}: il tuo tetto è "
                     "probabilmente più basso (lancia --storico, poi imposta --tetto), oppure quelle skill sono "
                     "name-only o senza descrizione. Fino ad allora obiettivo e simulazione non sono affidabili.",
        "full": "Con tutte le descrizioni: {chars} caratteri · obiettivo {target} (tetto {cap} meno margine "
                "{margin}) · {verdict}",
        "over": "OLTRE di {n}",
        "within": "ENTRO, restano {n}",
        "class_row": "  {label:<10} {skills:>4} skill · {chars:>7} caratteri · senza descrizione {hidden}",
        "own_budget": "  Spazio per le tue skill: {budget} caratteri; oggi ne usano {used}{cut}",
        "own_cut": " (da tagliare {n})",
        "own_hint": "  Le tue skill di plugin non si riconoscono da sole: indicale con --mie \"plugin:*\".",
        "older": "  Nota: descrizioni nascoste prese dall'elenco più recente, di qualsiasi sessione letta, in cui la "
                 "skill era mostrata: {n} ({names}).",
        "unknown": "  Attenzione: {n} skill nascoste senza SKILL.md trovato ({names}): il totale è per difetto. "
                   "Indica la loro cartella con --cartella.",
        "entry_cap": "  Oltre il tetto per voce di {cap} caratteri, contate fino al tetto: {n} ({names}).",
        "md_differs": "  Nota: {d} delle {c} descrizioni mostrate nell'elenco differiscono dal loro SKILL.md "
                      "(modificato dopo, o scritto diversamente nell'elenco): i totali che usano il testo dei SKILL.md "
                      "sono stime.",
        "top": "Descrizioni più lunghe:",
        "top_row": "  {rank:>2}. {chars:>6}  {name}  ({label}{hidden})",
        "top_hidden": ", nascosta",
        "now_hidden": "Elenco misurato: skill senza descrizione: {n}.",
        "simulation": "Simulazione ({file}): {chars} caratteri · cambiate {changed} · nuove {added} · tolte "
                      "{removed} · {verdict}",
        "sim_added": "  Nuove, cioè assenti dall'elenco (controlla che il nome sia giusto): {names}",
        "sim_missing": "  Avviso: da togliere ma assenti dall'elenco: {names}",
        "sim_within": "Esito della simulazione: entro l'obiettivo (uscita 0: riflette solo la simulazione).",
        "sim_over": "Esito della simulazione: oltre l'obiettivo di {n} (uscita 3): accorcia altre descrizioni.",
        "cap_check": " Controlla l'avviso sul tetto più sopra.",
        "verdict_hidden": "Esito: skill senza descrizione: {n}. Il modello ne vede solo il nome, quindi difficilmente "
                          "le sceglierà da sé: accorcia le descrizioni più lunghe e verifica con --simula.",
        "verdict_ok": "Esito: tutte le skill hanno la descrizione.",
        "no_listing": "Nessun elenco iniziale di skill trovato in {folder} (sessioni lette: {n}). Apri una "
                      "sessione di Claude Code e riprova, oppure indica la cartella con --trascrizioni.",
        "err_file": "Impossibile leggere {file}: {error}",
        "err_json": "{file} non è un oggetto JSON {{\"nome\": \"descrizione\"}} valido: {error}",
        "err_value": "Valore non valido per {key}: serve una stringa o null.",
        "err_ambiguous": "Nome ambiguo: {key} corrisponde a {names}. Usa il nome completo con il prefisso del "
                         "plugin.",
        "history": "Elenchi iniziali trovati: {n} (sessioni lette: {files})",
        "history_row": "  {when}  Claude Code {app:<9} {entry:<15} {skills:>4} skill {chars:>7} caratteri "
                       "senza descrizione {hidden:>3}",
        "estimated_cap": "Tetto stimato: {cap} caratteri, l'elenco più lungo fra quelli con skill senza descrizione. "
                         "Vale solo se nessuna tua skill è name-only o priva di descrizione; con più modelli è il "
                         "tetto più alto visto.",
        "no_estimate": "Tetto stimato: non disponibile (nessun elenco con skill senza descrizione).",
    },
    "en": {
        "parser": "Measure the skill listing that Claude Code gives the model: its size, which skills are left "
                  "without description, how much room is left. Read-only, no network.",
        "epilog": "Exit codes: 0 ok, 1 no listing found, 2 usage or input error, 3 skills without description. "
                  "With --simulate the exit code reflects the simulation only: 0 within the target, 3 over.",
        "h_simulate": "JSON file {\"name\": \"new description\" or null}: simulate changed descriptions, new skills "
                      "(name not in the listing) or removed ones (null)",
        "h_cap": "listing cap in characters (default %(default)s: the author's measurement with 1M-token context "
                 "models). The budget is 1%% of the context window, which is counted in tokens: measure your cap "
                 "with --history instead of computing it",
        "h_margin": "safety margin below the cap (default %(default)s)",
        "h_entry_cap": "cap of each entry, description plus when_to_use (default %(default)s, like "
                       "skillListingMaxDescChars)",
        "h_top": "how many of the longest descriptions to show (default %(default)s)",
        "h_json": "JSON output",
        "h_lang": "message language: it or en (default: the system's)",
        "h_mine": "name or pattern of YOUR plugin skills, for example \"my-plugin:*\" (repeatable, commas allowed)",
        "h_dir": "extra folder where SKILL.md files are searched (repeatable)",
        "h_transcripts": "transcripts folder (default: <config>/projects)",
        "h_recent": "how many recent sessions to read (default %(default)s; 0 = all)",
        "h_history": "one line per initial listing found, plus the estimated cap",
        "h_template": "print a JSON template for --simulate with the current descriptions",
        "h_version": "show the version and exit",
        "bad_number": "invalid value for {opt}: {value}",
        "classes": {OWN: "yours", THIRD: "third-party", BUILTIN: "built-in"},
        "header": "skill-budget-meter {version} · initial listing of {when} · Claude Code {app} ({entry}) · "
                  "session {session}",
        "listing": "Actual listing: {chars} characters (cap {cap}) · {skills} skills · with description {shown} · "
                   "WITHOUT {hidden}",
        "utf16": "  In UTF-16 units, as JavaScript counts them (an emoji counts 2): {units}",
        "hidden_names": "  Without description: {names}",
        "parse_warning": "  Warning: rebuilding the listing gives {rebuilt} characters instead of {chars}: the "
                         "format may have changed.",
        "names_mismatch": "  Warning: the listing's names field does not match its text; skills were split by the "
                          "\"- name:\" pattern and the counts may be off.",
        "below_cap": "  Warning: the listing has skills without description but is well below the cap of {cap}: "
                     "your cap is probably lower (run --history, then set --cap), or those skills are name-only or "
                     "have no description. Until then the target and the simulation are not reliable.",
        "full": "With every description: {chars} characters · target {target} (cap {cap} minus margin {margin}) "
                "· {verdict}",
        "over": "OVER by {n}",
        "within": "WITHIN, {n} left",
        "class_row": "  {label:<11} {skills:>4} skills · {chars:>7} characters · without description {hidden}",
        "own_budget": "  Room for your skills: {budget} characters; they use {used} today{cut}",
        "own_cut": " (cut {n})",
        "own_hint": "  Your plugin skills cannot be recognised automatically: mark them with --mine \"plugin:*\".",
        "older": "  Note: hidden descriptions taken from the most recent listing, from any session read, that "
                 "showed the skill: {n} ({names}).",
        "unknown": "  Warning: {n} hidden skills without a SKILL.md found ({names}): the total is an underestimate. "
                   "Point to their folder with --dir.",
        "entry_cap": "  Over the per-entry cap of {cap} characters, counted up to the cap: {n} ({names}).",
        "md_differs": "  Note: {d} of {c} descriptions shown in the listing differ from their SKILL.md (edited "
                      "since, or written differently in the listing): totals that use SKILL.md text are estimates.",
        "top": "Longest descriptions:",
        "top_row": "  {rank:>2}. {chars:>6}  {name}  ({label}{hidden})",
        "top_hidden": ", hidden",
        "now_hidden": "Measured listing: skills without description: {n}.",
        "simulation": "Simulation ({file}): {chars} characters · changed {changed} · new {added} · removed "
                      "{removed} · {verdict}",
        "sim_added": "  New, i.e. not in the listing (check the spelling): {names}",
        "sim_missing": "  Warning: to be removed but not in the listing: {names}",
        "sim_within": "Result of the simulation: within the target (exit code 0: it reflects the simulation only).",
        "sim_over": "Result of the simulation: over the target by {n} (exit code 3): shorten more descriptions.",
        "cap_check": " Check the cap warning above.",
        "verdict_hidden": "Result: skills without description: {n}. The model sees only their name, so it is unlikely "
                          "to choose them on its own: shorten the longest descriptions and check with --simulate.",
        "verdict_ok": "Result: every skill has its description.",
        "no_listing": "No initial skill listing found in {folder} (sessions read: {n}). Open a Claude Code session "
                      "and try again, or point to the folder with --transcripts.",
        "err_file": "Cannot read {file}: {error}",
        "err_json": "{file} is not a valid JSON object {{\"name\": \"description\"}}: {error}",
        "err_value": "Invalid value for {key}: a string or null is required.",
        "err_ambiguous": "Ambiguous name: {key} matches {names}. Use the full name with the plugin prefix.",
        "history": "Initial listings found: {n} (sessions read: {files})",
        "history_row": "  {when}  Claude Code {app:<9} {entry:<15} {skills:>4} skills {chars:>7} characters "
                       "without description {hidden:>3}",
        "estimated_cap": "Estimated cap: {cap} characters, the longest listing among those with skills without "
                         "description. It holds only if none of your skills is name-only or lacks a description; "
                         "across several models it is the highest cap seen.",
        "no_estimate": "Estimated cap: not available (no listing had skills without description).",
    },
}


class InputError(Exception):
    """A user input problem: the message key and its fields, printed in the chosen language."""

    def __init__(self, message: str, **fields: object) -> None:
        super().__init__(message)
        self.key, self.fields = message, fields


@dataclass
class Listing:
    content: str
    names: list
    timestamp: str
    app_version: str
    entrypoint: str
    session: str
    cwd: str
    order: tuple
    initial: bool = True


@dataclass
class Entry:
    name: str
    head: str
    more: list = field(default_factory=list)
    full: str = ""
    source: str = "unknown"
    owner: str = THIRD

    @property
    def shown(self) -> str:
        prefix = f"- {self.name}: "
        first = self.head[len(prefix):] if self.head.startswith(prefix) else ""
        return "\n".join([first] + self.more) if self.more else first


@dataclass
class SkillFile:
    name: str
    description: str
    path: Path
    kind: str
    plugin: str
    mtime: float


# ---------------------------------------------------------------- language, numbers, output helpers

def detect_language(argv: list) -> str:
    for i, arg in enumerate(argv):
        if arg in ("--lingua", "--lang") and i + 1 < len(argv):
            return argv[i + 1].lower() if argv[i + 1].lower() in MESSAGES else "en"
        for prefix in ("--lingua=", "--lang="):
            if arg.startswith(prefix):
                value = arg[len(prefix):].lower()
                return value if value in MESSAGES else "en"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value and value.split(".")[0] not in ("C", "POSIX"):
            return "it" if value.lower().startswith("it") else "en"
    try:
        current = locale.getlocale()[0] or ""
    except (ValueError, TypeError):
        current = ""
    return "it" if current.lower().startswith(("it", "italian")) else "en"


def fmt(number: int, lang: str) -> str:
    text = f"{number:,}"
    return text.replace(",", ".") if lang == "it" else text


def format_ts(stamp: str) -> str:
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return stamp or "?"
    if moment.tzinfo is None:
        return moment.strftime("%Y-%m-%d %H:%M")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def safe_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def emit_json(data: object) -> None:
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "").replace("_", "")
    print(json.dumps(data, ensure_ascii=encoding != "utf8", indent=2))


def mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


# ---------------------------------------------------------------- transcripts

def config_dir() -> Path:
    custom = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(custom).expanduser() if custom else Path.home() / ".claude"


def local_path(text: str):
    """A local absolute path, or None: network (UNC) and relative paths read from transcripts are never used."""
    text = (text or "").strip()
    if not text or text[:2].replace("/", "\\") == "\\\\":  # two leading slashes of either kind: a network share
        return None
    try:
        path = Path(text)
    except (TypeError, ValueError):
        return None
    if path.drive[:2].replace("/", "\\") == "\\\\":  # anything else that pathlib reads as a network share
        return None
    return path if path.is_absolute() else None


def recent_transcripts(folder: Path, recent: int) -> list:
    try:
        files = [p for p in folder.glob("*/*.jsonl") if p.is_file()]
    except OSError:
        return []
    files.sort(key=mtime, reverse=True)
    return files if recent <= 0 else files[:recent]


def strings_in(value: object):
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def listing_record(record: dict, path: Path, file_time: float, number: int):
    """A skill listing attachment. initial=False marks a mid-session update, which lists only the changed
    skills: it is never measured, it only lends descriptions (see remembered_descriptions)."""
    attachment = record.get("attachment")
    if not isinstance(attachment, dict) or attachment.get("type") != "skill_listing":
        return None
    if record.get("isSidechain") is True:
        return None  # a sub-agent's listing, not the main session's
    content = attachment.get("content")
    if not isinstance(content, str) or not content:
        return None
    names = attachment.get("names")
    names = [n for n in names if isinstance(n, str)] if isinstance(names, list) else []
    return Listing(content, names, str(record.get("timestamp") or ""), str(record.get("version") or "?"),
                   str(record.get("entrypoint") or "?"), path.stem, str(record.get("cwd") or ""),
                   (file_time, number), attachment.get("isInitial") is not False)


def remembered_descriptions(listings: list) -> dict:
    """name -> the most recent description shown for it in any listing read (initial or update)."""
    memory = {}
    for item in sorted(listings, key=lambda i: (i.timestamp, i.order)):
        for entry in parse_listing(item.content, item.names)[1]:
            if entry.shown.strip():
                memory[entry.name] = entry.shown
    return memory


def scan(files: list) -> tuple:
    """Skill listings (initial and updates) and the folders of the skills loaded in those sessions. The folders
    come only from the app's own skill-loading messages (user records with isMeta true, whose text block starts
    with the marker), never from tool results, web pages or other text that ended up in a transcript."""
    listings, bases, seen = [], [], set()
    for path in files:
        file_time = mtime(path)
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for number, line in enumerate(handle):
                has_listing, has_marker = '"skill_listing"' in line, MARKER in line
                if not (has_listing or has_marker):
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                if has_marker and record.get("type") == "user" and record.get("isMeta") is True:
                    for text in strings_in(record.get("message")):
                        match = MARKER_RE.match(text)  # the app puts it first; a line further down is not trusted
                        base = match.group(1).strip() if match else ""
                        if base and base not in seen:
                            seen.add(base)
                            bases.append(base)
                if has_listing:
                    item = listing_record(record, path, file_time, number)
                    if item is not None:
                        listings.append(item)
    return listings, bases


def parse_listing(content: str, names: list) -> tuple:
    """(lines before the first skill, entries, names_mismatch). Lines that do not start a skill continue the
    previous one. names_mismatch is True when the names field does not line up with the text: the entries then
    come from the "- name:" line pattern."""
    preamble, entries, position = [], [], 0
    for line in content.split("\n"):
        name = None
        if names:
            if position < len(names):
                expected = names[position]
                if line in (f"- {expected}", f"- {expected}:") or line.startswith(f"- {expected}: "):
                    name, position = expected, position + 1
        else:
            match = LINE_RE.match(line)
            name = match.group(1) if match else None
        if name is not None:
            entries.append(Entry(name, line))
        elif entries:
            entries[-1].more.append(line)
        else:
            preamble.append(line)
    if names and position < len(names):
        preamble, entries, _ = parse_listing(content, [])  # names and text do not line up: use the line pattern
        return preamble, entries, True
    return preamble, entries, False


def line_length(name: str, description: str) -> int:
    return len(f"- {name}: {description}") if description else len(f"- {name}")


def listing_length(preamble: list, pairs: list) -> int:
    lines = list(preamble) + [f"- {n}: {d}" if d else f"- {n}" for n, d in pairs]
    return len("\n".join(lines))


# ---------------------------------------------------------------- SKILL.md files

def _dedent(block: list) -> list:
    indents = [len(line) - len(line.lstrip(" \t")) for line in block if line.strip()]
    cut = min(indents) if indents else 0
    lines = [line[cut:].rstrip() for line in block]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _fold(lines: list) -> str:
    text, previous_blank = "", True
    for line in lines:
        if not line.strip():
            text += "\n"
            previous_blank = True
            continue
        if text and not previous_blank:
            text += " "
        text += line
        previous_blank = False
    return text


def _quoted(text: str) -> str:
    quote, out, i = text[0], [], 1
    escapes = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", '"': '"', "\\": "\\", "/": "/", " ": " "}
    while i < len(text):
        char = text[i]
        if quote == "'" and char == "'":
            if text[i + 1:i + 2] == "'":
                out.append("'")
                i += 2
                continue
            break
        if quote == '"' and char == "\\" and i + 1 < len(text):
            code = text[i + 1]
            size = {"x": 2, "u": 4, "U": 8}.get(code, 0)
            digits = text[i + 2:i + 2 + size]
            if size and len(digits) == size and all(c in string.hexdigits for c in digits):
                out.append(chr(int(digits, 16)))
                i += 2 + size
                continue
            out.append(escapes.get(code, code))
            i += 2
            continue
        if quote == '"' and char == '"':
            break
        out.append(char)
        i += 1
    return "".join(out)


def _scalar(rest: str, block: list) -> str:
    if rest[:1] in ("|", ">"):
        lines = _dedent(block)
        return ("\n".join(lines) if rest[0] == "|" else _fold(lines)).strip()
    if rest[:1] in ('"', "'"):
        return _quoted(" ".join([rest] + [line.strip() for line in block if line.strip()])).strip()
    text = " ".join([rest] + [line.strip() for line in block if line.strip()])
    return re.split(r"\s#", text, maxsplit=1)[0].strip()


def frontmatter(text: str) -> dict:
    """Top-level keys (name, description, when_to_use...) of a SKILL.md YAML front matter, in the subset skills
    use, without dependencies."""
    lines = text.lstrip(chr(0xFEFF)).splitlines()  # chr(0xFEFF): a byte order mark left by some editors
    if not lines or lines[0].rstrip() != "---":
        return {}
    for end in range(1, len(lines)):
        if lines[end].rstrip() in ("---", "..."):
            break
    else:
        return {}
    body, result, i = lines[1:end], {}, 0
    while i < len(body):
        match = KEY_RE.match(body[i])
        if not match:
            i += 1
            continue
        j = i + 1
        while j < len(body) and (not body[j].strip() or body[j][:1] in (" ", "\t")):
            j += 1
        result[match.group(1)] = _scalar((match.group(2) or "").strip(), body[i + 1:j])
        i = j
    return result


_PLUGIN_NAMES: dict = {}


def plugin_name(skill_md: Path) -> str:
    """Name from .claude-plugin/plugin.json for <plugin>/skills/<skill>/SKILL.md, else ''."""
    if skill_md.parent.parent.name != "skills":
        return ""
    root = skill_md.parent.parent.parent
    if root not in _PLUGIN_NAMES:
        name = ""
        try:
            data = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
            name = str(data.get("name") or "") if isinstance(data, dict) else ""
        except (OSError, ValueError):
            pass
        _PLUGIN_NAMES[root] = name
    return _PLUGIN_NAMES[root]


def skill_files(root: Path):
    """SKILL.md files under root, at most MAX_DEPTH levels down, following symbolic links. A folder already
    visited through another path (a link loop, or two links to the same place) is not walked again."""
    base_depth, visited = len(root.parts), set()
    for current, dirs, files in os.walk(root, followlinks=True):
        real = os.path.realpath(current)
        if real in visited:
            dirs[:] = []
            continue
        visited.add(real)
        depth = len(Path(current).parts) - base_depth
        dirs[:] = [d for d in dirs if d not in PRUNE] if depth < MAX_DEPTH else []
        if "SKILL.md" in files:
            yield Path(current) / "SKILL.md"


def skill_roots(config: Path, listing: Listing, extra: list, bases: list) -> list:
    """(folder, kind, pattern). Walked (pattern None): personal, project, extra (--dir) and plugin folders. For
    each skill loaded in a recent session: its sibling skills (*/SKILL.md) and, when it belongs to a plugin, the
    skills of the plugins next to that one (*/skills/*/SKILL.md)."""
    roots = [(config / "skills", "personal", None)]
    cwd = local_path(listing.cwd)
    if cwd is not None:
        roots.append((cwd / ".claude" / "skills", "project", None))
    roots += [(Path(folder).expanduser(), "extra", None) for folder in extra]
    roots.append((config / "plugins", "plugin", None))
    home = Path.home()
    for base in bases:
        folder = local_path(base)
        if folder is None:
            continue
        try:
            if not (folder / "SKILL.md").is_file():
                continue
        except (OSError, ValueError):
            continue
        owner = folder.parent.parent  # the plugin folder, or the folder holding personal or project skills
        roots.append((folder.parent, "project" if owner.name == ".claude" else "found", "*/SKILL.md"))
        if folder.parent.name == "skills" and owner.name != ".claude" and owner != config:
            above = owner.parent  # the folder that holds this plugin and its siblings
            if above != above.parent and above != home and above not in home.parents:
                roots.append((above, "found", "*/skills/*/SKILL.md"))
    return roots


def build_index(roots: list) -> dict:
    index, seen = {}, set()
    for root, kind, pattern in roots:
        try:
            if not root.is_dir():
                continue
            paths = sorted(root.glob(pattern)) if pattern else skill_files(root)
        except OSError:
            continue
        for path in paths:
            try:
                key = path.resolve()
            except (OSError, RuntimeError):  # RuntimeError: a link loop, on Python 3.10 to 3.12
                key = path
            if key in seen:
                continue
            seen.add(key)
            try:
                meta = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            name = (meta.get("name") or path.parent.name).strip()
            # the listing shows when_to_use after the description; the separator is not documented: a space
            text = " ".join(part for part in (meta.get("description", ""), meta.get("when_to_use", "")) if part)
            index.setdefault(name, []).append(SkillFile(name, text, path, kind, plugin_name(path), mtime(path)))
    return index


def match_skill(entry_name: str, index: dict):
    plugin, _, short = entry_name.rpartition(":")
    personal = ("personal", "project")
    candidates = [c for c in index.get(short, [])
                  if ((c.kind not in personal) == bool(plugin) or c.kind == "extra")
                  and not (plugin and c.plugin and c.plugin != plugin)]  # never another plugin's skill
    if not candidates:
        return None
    return max(candidates, key=lambda c: (bool(plugin) and c.plugin == plugin,
                                         "marketplaces" not in c.path.parts, c.mtime))


def classify(entry_name: str, found, patterns: list) -> str:
    lowered = entry_name.lower()
    if any(fnmatch.fnmatchcase(lowered, pattern.lower()) for pattern in patterns):
        return OWN
    if ":" not in entry_name:
        return OWN if found is not None else BUILTIN
    return THIRD


# ---------------------------------------------------------------- analysis and simulation

def analyse(listing: Listing, preamble: list, entries: list, index: dict, patterns: list, cap: int, margin: int,
            top: int, memory: dict | None = None, entry_cap: int = DEFAULT_ENTRY_CAP,
            names_mismatch: bool = False) -> dict:
    compared = equal = 0
    memory = memory or {}
    for entry in entries:
        found = match_skill(entry.name, index)
        entry.owner = classify(entry.name, found, patterns)
        shown = entry.shown
        if shown.strip():
            entry.full, entry.source = shown, "listing"
            if found is not None and found.description:
                compared += 1
                equal += " ".join(found.description[:entry_cap].split()) == " ".join(shown[:entry_cap].split())
        elif found is not None and found.description:
            entry.full, entry.source = found.description, "skill_md"
        elif entry.name in memory:
            entry.full, entry.source = memory[entry.name], "older_listing"
        else:
            entry.full, entry.source = "", "unknown"

    def size(entry: Entry) -> int:
        return min(len(entry.full), entry_cap)

    target = cap - margin
    full = listing_length(preamble, [(e.name, e.full[:entry_cap]) for e in entries])
    hidden = [e.name for e in entries if not e.shown.strip()]
    classes = {key: {"skills": 0, "chars": 0, "without_description": 0} for key in (OWN, THIRD, BUILTIN)}
    for entry in entries:
        bucket = classes[entry.owner]
        bucket["skills"] += 1
        bucket["chars"] += line_length(entry.name, entry.full[:entry_cap]) + 1
        bucket["without_description"] += 0 if entry.shown.strip() else 1
    own_budget = target - (full - classes[OWN]["chars"]) if classes[OWN]["skills"] else None
    longest = sorted(entries, key=lambda e: (-size(e), e.name))[:top]
    return {
        "tool": "skill-budget-meter",
        "version": VERSION,
        "listing": {
            "session": listing.session, "timestamp": listing.timestamp, "app_version": listing.app_version,
            "entrypoint": listing.entrypoint, "chars": len(listing.content),
            "utf16_units": len(listing.content.encode("utf-16-le", "surrogatepass")) // 2,
            "rebuilt_chars": listing_length(preamble, [(e.name, e.shown) for e in entries]),
            "names_mismatch": names_mismatch,
            # hidden skills in a listing far below the cap: the cap is wrong for this model, or they are name-only
            "cut_well_below_cap": bool(hidden) and len(listing.content) < 0.9 * cap,
            "skills": len(entries), "with_description": len(entries) - len(hidden), "without_description": hidden,
        },
        "full": {"chars": full, "cap": cap, "margin": margin, "target": target, "room": target - full,
                 "entry_cap": entry_cap, "over_entry_cap": [e.name for e in entries if len(e.full) > entry_cap],
                 "unknown_full_description": [e.name for e in entries if e.source == "unknown"],
                 "from_older_listings": [e.name for e in entries if e.source == "older_listing"]},
        "by_class": classes,
        "own_budget": own_budget,
        "longest": [{"name": e.name, "chars": size(e), "class": e.owner, "shown": bool(e.shown.strip())}
                    for e in longest],
        "skills": [{"name": e.name, "class": e.owner, "shown": bool(e.shown.strip()), "shown_chars": len(e.shown),
                    "full_chars": size(e), "source": e.source} for e in entries],
        "skill_md_check": {"compared": compared, "equal": equal},
    }


def read_text_any(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8")


def load_changes(path: Path) -> dict:
    try:
        text = read_text_any(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError("err_file", file=path, error=exc) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise InputError("err_json", file=path.name, error=exc) from exc
    if not isinstance(data, dict):
        raise InputError("err_json", file=path.name, error=type(data).__name__)
    return data


def simulate(preamble: list, entries: list, changes: dict, target: int, entry_cap: int = DEFAULT_ENTRY_CAP) -> dict:
    current = {e.name: e.full for e in entries}
    by_short = {}
    for name in current:
        by_short.setdefault(name.rpartition(":")[2], []).append(name)
    changed, added, removed, not_found = [], [], [], []
    for key, value in changes.items():
        if not key.strip() or (value is not None and not isinstance(value, str)):
            raise InputError("err_value", key=json.dumps(key, ensure_ascii=False))
        hit = key if key in current else None
        if hit is None and ":" not in key:
            hits = by_short.get(key, [])
            if len(hits) > 1:
                raise InputError("err_ambiguous", key=key, names=", ".join(hits))
            hit = hits[0] if hits else None
        if value is None:
            if hit is not None and hit in current:
                del current[hit]
                removed.append(hit)
            else:
                not_found.append(key)
        elif hit is not None and hit in current:
            current[hit] = value
            changed.append(hit)
        else:
            current[key] = value
            added.append(key)
    chars = listing_length(preamble, [(name, text[:entry_cap]) for name, text in current.items()])
    return {"chars": chars, "target": target, "room": target - chars, "within_target": chars <= target,
            "changed": changed, "added": added, "removed": removed, "not_found": not_found}


def template(entries: list) -> dict:
    own = [e for e in entries if e.owner == OWN]
    return {e.name: e.full for e in (own or entries)}


# ---------------------------------------------------------------- printing

def print_report(report: dict, lang: str) -> None:
    text = MESSAGES[lang]

    def n(value: int) -> str:
        return fmt(value, lang)

    def verdict(room: int) -> str:
        return text["within"].format(n=n(room)) if room >= 0 else text["over"].format(n=n(-room))

    listing, full, classes = report["listing"], report["full"], report["by_class"]
    hidden = listing["without_description"]
    print(text["header"].format(version=VERSION, when=format_ts(listing["timestamp"]), app=listing["app_version"],
                                entry=listing["entrypoint"], session=listing["session"][:8]))
    print(text["listing"].format(chars=n(listing["chars"]), cap=n(full["cap"]), skills=listing["skills"],
                                 shown=listing["with_description"], hidden=len(hidden)))
    if listing["utf16_units"] != listing["chars"]:
        print(text["utf16"].format(units=n(listing["utf16_units"])))
    if hidden:
        print(text["hidden_names"].format(names=", ".join(hidden)))
    if listing["rebuilt_chars"] != listing["chars"]:
        print(text["parse_warning"].format(rebuilt=n(listing["rebuilt_chars"]), chars=n(listing["chars"])))
    if listing["names_mismatch"]:
        print(text["names_mismatch"])
    if listing["cut_well_below_cap"]:
        print(text["below_cap"].format(cap=n(full["cap"])))
    print(text["full"].format(chars=n(full["chars"]), target=n(full["target"]), cap=n(full["cap"]),
                              margin=n(full["margin"]), verdict=verdict(full["room"])))
    for key in (OWN, THIRD, BUILTIN):
        bucket = classes[key]
        if bucket["skills"]:
            print(text["class_row"].format(label=text["classes"][key], skills=bucket["skills"],
                                           chars=n(bucket["chars"]), hidden=bucket["without_description"]))
    if report["own_budget"] is not None:
        used, budget = classes[OWN]["chars"], report["own_budget"]
        cut = text["own_cut"].format(n=n(used - budget)) if used > budget else ""
        print(text["own_budget"].format(budget=n(budget), used=n(used), cut=cut))
    elif classes[THIRD]["skills"]:
        print(text["own_hint"])
    if full["from_older_listings"]:
        print(text["older"].format(n=len(full["from_older_listings"]), names=", ".join(full["from_older_listings"])))
    if full["unknown_full_description"]:
        print(text["unknown"].format(n=len(full["unknown_full_description"]),
                                     names=", ".join(full["unknown_full_description"])))
    if full["over_entry_cap"]:
        print(text["entry_cap"].format(cap=n(full["entry_cap"]), n=len(full["over_entry_cap"]),
                                       names=", ".join(full["over_entry_cap"])))
    check = report["skill_md_check"]
    if check["equal"] < check["compared"]:
        print(text["md_differs"].format(d=check["compared"] - check["equal"], c=check["compared"]))
    if report["longest"]:
        print(text["top"])
        for rank, item in enumerate(report["longest"], 1):
            print(text["top_row"].format(rank=rank, chars=n(item["chars"]), name=item["name"],
                                         label=text["classes"][item["class"]],
                                         hidden="" if item["shown"] else text["top_hidden"]))
    simulation = report.get("simulation")
    if not simulation:
        print(text["verdict_hidden"].format(n=len(hidden)) if hidden else text["verdict_ok"])
        return
    if hidden:
        print(text["now_hidden"].format(n=len(hidden)))
    print(text["simulation"].format(file=simulation["file"], chars=n(simulation["chars"]),
                                    changed=len(simulation["changed"]), added=len(simulation["added"]),
                                    removed=len(simulation["removed"]), verdict=verdict(simulation["room"])))
    if simulation["added"]:
        print(text["sim_added"].format(names=", ".join(simulation["added"])))
    if simulation["not_found"]:
        print(text["sim_missing"].format(names=", ".join(simulation["not_found"])))
    result = text["sim_within"] if simulation["within_target"] else text["sim_over"].format(n=n(-simulation["room"]))
    print(result + (text["cap_check"] if listing["cut_well_below_cap"] else ""))


def print_history(listings: list, files: int, folder: Path, lang: str, as_json: bool) -> int:
    text = MESSAGES[lang]
    if not listings:
        print(text["no_listing"].format(folder=folder, n=files), file=sys.stderr)
        return 1
    rows = []
    for item in sorted(listings, key=lambda i: (i.timestamp, i.order)):
        _, entries, _ = parse_listing(item.content, item.names)
        rows.append({"timestamp": item.timestamp, "app_version": item.app_version, "entrypoint": item.entrypoint,
                     "session": item.session, "skills": len(entries), "chars": len(item.content),
                     "without_description": sum(1 for e in entries if not e.shown.strip())})
    cut = [row["chars"] for row in rows if row["without_description"]]
    estimated = max(cut) if cut else None  # a listing that lost descriptions was filled up to the budget
    if as_json:
        emit_json({"tool": "skill-budget-meter", "version": VERSION, "estimated_cap": estimated, "history": rows})
        return 0
    print(text["history"].format(n=len(rows), files=files))
    for row in rows:
        print(text["history_row"].format(when=format_ts(row["timestamp"]), app=row["app_version"],
                                         entry=row["entrypoint"], skills=row["skills"],
                                         chars=fmt(row["chars"], lang), hidden=row["without_description"]))
    print(text["estimated_cap"].format(cap=fmt(estimated, lang)) if estimated is not None else text["no_estimate"])
    return 0


# ---------------------------------------------------------------- command line

def build_parser(lang: str) -> argparse.ArgumentParser:
    text = MESSAGES[lang]
    parser = argparse.ArgumentParser(prog="skill_budget_meter.py", description=text["parser"],
                                     epilog=text["epilog"], allow_abbrev=False)
    parser.add_argument("--simula", "--simulate", dest="simulate", metavar="FILE.json", help=text["h_simulate"])
    parser.add_argument("--tetto", "--cap", dest="cap", type=int, default=DEFAULT_CAP, metavar="N",
                        help=text["h_cap"])
    parser.add_argument("--margine", "--margin", dest="margin", type=int, default=DEFAULT_MARGIN, metavar="N",
                        help=text["h_margin"])
    parser.add_argument("--max-voce", "--entry-cap", dest="entry_cap", type=int, default=DEFAULT_ENTRY_CAP,
                        metavar="N", help=text["h_entry_cap"])
    parser.add_argument("--prime", "--top", dest="top", type=int, default=DEFAULT_TOP, metavar="N",
                        help=text["h_top"])
    parser.add_argument("--json", action="store_true", help=text["h_json"])
    parser.add_argument("--lingua", "--lang", dest="lang", choices=sorted(MESSAGES), help=text["h_lang"])
    parser.add_argument("--mie", "--mine", dest="mine", action="append", default=[], metavar="PATTERN",
                        help=text["h_mine"])
    parser.add_argument("--cartella", "--dir", dest="dirs", action="append", default=[], metavar="DIR",
                        help=text["h_dir"])
    parser.add_argument("--trascrizioni", "--transcripts", dest="transcripts", metavar="DIR",
                        help=text["h_transcripts"])
    parser.add_argument("--recenti", "--recent", dest="recent", type=int, default=DEFAULT_RECENT, metavar="N",
                        help=text["h_recent"])
    parser.add_argument("--storico", "--history", dest="history", action="store_true", help=text["h_history"])
    parser.add_argument("--modello", "--template", dest="template", action="store_true", help=text["h_template"])
    parser.add_argument("--versione", "--version", action="version", version=f"skill-budget-meter {VERSION}",
                        help=text["h_version"])
    return parser


def main(argv: list | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    safe_streams()
    lang = detect_language(argv)
    parser = build_parser(lang)
    args = parser.parse_args(argv)
    lang = args.lang or lang
    text = MESSAGES[lang]
    checks = (("--tetto/--cap", args.cap, args.cap > 0),
              ("--margine/--margin", args.margin, 0 <= args.margin < args.cap),
              ("--max-voce/--entry-cap", args.entry_cap, args.entry_cap > 0),
              ("--prime/--top", args.top, args.top >= 0), ("--recenti/--recent", args.recent, args.recent >= 0))
    for option, value, ok in checks:
        if not ok:
            parser.error(text["bad_number"].format(opt=option, value=value))
    patterns = [p.strip() for item in args.mine for p in item.split(",") if p.strip()]
    config = config_dir()
    folder = Path(args.transcripts).expanduser() if args.transcripts else config / "projects"
    files = recent_transcripts(folder, args.recent)
    listings, bases = scan(files)
    initial = [item for item in listings if item.initial]
    if args.history:
        return print_history(initial, len(files), folder, lang, args.json)
    if not initial:
        print(text["no_listing"].format(folder=folder, n=len(files)), file=sys.stderr)
        return 1
    latest = max(initial, key=lambda item: (item.timestamp, item.order))
    preamble, entries, mismatch = parse_listing(latest.content, latest.names)
    index = build_index(skill_roots(config, latest, args.dirs, bases))
    report = analyse(latest, preamble, entries, index, patterns, args.cap, args.margin, args.top,
                     remembered_descriptions(listings), args.entry_cap, mismatch)
    if args.template:
        emit_json(template(entries))
        return 0
    code = 3 if report["listing"]["without_description"] else 0
    if args.simulate:
        try:
            simulation = simulate(preamble, entries, load_changes(Path(args.simulate)), report["full"]["target"],
                                  args.entry_cap)
        except InputError as exc:
            print(text[exc.key].format(**exc.fields), file=sys.stderr)
            return 2
        simulation["file"] = Path(args.simulate).name
        report["simulation"] = simulation
        code = 0 if simulation["within_target"] else 3  # with a simulation, the exit code reflects it only
    report["exit_code"] = code
    if args.json:
        emit_json(report)
    else:
        print_report(report, lang)
    return code


if __name__ == "__main__":
    sys.exit(main())
