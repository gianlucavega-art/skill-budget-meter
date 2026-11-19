#!/usr/bin/env python3
"""Restyle the top and the support section of README.md and README.it.md.

Idempotent: the blocks are delimited by <!-- hero:start/end --> and
<!-- support:start/end --> markers; a second run replaces them in place.
Usage: python assets/restyle_readme.py [--dry-run]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = "https://buy.stripe.com/3cI7sNcuX1121ZyeRDawo00"
KOFI = "https://ko-fi.com/gianlucavega"
CONSULT = "https://github.com/gianlucavega-art/skill-budget-meter/issues/new?title=Consulting"
STARS = "https://github.com/gianlucavega-art/skill-budget-meter/stargazers"
REPO = "https://github.com/gianlucavega-art/skill-budget-meter"

BADGES = (
    '<a href="LICENSE"><img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-22c55e?style=for-the-badge"></a> '
    '<img alt="Python 3, standard library" src="https://img.shields.io/badge/python-3%20%C2%B7%20stdlib-6366f1?style=for-the-badge&logo=python&logoColor=white"> '
    '<img alt="read-only, no network" src="https://img.shields.io/badge/read--only-no%20network-0ea5e9?style=for-the-badge"> '
    f'<a href="{KOFI}"><img alt="Ko-fi" src="https://img.shields.io/badge/Ko--fi-support-ff5e5b?style=for-the-badge&logo=ko-fi&logoColor=white"></a>'
)

HERO = {
    "en": f"""<!-- hero:start -->
<p align="center">
  <img src="assets/hero-en.svg" width="100%" alt="skill-budget-meter: which of your Claude Code skills lost their description? A budget bar overflows with 37 skills without description, then fits with 0.">
</p>

<p align="center">{BADGES}</p>

<p align="center">
  <b>🎯 Find the skills Claude can no longer see · 🧪 simulate shorter descriptions · 🔒 nothing leaves your PC</b><br>
  <a href="#quick-start">🚀 Quick start</a> · <a href="#what-was-measured">📊 Real data</a> · <a href="#simulate-before-you-install">🧪 Simulate</a> · <a href="#support-the-project">💖 Support</a> · <a href="README.it.md">🇮🇹 Italiano</a>
</p>
<!-- hero:end -->
""",
    "it": f"""<!-- hero:start -->
<p align="center">
  <img src="assets/hero-it.svg" width="100%" alt="skill-budget-meter: quali skill di Claude Code hanno perso la descrizione? La barra del budget trabocca con 37 skill senza descrizione, poi rientra con 0.">
</p>

<p align="center">{BADGES}</p>

<p align="center">
  <b>🎯 Trova le skill che Claude non vede più · 🧪 simula descrizioni più corte · 🔒 nulla esce dal tuo PC</b><br>
  <a href="README.md">🇬🇧 English</a> · <a href="#supporta-il-progetto">💖 Supporta il progetto</a>
</p>
<!-- hero:end -->
""",
}

SUPPORT = {
    "en": f"""<!-- support:start -->
## Support the project

<p align="center">
  <a href="{GUIDE}"><img src="assets/support-en.svg" width="100%" alt="37 to 0 in one day: step-by-step method, copy-ready description templates, checklists in English and Italian. PDF guide, 12 euro."></a>
</p>

<h3 align="center">🤔 How did 37 description-less skills drop to 0 in a single day?</h3>

<p align="center">The illustrated guide shows the exact path, step by step, so you can repeat it on your own setup.</p>

<table align="center">
<tr><td>📋</td><td><b>Step-by-step method</b> behind the 37 → 0 result</td></tr>
<tr><td>✍️</td><td><b>Copy-ready description templates</b> to paste and adapt</td></tr>
<tr><td>✅</td><td><b>Checklists</b> to run it yourself, in English and Italian</td></tr>
</table>

<p align="center">
  <a href="{GUIDE}"><img src="assets/btn-guide-en.svg" height="64" alt="Get the guide, 12 euro"></a>
</p>
<p align="center"><sub>PDF guide · English + Italian · one-time 12 € · no subscription</sub></p>

<br>

<table>
<tr>
<td width="50%" align="center" valign="top">
<h3>☕ Just want to say thanks?</h3>
A Ko-fi coffee keeps the free updates coming.<br><br>
<a href="{KOFI}"><img src="assets/btn-kofi-en.svg" height="56" alt="Buy me a coffee on Ko-fi"></a>
</td>
<td width="50%" align="center" valign="top">
<h3>🛠️ Want it done for you?</h3>
Paid audit of your skills and descriptions, routing checks and Claude Code cost settings.<br><br>
<a href="{CONSULT}"><img src="assets/btn-consult-en.svg" height="56" alt="Book a setup audit: open an Issue titled Consulting"></a>
</td>
</tr>
</table>

