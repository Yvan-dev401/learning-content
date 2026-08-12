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

    # Prompts système : une page par outil, et chaque fichier réellement publié.
    prompts = json.loads((CONTENT / "_prompts.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_prompts.json").is_file() else {"tools": {}}
    prompts_meta = json.loads((CONTENT / "_prompts_meta.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_prompts_meta.json").is_file() else {"tools": {}}
    for tid, tool in prompts["tools"].items():
        if not (DOCS / "prompts-systeme" / tid / "index.html").exists():
            problems.append(f"prompt système absent du site : {tid}")
        if tid not in prompts_meta["tools"]:
            problems.append(f"outil sans habillage français : {tid}")
        for f in tool["files"]:
            if not (DOCS / "assets" / "prompts-systeme" / tid / f["name"]).exists():
                problems.append(f"fichier de prompt non publié : {tid}/{f['name']}")
    for tid in prompts_meta["tools"]:
        if tid not in prompts["tools"]:
            problems.append(f"outil décrit mais absent du manifeste : {tid}")

    # Mise en situation : sans ces champs, la fiche redevient un mur de texte.
    for tid, fr in prompts_meta["tools"].items():
        for champ in ("role", "when", "output", "reuse"):
            if not fr.get(champ):
                problems.append(f"outil sans « {champ} » : {tid}")

    # Chaque fichier publié doit être situé, et aucune fiche ne doit décrire un fichier
    # absent : c'est la seule garantie que le tableau « Quel fichier, et où ? » est complet.
    filedef_all = json.loads((CONTENT / "_prompt_files.json").read_text(encoding="utf-8")) \
        if (CONTENT / "_prompt_files.json").is_file() else {"files": {}, "status_labels": {}}
    filedef, statuses = filedef_all["files"], filedef_all.get("status_labels", {})
    published = {f"{tid}/{f['name']}" for tid, tool in prompts["tools"].items()
                 for f in tool["files"]}
    for key in sorted(published - set(filedef)):
        problems.append(f"fichier de prompt non situé : {key}")
    for key in sorted(set(filedef) - published):
        problems.append(f"fiche de fichier orpheline : {key}")
    firsts: dict[str, int] = {}
    for key, fr in filedef.items():
        tid = key.split("/")[0]
        for champ in ("title", "surface", "when", "read", "status"):
            if not fr.get(champ):
                problems.append(f"fichier sans « {champ} » : {key}")
        if fr.get("status") and fr["status"] not in statuses:
            problems.append(f"statut de fichier hors vocabulaire : {key} → {fr['status']}")
        if fr.get("first"):
            firsts[tid] = firsts.get(tid, 0) + 1
    for tid, tool in prompts["tools"].items():
        if firsts.get(tid, 0) != 1:
            problems.append(f"outil sans « à lire en premier » unique : {tid} "
                            f"({firsts.get(tid, 0)})")
        if len(tool["files"]) > 1 and not prompts_meta["tools"].get(tid, {}).get("files_note"):
            problems.append(f"outil à plusieurs fichiers sans cadrage « files_note » : {tid}")
    if not (DOCS / "prompts-systeme" / "guide" / "index.html").exists():
        problems.append("guide de lecture des prompts absent du site")

    # Glossaire des sections : alias résolus, leçons existantes, couverture mesurée.
    gloss = json.loads((CONTENT / "_prompt_sections.json").read_text(encoding="utf-8"))["sections"] \
        if (CONTENT / "_prompt_sections.json").is_file() else {}
    MOMENTS = {"cadre", "machine", "vos-regles", "joint", "message", "outils",
               "comprendre", "appeler", "agir", "repondre", "hors"}
    for k, v in gloss.items():
        if "alias" in v and v["alias"] not in gloss:
            problems.append(f"alias de section cassé : {k} → {v['alias']}")
        if v.get("lesson") and v["lesson"] not in meta["lessons"]:
            problems.append(f"section « {k} » liée à une leçon inconnue : {v['lesson']}")
        if "title" in v and v.get("moment") not in MOMENTS:
            problems.append(f"section sans moment valide : {k} → {v.get('moment')}")

    glossed = flat = numbered = 0
    for page in sorted((DOCS / "prompts-systeme").glob("*/index.html")):
        html_txt = page.read_text(encoding="utf-8")
        glossed += html_txt.count("promptsec__role")
        flat += len(re.findall(r'<details class="promptsec"', html_txt))
        numbered += len(re.findall(r'<span class="step step--(?!compte|hors)', html_txt))
    gloss_rate = f"{100 * glossed // flat} %" if flat else "n/a"
    # Une pastille apparaît deux fois par section (plan + texte) : on ramène au nombre réel.
    step_rate = f"{100 * (numbered // 2) // flat} %" if flat else "n/a"

    # Sujets : vocabulaire connu, page produite, et aucun sujet vide (page inutile).
    topics = json.loads((CONTENT / "_topics.json").read_text(encoding="utf-8"))["topics"] \
        if (CONTENT / "_topics.json").is_file() else {}
    declared = [(f"leçon {k}", t) for k, v in meta["lessons"].items() for t in v.get("topics", [])]
    declared += [(f"catégorie {k}", t) for k, v in apps_meta["categories"].items()
                 for t in v.get("topics", [])]
    declared += [(f"outil {k}", t) for k, v in prompts_meta["tools"].items()
                 for t in v.get("topics", [])]
    for where, t in declared:
        if t not in topics:
            problems.append(f"sujet inconnu dans {where} : {t}")
    for tid in topics:
        if not (DOCS / "sujets" / tid / "index.html").exists():
            problems.append(f"sujet absent du site : {tid}")

    # Couverture : un sujet vide n'a pas de raison d'exister ; un sujet porté par une
    # seule famille est signalé sans être bloquant — c'est un signal éditorial.
    coverage: dict[str, dict[str, int]] = {}
    for page in DOCS.rglob("catalogue/index.html"):
        html_txt = page.read_text(encoding="utf-8")
        for m in re.finditer(r'data-type="([^"]*)"[^>]*data-topics="([^"]*)"', html_txt):
            ctype, tlist = m.group(1), m.group(2).split()
            for t in tlist:
                coverage.setdefault(t, {}).setdefault(ctype, 0)
                coverage[t][ctype] += 1
    thin = []
    for tid in topics:
        fams = coverage.get(tid, {})
        if not fams:
            problems.append(f"sujet sans aucun contenu : {tid}")
        elif len(fams) < 2:
            thin.append(f"{tid} ({', '.join(f'{k}×{v}' for k, v in fams.items())})")

    # Cohérence des tags : tout tag posé à la main doit exister au vocabulaire.
    vocab = set(meta.get("tags", {}).get("values", {}))
    groups = set(meta.get("tags", {}).get("groups", {}))
    for t, v in meta.get("tags", {}).get("values", {}).items():
        if v["group"] not in groups:
            problems.append(f"tag « {t} » rattaché à un groupe inconnu : {v['group']}")
    declared_tags = [(f"leçon {k}", t) for k, v in meta["lessons"].items() for t in v.get("tags", [])]
    declared_tags += [(f"catégorie {k}", t) for k, v in apps_meta["categories"].items()
                      for t in v.get("defaults", {}).values()]
    declared_tags += [(f"atelier {k}", t) for k, v in apps_meta["projects"].items()
                      for t in v.get("tags", [])]
    declared_tags += [(f"outil {k}", t) for k, v in prompts_meta["tools"].items()
                      for t in v.get("tags", [])]
    for where, t in declared_tags:
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
    print(f"Prompts système publiés : {len(prompts['tools'])} · sujets : {len(topics)}")
    print(f"Sections de prompt : {flat} découpées, {glossed} expliquées par le glossaire "
          f"({gloss_rate}) · {sum(1 for v in gloss.values() if 'title' in v)} types décrits")
    print(f"Fichiers de prompt situés : {len(filedef)} · sections placées dans le "
          f"déroulé : {step_rate}")
    print(f"Services décrits : {len(services['services'])} · tags au vocabulaire : {len(vocab)}")
    if thin:
        print(f"Sujets portés par une seule famille ({len(thin)}) : {', '.join(thin)}")
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
