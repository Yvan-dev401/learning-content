#!/usr/bin/env python3
"""Vérifie l'intégrité du site généré : liens internes, images, ancres, complétude.

Ne fait aucune requête réseau : seuls les liens internes sont contrôlés.

Usage :  python3 tools/check_links.py
Sort en code 1 si un problème est détecté.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CONTENT = ROOT / "content"

ATTR_RE = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""", re.IGNORECASE)
ID_RE = re.compile(r"""\bid=["']([^"']+)["']""")
MIN_LESSON_BYTES = 3000


def anchors(html: str) -> set[str]:
    return set(ID_RE.findall(html))


def main() -> int:
    if not DOCS.exists():
        print("docs/ absent — lancez `python3 tools/build.py`.", file=sys.stderr)
        return 1

    # `docs/assets/` contient le code source copié des projets : des .html qui appartiennent
    # à ces projets, pas au site. Les vérifier n'aurait aucun sens.
    pages = sorted(p for p in DOCS.rglob("*.html")
                   if "assets" not in p.relative_to(DOCS).parts)
    cache: dict[Path, str] = {p: p.read_text(encoding="utf-8") for p in pages}
    ids: dict[Path, set[str]] = {p: anchors(h) for p, h in cache.items()}

    problems: list[str] = []
    checked = 0

    for page in pages:
        html = cache[page]
        rel_page = page.relative_to(DOCS)
        for raw in ATTR_RE.findall(html):
            target = raw.strip()
            if (not target or target.startswith(("http://", "https://", "mailto:", "data:", "//"))):
                continue
            checked += 1
            path_part, _, frag = target.partition("#")
            frag = unquote(frag)

            if not path_part:                      # ancre dans la page courante
                if frag and frag not in ids[page]:
                    problems.append(f"{rel_page}: ancre inconnue #{frag}")
                continue

            dest = (page.parent / unquote(path_part)).resolve()
            try:
                dest.relative_to(DOCS.resolve())
            except ValueError:
                problems.append(f"{rel_page}: lien hors de docs/ → {target}")
                continue
            if not dest.exists():
                problems.append(f"{rel_page}: cible absente → {target}")
                continue
            if frag and dest.suffix == ".html":
                if frag not in ids.get(dest, anchors(dest.read_text(encoding="utf-8"))):
                    problems.append(f"{rel_page}: ancre inconnue → {target}")

    # Complétude : une page par leçon, chacune substantielle.
    meta = json.loads((CONTENT / "_meta.json").read_text(encoding="utf-8"))
    ingest = json.loads((CONTENT / "_ingest.json").read_text(encoding="utf-8"))
    lessons = [s for t in meta["tracks"] for s in t["lessons"]]
    for slug in lessons:
        page = DOCS / "lecons" / slug / "index.html"
        if not page.exists():
            problems.append(f"leçon absente du site : {slug}")
        elif page.stat().st_size < MIN_LESSON_BYTES:
            problems.append(f"leçon anormalement courte : {slug} ({page.stat().st_size} o)")
        for rel in ingest["lessons"].get(slug, {}).get("code", []):
            if not (DOCS / "assets" / "code" / slug / rel).exists():
                problems.append(f"fichier de code non publié : {slug}/{rel}")

    for track in meta["tracks"]:
        if not (DOCS / "parcours" / track["id"] / "index.html").exists():
            problems.append(f"parcours absent du site : {track['id']}")

    # Ateliers : chaque projet et chaque catégorie doit avoir sa page, et son code publié.
    apps = json.loads((CONTENT / "_apps.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_apps.json").is_file() else {"categories": {}, "projects": {}}
    apps_meta = json.loads((CONTENT / "_apps_meta.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_apps_meta.json").is_file() else {"categories": {}, "projects": {}}
    for cat in apps["categories"]:
        if not (DOCS / "ateliers" / cat / "index.html").exists():
            problems.append(f"catégorie d'ateliers absente du site : {cat}")
        if cat not in apps_meta["categories"]:
            problems.append(f"catégorie sans habillage français : {cat}")
    for pid, proj in apps["projects"].items():
        if not (DOCS / "ateliers" / pid / "index.html").exists():
            problems.append(f"atelier absent du site : {pid}")
        for rel in proj["code"]:
            if not (DOCS / "assets" / "code" / "ateliers" / pid / rel).exists():
                problems.append(f"code d'atelier non publié : {pid}/{rel}")

    # Cohérence des tags : tout tag posé à la main doit exister au vocabulaire.
    vocab = set(meta.get("tags", {}).get("values", {}))
    groups = set(meta.get("tags", {}).get("groups", {}))
    for t, v in meta.get("tags", {}).get("values", {}).items():
        if v["group"] not in groups:
            problems.append(f"tag « {t} » rattaché à un groupe inconnu : {v['group']}")
    declared = [(f"leçon {k}", t) for k, v in meta["lessons"].items() for t in v.get("tags", [])]
    declared += [(f"catégorie {k}", t) for k, v in apps_meta["categories"].items()
                 for t in v.get("defaults", {}).values()]
    declared += [(f"atelier {k}", t) for k, v in apps_meta["projects"].items()
                 for t in v.get("tags", [])]
    for where, t in declared:
        if t not in vocab:
            problems.append(f"tag inconnu dans {where} : {t}")

    # Services : chaque motif doit compiler, et chaque alternative avoir un lien.
    services = json.loads((CONTENT / "_services.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_services.json").is_file() else {"categories": {}, "services": {}}
    for sid, sv in services["services"].items():
        if sv["category"] not in services["categories"]:
            problems.append(f"service « {sid} » dans une catégorie inconnue : {sv['category']}")
        if sv["cost"] not in services.get("cost_labels", {}):
            problems.append(f"service « {sid} » avec un coût inconnu : {sv['cost']}")
        for pat in sv["detect"]:
            try:
                re.compile(pat)
            except re.error as exc:
                problems.append(f"motif invalide pour « {sid} » : {pat} ({exc})")
        if sv["cost"] != "gratuit" and not sv["free"]:
            problems.append(f"service payant sans alternative : {sid}")
        for f in sv["free"]:
            if not f.get("url", "").startswith("http"):
                problems.append(f"alternative sans lien valide dans « {sid} » : {f.get('name')}")

    # Images orphelines : présentes dans assets/images mais jamais référencées.
    referenced = set()
    for html in cache.values():
        for raw in ATTR_RE.findall(html):
            if "assets/images/" in raw:
                referenced.add(unquote(raw.rsplit("/", 1)[-1]))
    orphans = sorted(
        p.name for p in (DOCS / "assets" / "images").glob("*") if p.name not in referenced
    )

    print(f"Pages HTML analysées : {len(pages)}")
    print(f"Liens internes vérifiés : {checked}")
    print(f"Leçons publiées : {len(lessons)} · parcours : {len(meta['tracks'])}")
    print(f"Ateliers publiés : {len(apps['projects'])} · catégories : {len(apps['categories'])}")
    print(f"Services décrits : {len(services['services'])} · tags au vocabulaire : {len(vocab)}")
    if orphans:
        print(f"Images non référencées ({len(orphans)}) : {', '.join(orphans[:8])}"
              + (" …" if len(orphans) > 8 else ""))
    if problems:
        print(f"\n✗ {len(problems)} problème(s) :")
        for p in problems:
            print(f"   - {p}")
        return 1
    print("\n✓ Aucun lien interne cassé, aucune leçon manquante.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
