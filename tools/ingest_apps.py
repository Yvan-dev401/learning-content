#!/usr/bin/env python3
"""Importe les ateliers pratiques du dépôt awesome-llm-apps (Apache-2.0).

Le dépôt source n'a pas de structure régulière : les projets vivent à des profondeurs
variables (`rag_tutorials/corrective_rag`, mais aussi
`advanced_ai_agents/multi_agent_apps/agent_teams/ai_finance_agent_team`), et certains
dossiers ne servent qu'à regrouper. On identifie donc un projet par une règle plutôt que
par une liste : le dossier le moins profond (à partir du niveau 2) qui contient un
`README.md` et du code. Ses sous-dossiers sont absorbés dans ce projet.

Les liens sont réécrits en jetons résolus ensuite par `build.py` :
    @apps                          catalogue des ateliers
    @app/<cat>/<projet>            page d'un atelier
    @apppage/<cat>/<projet>/<page> page annexe d'un atelier
    @appcode/<cat>/<projet>/<rel>  fichier de code d'un atelier
    @img/<nom>                     image

Usage :  python3 tools/ingest_apps.py [--upstream <chemin-du-clone>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from common import (CODE, CONTENT, HTML_SRC_RE, IMAGE_EXT, IMAGES, MD_LINK_RE,
                    ROOT, ImagePool, copy_code_tree, log, shallow_clone)

UPSTREAM_URL = "https://github.com/Shubhamsaboo/awesome-llm-apps.git"
UPSTREAM_WEB = "https://github.com/Shubhamsaboo/awesome-llm-apps"
DEFAULT_UPSTREAM = (
    Path(os.environ["APPS_UPSTREAM"]) if os.environ.get("APPS_UPSTREAM")
    else ROOT.parent / "awesome-llm-apps-upstream"
)

CONTENT_APPS = CONTENT / "ateliers"
CODE_APPS = CODE / "ateliers"

CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".ipynb", ".sh", ".ps1"}
# Dossiers qui ne décrivent pas un projet à publier.
SKIP_PARTS = {".git", "node_modules", ".venv", "venv", "__pycache__", "docs",
              ".next", "dist", "build", ".agent", "evals", ".github", "assets"}
# Projets écartés : outillage interne du dépôt source, sans valeur pédagogique ici.
SKIP_PROJECTS = {"agent_skills/evals"}
MAX_FEATURES = 6


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s.-]", "", text.lower())
    text = re.sub(r"[\s_.]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text) or "projet"


def is_clean(path: Path, root: Path) -> bool:
    return not (set(path.relative_to(root).parts) & SKIP_PARTS)


def find_projects(root: Path) -> list[Path]:
    """Racines de projet : le dossier le moins profond, au niveau 2 minimum, qui a un
    README et du code sous lui. Les descendants sont absorbés."""
    candidates = sorted(
        {p.parent for p in root.rglob("README.md") if is_clean(p.parent, root)} - {root}
    )
    qualified = [
        d for d in candidates
        if len(d.relative_to(root).parts) >= 2
        and any(f.is_file() and f.suffix.lower() in CODE_EXT
                for f in d.rglob("*") if is_clean(f, root))
    ]
    roots: list[Path] = []
    for d in sorted(qualified, key=lambda x: (len(x.parts), str(x))):
        rel = d.relative_to(root).as_posix()
        if rel in SKIP_PROJECTS:
            continue
        if any(rel.startswith(r.relative_to(root).as_posix() + "/") for r in roots):
            continue
        roots.append(d)
    return sorted(roots, key=lambda x: str(x))


def first_heading(md: str) -> str | None:
    m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else None


def extract_features(md: str) -> list[str]:
    """Puces de la section « Features » du README, pour un résumé de repli."""
    m = re.search(r"^#{2,3}\s*(?:[^\w\s]*\s*)?(?:Features?|Key Features?|What it does)\b.*?$",
                  md, re.MULTILINE | re.IGNORECASE)
    if not m:
        return []
    tail = md[m.end():]
    stop = re.search(r"^#{1,3}\s", tail, re.MULTILINE)
    block = tail[: stop.start()] if stop else tail
    items = re.findall(r"^\s*[-*]\s+(.+)$", block, re.MULTILINE)
    out = []
    for it in items:
        it = re.sub(r"\*\*(.+?)\*\*", r"\1", it)
        it = re.sub(r"`([^`]+)`", r"\1", it)
        it = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", it).strip()
        if it:
            out.append(it[:200])
    return out[:MAX_FEATURES]


class AppIngest:
    def __init__(self, upstream: Path):
        self.up = upstream
        self.images = ImagePool()
        self.projects: dict[str, dict] = {}   # id "<cat>/<proj>" -> infos
        self.by_path: dict[str, str] = {}     # chemin amont -> id
        self.manifest: dict = {"categories": {}, "projects": {}, "images": 0, "skipped": []}
        self.warnings: list[str] = []

    # ------------------------------------------------------------ découverte

    def discover(self) -> None:
        for d in find_projects(self.up):
            rel = d.relative_to(self.up)
            cat_path = rel.parent.as_posix()
            cat_slug = slugify(cat_path.replace("/", "-"))
            proj_slug = slugify(rel.name)
            pid = f"{cat_slug}/{proj_slug}"
            if pid in self.projects:                       # collision improbable, tranchée
                pid = f"{cat_slug}/{slugify(rel.parent.name)}-{proj_slug}"
            self.projects[pid] = {"dir": d, "path": rel.as_posix(),
                                  "cat_path": cat_path, "cat_slug": cat_slug,
                                  "slug": proj_slug, "name": rel.name}
            self.by_path[rel.as_posix()] = pid

    def project_of(self, rel_path: str) -> str | None:
        """Projet auquel appartient un chemin du dépôt source, s'il y en a un."""
        best = None
        for path, pid in self.by_path.items():
            if rel_path == path or rel_path.startswith(path + "/"):
                if best is None or len(path) > len(self.projects[best]["path"]):
                    best = pid
        return best

    # ------------------------------------------------------- liens et images

    def resolve(self, target: str, md_file: Path, pid: str) -> str | None:
        raw, _, frag = target.partition("#")
        frag = ("#" + frag) if frag else ""
        if not raw:
            return (frag or None)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("//"):
            return None
        if re.fullmatch(r"[^@\s/]+@[^@\s/]+\.[A-Za-z]{2,}", raw):
            return "mailto:" + raw

        try:
            dest = (md_file.parent / raw).resolve()
            rel = dest.relative_to(self.up.resolve()).as_posix()
        except ValueError:
            return None

        if dest.suffix.lower() in IMAGE_EXT:
            if not dest.is_file():
                self.warnings.append(f"image absente : {target} (dans {pid})")
                return "@missing"
            name = self.images.target(dest, "atelier-" + self.projects[pid]["slug"])
            if name is None:   # image trop lourde : on pointe vers le dépôt d'origine
                return f"https://raw.githubusercontent.com/Shubhamsaboo/awesome-llm-apps/main/{rel}"
            return "@img/" + name

        owner = self.project_of(rel)
        if owner is None:
            return f"{UPSTREAM_WEB}/blob/main/{rel}" + frag
        info = self.projects[owner]
        inner = rel[len(info["path"]):].lstrip("/")
        if not inner or inner == "README.md":
            return f"@app/{owner}" + frag
        if inner.endswith(".md"):
            return f"@apppage/{owner}/{self.page_slug(inner)}" + frag
        if (CODE_APPS / owner / inner).is_file():
            return f"@appcode/{owner}/{inner}"
        return f"@app/{owner}" + frag

    @staticmethod
    def page_slug(rel_md: str) -> str:
        stem = rel_md[:-3] if rel_md.endswith(".md") else rel_md
        parts = [p for p in stem.split("/") if p]
        if len(parts) > 1 and parts[-1].upper() == "README":
            parts = parts[:-1]
        return slugify("-".join(parts))

    def rewrite(self, text: str, md_file: Path, pid: str) -> str:
        def md_sub(m):
            tok = self.resolve(m.group(2), md_file, pid)
            return m.group(1) + (tok if tok is not None else m.group(2)) + m.group(3)

        def html_sub(m):
            tok = self.resolve(m.group(3), md_file, pid)
            return m.group(0) if tok is None else f"{m.group(1)}{m.group(2)}{tok}{m.group(2)}"

        text = MD_LINK_RE.sub(md_sub, text)
        text = HTML_SRC_RE.sub(html_sub, text)
        text = re.sub(r"!\[[^\]]*\]\(@missing\)\s*", "", text)
        text = re.sub(r"\[([^\]]*)\]\(@missing\)", r"\1", text)
        return re.sub(r"<img\b[^>]*?src=([\"'])@missing\1[^>]*>", "", text, flags=re.IGNORECASE)

    # ------------------------------------------------------------- ingestion

    def ingest(self) -> None:
        for d in (CONTENT_APPS, CODE_APPS):
            if d.exists():
                shutil.rmtree(d)

        for pid, info in self.projects.items():
            src = info["dir"]
            kept, skipped = copy_code_tree(src, CODE_APPS / pid)

            pages: list[str] = []
            for md in sorted(src.rglob("*.md")):
                if not is_clean(md, self.up):
                    continue
                text = md.read_text(encoding="utf-8", errors="replace")
                if not text.strip():
                    continue
                rel = md.relative_to(src).as_posix()
                out = CONTENT_APPS / pid / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(self.rewrite(text, md, pid).rstrip() + "\n", encoding="utf-8")
                pages.append(rel)

            if "README.md" not in pages:
                self.warnings.append(f"projet sans README : {pid}")
                continue

            readme = (CONTENT_APPS / pid / "README.md").read_text(encoding="utf-8")
            self.manifest["projects"][pid] = {
                "path": info["path"],
                "name": info["name"],
                "category": info["cat_slug"],
                "slug": info["slug"],
                "title_en": first_heading(readme) or info["name"].replace("_", " ").title(),
                "features": extract_features(readme),
                "pages": pages,
                "code": kept,
                "skipped": skipped,
            }
            for s in skipped:
                self.manifest["skipped"].append({"project": pid, **s})
            cat = self.manifest["categories"].setdefault(
                info["cat_slug"], {"path": info["cat_path"], "projects": []})
            cat["projects"].append(pid)

        for cat in self.manifest["categories"].values():
            cat["projects"].sort()
        self.manifest["images"] = self.images.count

        CONTENT.mkdir(parents=True, exist_ok=True)
        (CONTENT / "_apps.json").write_text(
            json.dumps(self.manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

        n_pages = sum(len(p["pages"]) for p in self.manifest["projects"].values())
        n_code = sum(len(p["code"]) for p in self.manifest["projects"].values())
        log("")
        log(f"✓ {len(self.manifest['projects'])} ateliers dans "
            f"{len(self.manifest['categories'])} catégories · {n_pages} pages · "
            f"{n_code} fichiers de code · {self.images.count} images · "
            f"{len(self.manifest['skipped'])} fichiers écartés")
        for cat_slug, cat in sorted(self.manifest["categories"].items()):
            log(f"  {cat_slug:<45} {len(cat['projects'])} atelier(s)")
        if self.warnings:
            log(f"⚠ {len(self.warnings)} avertissement(s) :")
            for w in self.warnings[:15]:
                log(f"   - {w}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM,
                    help="chemin du clone d'awesome-llm-apps (cloné si absent)")
    args = ap.parse_args()

    upstream = shallow_clone(UPSTREAM_URL, args.upstream.resolve(),
                             marker=args.upstream.resolve() / "rag_tutorials")
    ing = AppIngest(upstream)
    ing.discover()
    ing.ingest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
