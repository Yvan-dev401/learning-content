#!/usr/bin/env python3
"""Assemble toute la section « Prompts système » en un seul PDF.

Le document ne refait pas le rendu du site : il reprend les pages déjà publiées dans
`docs/prompts-systeme/`, ce qui garantit qu'il montre exactement ce que montre le site. Trois
obstacles à lever au passage :

* le texte des prompts vit dans des `<details>` repliés et des onglets `hidden` — invisibles à
  l'impression s'ils ne sont pas forcés ouverts ;
* quarante pages concaténées, ce sont des identifiants en double — chaque `id` et chaque ancre
  sont préfixés par l'outil ;
* les liens vers les leçons et les ateliers ne mènent nulle part dans un PDF — ils sont
  réécrits en URL absolues du site publié.

Usage :  python3 tools/build_pdf.py [--out dist/prompts-systeme.pdf] [--keep-html]
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build import CONTENT, DOCS, ROOT, Site, esc, human_size, read_json  # noqa: E402

SITE_URL = "https://yvan-dev401.github.io/Softscar-learning-content/"
OUT_DEFAULT = ROOT / "dist" / "prompts-systeme.pdf"

MAIN_RE = re.compile(r'<main id="contenu" class="main">(.*?)</main>', re.DOTALL)
HIDDEN_RE = re.compile(r'(<div class="tabs__panel"[^>]*?)\s+hidden(\s*>)')
DETAILS_RE = re.compile(r"<details(?![^>]*\bopen\b)")
ID_RE = re.compile(r'\bid="([^"]+)"')
HREF_FRAG_RE = re.compile(r'href="#([^"]+)"')
HREF_REL_RE = re.compile(r'href="((?:\.\./)+)([^"#]*)(#[^"]*)?"')
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre")


def extract_main(page: Path) -> str:
    """Le corps d'une page du site, sans son habillage."""
    mo = MAIN_RE.search(page.read_text(encoding="utf-8"))
    if not mo:
        raise SystemExit(f"corps introuvable dans {page}")
    return mo.group(1)


def printable(html: str, prefix: str) -> str:
    """Rendre un corps de page imprimable et unique dans le document assemblé."""
    # Tout déplier : sans cela, le texte des prompts n'apparaît pas sur le papier.
    html = HIDDEN_RE.sub(r"\1\2", html)
    html = DETAILS_RE.sub("<details open", html)

    # Préfixer les ancres : quarante pages dans un seul document, ce sont autant de
    # collisions d'identifiants, et des liens qui sautent au mauvais endroit.
    html = ID_RE.sub(lambda m: f'id="{prefix}--{m.group(1)}"', html)
    html = HREF_FRAG_RE.sub(lambda m: f'href="#{prefix}--{m.group(1)}"', html)

    # Les liens sortants deviennent des URL du site publié, donc cliquables depuis le PDF.
    def absolute(mo: re.Match) -> str:
        return f'href="{SITE_URL}{mo.group(2)}{mo.group(3) or ""}"'

    html = HREF_REL_RE.sub(absolute, html)

    # Ce qui n'a pas de sens sur papier.
    html = re.sub(r'<nav class="crumbs".*?</nav>', "", html, flags=re.DOTALL)
    html = re.sub(r'<section class="done".*?</section>', "", html, flags=re.DOTALL)
    html = re.sub(r'<nav class="prevnext".*?</nav>', "", html, flags=re.DOTALL)
    html = re.sub(r'<div class="tabs" role="tablist">.*?</div>', "", html, flags=re.DOTALL)
    html = re.sub(r'<button class="codeblock__copy"[^>]*>.*?</button>', "", html, flags=re.DOTALL)
    html = re.sub(r'<a class="anchor"[^>]*>.*?</a>', "", html, flags=re.DOTALL)
    return html


def cover_html(site: Site, n_files: int, chars: int) -> str:
    sec = site.prompts_meta.get("section", {})
    src = site.source("prompts")
    today = date.today()
    return f"""
<section class="cover">
  <p class="cover__eyebrow">Softscar Learning Content</p>
  <h1 class="cover__title">Prompts système — {len(site.prompt_order)} outils décortiqués</h1>
  <p class="cover__tagline">{esc(sec.get("tagline", ""))}</p>
  <ul class="cover__facts">
    <li><strong>{len(site.prompt_order)}</strong> outils commerciaux</li>
    <li><strong>{n_files}</strong> fichiers de prompt</li>
    <li><strong>{chars // 1000} k</strong> caractères reproduits à l'octet près</li>
    <li><strong>{sum(t["tool_defs"] for t in site.prompts["tools"].values())}</strong> définitions d'outils</li>
  </ul>
  <p class="cover__warn"><strong>Avertissement.</strong> {esc(sec.get("disclaimer", ""))}</p>
  <p class="cover__meta">Document assemblé le {today.day} {MOIS[today.month - 1]} {today.year}
     à partir du site publié. Source : <code>{esc(src.get("repo", ""))}</code>,
     licence {esc(src.get("license", ""))}. Version en ligne : {SITE_URL}prompts-systeme/</p>
</section>
"""