<p align="center">
  <a href="{STARS}"><img src="assets/btn-star-en.svg" height="48" alt="Star the repository"></a><br>
  <sub>⭐ A star helps other Claude Code users find this tool.</sub>
</p>

<p align="center"><b>P.S.</b> 💚 The code stays free under the MIT licence, and always will.</p>
<!-- support:end -->
""",
    "it": f"""<!-- support:start -->
## Supporta il progetto

<p align="center">
  <a href="{GUIDE}"><img src="assets/support-it.svg" width="100%" alt="Da 37 a 0 in un giorno: metodo passo passo, modelli di descrizioni pronti da copiare, liste di controllo in italiano e inglese. Guida PDF, 12 euro."></a>
</p>

<h3 align="center">🔍 Quante delle tue skill Claude non vede più, senza che tu lo sappia?</h3>

<p align="center">La guida illustrata mostra il percorso esatto, passo passo, per ripeterlo sul tuo sistema.</p>

<table align="center">
<tr><td>🧭</td><td><b>Il metodo passo passo</b> dietro il passaggio da 37 a 0</td></tr>
<tr><td>📝</td><td><b>Modelli di descrizioni</b> pronti da copiare e adattare</td></tr>
<tr><td>✅</td><td><b>Liste di controllo</b> illustrate, in italiano e inglese</td></tr>
</table>

<p align="center">
  <a href="{GUIDE}"><img src="assets/btn-guide-it.svg" height="64" alt="Acquista la guida, 12 euro"></a>
</p>
<p align="center"><sub>Guida PDF · italiano + inglese · 12 € una tantum · nessun abbonamento</sub></p>

<br>

<table>
<tr>
<td width="50%" align="center" valign="top">
<h3>☕ Vuoi solo dire grazie?</h3>
Un caffè su Ko-fi tiene vivi gli aggiornamenti gratuiti.<br><br>
<a href="{KOFI}"><img src="assets/btn-kofi-it.svg" height="56" alt="Offrimi un caffè su Ko-fi"></a>
</td>
<td width="50%" align="center" valign="top">
<h3>🛠️ Vuoi che lo faccia io?</h3>
Audit a pagamento di skill e descrizioni, controlli di instradamento e impostazioni dei costi di Claude Code.<br><br>
<a href="{CONSULT}"><img src="assets/btn-consult-it.svg" height="56" alt="Prenota un audit: apri una Issue intitolata Consulting"></a>
</td>
</tr>
</table>

<p align="center">
  <a href="{STARS}"><img src="assets/btn-star-it.svg" height="48" alt="Metti una stella al repository"></a><br>
  <sub>⭐ Una stella aiuta altri utenti di Claude Code a trovare lo strumento.</sub>
</p>

<p align="center"><b>P.S.</b> 🚀 Il risultato è reale: il 13 novembre 2026 da 37 skill senza descrizione a 0 in un giorno. Il codice resta gratuito con licenza MIT.</p>
<!-- support:end -->
""",
}


def restyle(text: str, lang: str) -> str:
    nl = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    # hero: replace marker block, or the first H1 line
    if "<!-- hero:start -->" in text:
        text = re.sub(r"<!-- hero:start -->.*?<!-- hero:end -->\n", HERO[lang], text, count=1, flags=re.S)
    else:
        text = re.sub(r"\A# skill-budget-meter\n", HERO[lang], text, count=1)
    # the language link now sits in the hero
    for link in ("[Leggimi in italiano](README.it.md)\n\n", "[Read me in English](README.md)\n\n"):
        text = text.replace(link, "", 1)
    # support: replace marker block, or from the last H2 that holds the Ko-fi link to the end
    if "<!-- support:start -->" in text:
        text = re.sub(r"<!-- support:start -->.*?<!-- support:end -->\n", SUPPORT[lang], text, count=1, flags=re.S)
    else:
        k = text.rfind("ko-fi.com/gianlucavega")
        h = text.rfind("\n## ", 0, k)
        if k < 0 or h < 0:
            raise SystemExit(f"support section not found ({lang})")
        text = text[: h + 1] + SUPPORT[lang]
    return text.replace("\n", nl)


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    for name, lang in (("README.md", "en"), ("README.it.md", "it")):
        path = ROOT / name
        old = path.read_bytes().decode("utf-8")
        new = restyle(old, lang)
        if new == old:
            print(f"{name}: unchanged")
            continue
        print(f"{name}: {'would change' if dry else 'changed'} ({len(old)} -> {len(new)} chars)")
        if not dry:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
