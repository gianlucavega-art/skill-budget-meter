#!/usr/bin/env python3
"""Generate the animated SVG artwork of the README (English and Italian).

Standard library only. Idempotent: rewrites assets/*.svg from the texts below.
Usage:  python assets/make_assets.py [--dry-run]

The SVGs use CSS animations (rendered by GitHub inside <img>) and honour
prefers-reduced-motion. No external fonts, images or scripts.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent
FONT = "font-family:'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"

TEXT = {
    "en": {
        "tagline": "Which of your Claude Code skills lost their description?",
        "pills": ["1 Python file", "standard library", "read-only", "no network"],
        "before": "37 skills without description",
        "after": "0 skills without description",
        "budget": "skill listing budget",
        "s_kicker": "THE METHOD BEHIND THE RESULT",
        "s_title": "37 → 0 in one day",
        "s_sub": "Every skill back in the listing, every description visible again.",
        "s_items": ["Step-by-step method", "Copy-ready description templates", "Checklists, English + Italian"],
        "s_price": "12 €",
        "s_price_note": "PDF guide",
        "b_guide": "Get the guide · 12 €",
        "b_kofi": "Buy me a coffee",
        "b_consult": "Book a setup audit",
        "b_star": "Star the repo",
    },
    "it": {
        "tagline": "Quali skill di Claude Code hanno perso la descrizione?",
        "pills": ["1 file Python", "libreria standard", "sola lettura", "nessuna rete"],
        "before": "37 skill senza descrizione",
        "after": "0 skill senza descrizione",
        "budget": "budget dell'elenco skill",
        "s_kicker": "IL METODO DIETRO IL RISULTATO",
        "s_title": "Da 37 a 0 in un giorno",
        "s_sub": "Ogni skill di nuovo nell'elenco, ogni descrizione di nuovo visibile.",
        "s_items": ["Metodo passo passo", "Modelli di descrizioni pronti da copiare", "Liste di controllo, italiano + inglese"],
        "s_price": "12 €",
        "s_price_note": "guida PDF",
        "b_guide": "Acquista la guida · 12 €",
        "b_kofi": "Offrimi un caffè",
        "b_consult": "Prenota un audit",
        "b_star": "Metti una stella",
    },
}

REDUCED = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


def hero(t: dict) -> str:
    pills, x = [], 0
    widths = [len(p) * 9 + 36 for p in t["pills"]]
    total = sum(widths) + 12 * (len(widths) - 1)
    x = (1200 - total) / 2
    for p, w in zip(t["pills"], widths):
        pills.append(
            f'<rect x="{x:.0f}" y="168" width="{w}" height="34" rx="17" fill="#ffffff" fill-opacity=".10" stroke="#a5b4fc" stroke-opacity=".5"/>'
            f'<text x="{x + w / 2:.0f}" y="190" text-anchor="middle" class="pill">{escape(p)}</text>'
        )
        x += w + 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="380" viewBox="0 0 1200 380" role="img" aria-label="skill-budget-meter: {escape(t['tagline'])}">
<title>skill-budget-meter</title>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0f172a"/><stop offset=".55" stop-color="#1e1b4b"/><stop offset="1" stop-color="#4c1d95"/></linearGradient>
<linearGradient id="title" x1="0" x2="1"><stop offset="0" stop-color="#67e8f9"/><stop offset=".5" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
<radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#8b5cf6" stop-opacity=".55"/><stop offset="1" stop-color="#8b5cf6" stop-opacity="0"/></radialGradient>
<clipPath id="bar"><rect x="250" y="262" width="700" height="30" rx="15"/></clipPath>
</defs>
<style>
text{{{FONT}}}
.h1{{font-size:64px;font-weight:800;fill:url(#title);letter-spacing:-1px}}
.tag{{font-size:24px;fill:#e0e7ff}}
.pill{{font-size:15px;fill:#e0e7ff;font-weight:600}}
.lbl{{font-size:15px;fill:#c7d2fe}}
.st{{font-size:19px;font-weight:700}}
.orb{{animation:float 9s ease-in-out infinite}}
.orb2{{animation:float 11s ease-in-out infinite reverse}}
@keyframes float{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(30px,-18px)}}}}
.fill{{animation:fill 8s cubic-bezier(.65,0,.35,1) infinite}}
@keyframes fill{{0%{{width:0;fill:#f43f5e}}35%{{width:700px;fill:#f43f5e}}55%{{width:700px;fill:#f43f5e}}70%{{width:610px;fill:#22c55e}}100%{{width:610px;fill:#22c55e}}}}
.over{{animation:over 8s linear infinite}}
@keyframes over{{0%,30%{{opacity:0}}36%,55%{{opacity:1}}62%,100%{{opacity:0}}}}
.ok{{animation:ok 8s linear infinite}}
@keyframes ok{{0%,62%{{opacity:0}}70%,96%{{opacity:1}}100%{{opacity:0}}}}
{REDUCED}
@media (prefers-reduced-motion: reduce){{.fill{{width:610px;fill:#22c55e}}.over{{opacity:0}}.ok{{opacity:1}}}}
</style>
<rect width="1200" height="380" rx="24" fill="url(#bg)"/>
<circle class="orb" cx="160" cy="90" r="160" fill="url(#glow)"/>
<circle class="orb2" cx="1060" cy="300" r="190" fill="url(#glow)"/>
<text x="600" y="100" text-anchor="middle" class="h1">skill-budget-meter</text>
<text x="600" y="145" text-anchor="middle" class="tag">{escape(t['tagline'])}</text>
{''.join(pills)}
<text x="250" y="252" class="lbl">{escape(t['budget'])}</text>
<rect x="250" y="262" width="700" height="30" rx="15" fill="#ffffff" fill-opacity=".12"/>
<g clip-path="url(#bar)"><rect class="fill" x="250" y="262" width="610" height="30" fill="#22c55e"/></g>
<line x1="860" y1="254" x2="860" y2="300" stroke="#fde68a" stroke-width="2" stroke-dasharray="4 4"/>
<text x="600" y="335" text-anchor="middle" class="st over" fill="#fda4af">⚠ {escape(t['before'])}</text>
<text x="600" y="335" text-anchor="middle" class="st ok" fill="#86efac">✔ {escape(t['after'])}</text>
</svg>
'''


def support(t: dict) -> str:
    items = "".join(
        f'<g class="it" style="animation-delay:{0.4 + i * 0.35:.2f}s">'
        f'<circle cx="92" cy="{232 + i * 46}" r="14" fill="#ffffff"/>'
        f'<path d="M85 {232 + i * 46} l5 5 l9 -10" stroke="#db2777" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<text x="118" y="{239 + i * 46}" class="item">{escape(s)}</text></g>'
        for i, s in enumerate(t["s_items"])
    )
    sparkles = "".join(
        f'<path class="sp" style="animation-delay:{d}s" transform="translate({x} {y}) scale({s})" d="M0 -12 L3 -3 L12 0 L3 3 L0 12 L-3 3 L-12 0 L-3 -3Z" fill="#fff"/>'
        for x, y, s, d in [(640, 60, 1.2, 0), (1140, 70, .9, .8), (700, 380, .8, 1.6), (1150, 360, 1.1, 2.4), (560, 300, .7, 1.2)]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-label="{escape(t['s_title'])}: {escape(', '.join(t['s_items']))}, {escape(t['s_price'])}">
<title>{escape(t['s_title'])}</title>
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c3aed"/><stop offset=".5" stop-color="#db2777"/><stop offset="1" stop-color="#f59e0b"/></linearGradient>
<linearGradient id="book" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset="1" stop-color="#312e81"/></linearGradient>
</defs>
<style>
text{{{FONT}}}
.k{{font-size:16px;font-weight:700;fill:#fde68a;letter-spacing:3px}}
.t{{font-size:58px;font-weight:800;fill:#fff;letter-spacing:-1px}}
.s{{font-size:21px;fill:#fdf2f8}}
.item{{font-size:22px;font-weight:600;fill:#fff}}
.it{{opacity:0;animation:in .6s ease-out forwards}}
@keyframes in{{from{{opacity:0;transform:translateX(-16px)}}to{{opacity:1;transform:none}}}}
.sp{{animation:tw 3.2s ease-in-out infinite;opacity:.2}}
@keyframes tw{{0%,100%{{opacity:.15}}50%{{opacity:.95}}}}
.bk{{animation:bob 4s ease-in-out infinite;transform-origin:930px 210px}}
@keyframes bob{{0%,100%{{transform:translateY(0) rotate(-4deg)}}50%{{transform:translateY(-10px) rotate(-2deg)}}}}
.tagp{{animation:pulse 2.4s ease-in-out infinite;transform-origin:1112px 84px}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.08)}}}}
{REDUCED}
@media (prefers-reduced-motion: reduce){{.it{{opacity:1}}}}
</style>
<rect width="1200" height="420" rx="24" fill="url(#g)"/>
{sparkles}
<text x="64" y="78" class="k">{escape(t['s_kicker'])}</text>
<text x="64" y="146" class="t">{escape(t['s_title'])}</text>
<text x="64" y="186" class="s">{escape(t['s_sub'])}</text>
{items}
<g class="bk">
<rect x="830" y="90" width="210" height="270" rx="12" fill="url(#book)" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
<rect x="830" y="90" width="22" height="270" rx="6" fill="#000" fill-opacity=".25"/>
<text x="946" y="160" text-anchor="middle" style="font-size:42px;font-weight:800;fill:#f9a8d4">37→0</text>
<rect x="878" y="190" width="136" height="10" rx="5" fill="#fff" fill-opacity=".5"/>
<rect x="878" y="212" width="110" height="10" rx="5" fill="#fff" fill-opacity=".35"/>
<rect x="878" y="234" width="124" height="10" rx="5" fill="#fff" fill-opacity=".35"/>
<rect x="878" y="290" width="136" height="26" rx="13" fill="#22c55e"/>
<text x="946" y="309" text-anchor="middle" style="font-size:15px;font-weight:700;fill:#fff">EN + IT · PDF</text>
</g>
<g class="tagp">
<circle cx="1112" cy="84" r="56" fill="#fde047" stroke="#fff" stroke-width="4"/>
<text x="1112" y="92" text-anchor="middle" style="font-size:34px;font-weight:800;fill:#7c2d12">{escape(t['s_price'])}</text>
<text x="1112" y="114" text-anchor="middle" style="font-size:13px;font-weight:700;fill:#7c2d12">{escape(t['s_price_note'])}</text>
</g>
</svg>
'''


def button(label: str, c1: str, c2: str, icon: str, pulse: bool) -> str:
    w = max(300, int(len(label) * 12) + 100)
    anim = (".glow{animation:gl 2.2s ease-in-out infinite}@keyframes gl{0%,100%{opacity:.25}50%{opacity:.75}}"
            if pulse else ".glow{opacity:.3}")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="72" viewBox="0 0 {w} 72" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<defs><linearGradient id="b" x1="0" x2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<style>text{{{FONT}}}{anim}{REDUCED}</style>
<rect class="glow" x="2" y="2" width="{w - 4}" height="68" rx="34" fill="none" stroke="{c2}" stroke-width="4"/>
<rect x="8" y="8" width="{w - 16}" height="56" rx="28" fill="url(#b)"/>
<g transform="translate(46 36)">{icon}</g>
<text x="{(w + 40) / 2:.0f}" y="44" text-anchor="middle" style="font-size:22px;font-weight:700;fill:#fff">{escape(label)}</text>
</svg>
'''


ICON_BOOK = '<path d="M-12 -10h9a5 5 0 0 1 3 2a5 5 0 0 1 3 -2h9v20h-9a4 4 0 0 0 -3 2a4 4 0 0 0 -3 -2h-9z" fill="none" stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/>'
ICON_CUP = '<path d="M-12 -6h18v8a8 8 0 0 1 -8 8h-2a8 8 0 0 1 -8 -8z M6 -3h3a4 4 0 0 1 0 8h-3" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M-6 -14q2 3 0 5M0 -14q2 3 0 5" stroke="#fff" stroke-width="2" fill="none"/>'
ICON_TOOL = '<circle r="11" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M-5 0l4 4l7 -8" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
ICON_STAR = '<path d="M0 -13l3.8 7.7 8.5 1.2-6.1 6 1.4 8.4L0 6.3l-7.6 4 1.4-8.4-6.1-6 8.5-1.2z" fill="#fff"/>'


def build() -> dict[str, str]:
    files = {}
    for lang, t in TEXT.items():
        files[f"hero-{lang}.svg"] = hero(t)
        files[f"support-{lang}.svg"] = support(t)
        files[f"btn-guide-{lang}.svg"] = button(t["b_guide"], "#db2777", "#f59e0b", ICON_BOOK, True)
        files[f"btn-kofi-{lang}.svg"] = button(t["b_kofi"], "#0ea5e9", "#6366f1", ICON_CUP, False)
        files[f"btn-consult-{lang}.svg"] = button(t["b_consult"], "#7c3aed", "#4f46e5", ICON_TOOL, False)
        files[f"btn-star-{lang}.svg"] = button(t["b_star"], "#ca8a04", "#ea580c", ICON_STAR, False)
    return files


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    changed = 0
    for name, body in build().items():
        path = OUT / name
        if path.exists() and path.read_text(encoding="utf-8") == body:
            continue
        changed += 1
        print(("would write " if dry else "write ") + name)
        if not dry:
            path.write_text(body, encoding="utf-8", newline="\n")
    print(f"done: {changed} file(s) {'to change' if dry else 'changed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