def toc_html(site: Site) -> str:
    rows = []
    for tid in site.prompt_order:
        p = site.prompt(tid)
        editor = f' <span class="pdftoc__editor">{esc(p["editor"])}</span>' if p["editor"] else ""
        rows.append(f'<li><a href="#outil--{tid}">{esc(p["title"])}</a>{editor}</li>')
    return ('<section class="pdftoc"><h2>Les outils, dans l\'ordre du document</h2>'
            '<ol>' + "".join(rows) + "</ol></section>")


def build_document(site: Site) -> str:
    n_files = sum(len(t["files"]) for t in site.prompts["tools"].values())
    chars = sum(t["chars"] for t in site.prompts["tools"].values())

    parts = [cover_html(site, n_files, chars), toc_html(site)]

    guide = DOCS / "prompts-systeme" / "guide" / "index.html"
    if guide.is_file():
        parts.append('<section class="pdfpart" id="guide">'
                     + printable(extract_main(guide), "guide") + "</section>")

    for tid in site.prompt_order:
        page = DOCS / "prompts-systeme" / tid / "index.html"
        parts.append(f'<section class="pdfpart" id="outil--{tid}">'
                     + printable(extract_main(page), tid) + "</section>")

    assets = DOCS / "assets"
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Prompts système — {len(site.prompt_order)} outils décortiqués</title>
<link rel="stylesheet" href="{assets / 'style.css'}">
<link rel="stylesheet" href="{assets / 'highlight.css'}">
<link rel="stylesheet" href="{ROOT / 'tools' / 'assets' / 'print.css'}">
</head>
<body class="pdf">
<div class="pdf__main">
{"".join(parts)}
</div>
</body>
</html>
"""


def launch_chromium(pw):
    """Chromium change de version et d'arborescence d'une image à l'autre.

    Playwright cherche le binaire de la version qu'il attend ; quand l'image embarque une
    autre version, on balaie le dossier des navigateurs plutôt que de figer un chemin.
    """
    try:
        return pw.chromium.launch()
    except Exception as first:
        root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
        found: list[str] = []
        for pattern in ("chromium-*/chrome-linux*/chrome",
                        "chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"):
            found += sorted(glob.glob(str(Path(root) / pattern)), reverse=True)
        for path in found:
            p = Path(path)
            if p.is_file() and os.access(p, os.X_OK):
                print(f"  (Chromium trouvé : {p})", flush=True)
                return pw.chromium.launch(executable_path=str(p))
        raise first


def render(html_path: Path, out: Path, title: str) -> None:
    from playwright.sync_api import sync_playwright

    foot = ('<div style="width:100%;font-size:7pt;color:#8a8a99;padding:0 14mm;'
            'font-family:system-ui,sans-serif;display:flex;justify-content:space-between">'
            f'<span>{esc(title)}</span>'
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
            "</div>")
    head = ('<div style="width:100%;font-size:7pt;color:#b5b5c2;padding:0 14mm;'
            'font-family:system-ui,sans-serif;text-align:right">'
            "Softscar Learning Content</div>")

    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        page = browser.new_page()
        # Un document d'un millier de pages dépasse largement les délais par défaut.
        page.set_default_timeout(900_000)
        page.set_default_navigation_timeout(900_000)
        page.goto(html_path.as_uri(), wait_until="load", timeout=600_000)
        page.emulate_media(media="print")
        page.pdf(path=str(out), format="A4", print_background=True,
                 display_header_footer=True, header_template=head, footer_template=foot,
                 margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
                 outline=True, tagged=True)
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="chemin du PDF à produire")
    ap.add_argument("--keep-html", action="store_true",
                    help="conserver le HTML intermédiaire à côté du PDF")
    args = ap.parse_args()

    if not (DOCS / "prompts-systeme").is_dir():
        print("docs/prompts-systeme absent — lancez `python3 tools/build.py`.", file=sys.stderr)
        return 1

    site = Site()
    print(f"→ assemblage de {len(site.prompt_order)} fiches…", flush=True)
    doc = build_document(site)

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    html_path = out.with_suffix(".html")
    html_path.write_text(doc, encoding="utf-8")
    print(f"  HTML intermédiaire : {human_size(len(doc.encode()))}", flush=True)

    print("→ rendu par Chromium (quelques minutes pour un millier de pages)…", flush=True)
    render(html_path, out, "Prompts système — 40 outils décortiqués")
    if not args.keep_html:
        html_path.unlink(missing_ok=True)

    print(f"✓ {out} — {human_size(out.stat().st_size)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
