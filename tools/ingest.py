#!/usr/bin/env python3
"""Importe le contenu français du cours « Generative AI for Beginners » de Microsoft.

Le dépôt source mélange 50+ traductions, des images traduites nommées avec un hash
et des chemins relatifs profonds (`../../../translated_images/fr/...`). Ce script en
extrait la version française, réécrit les liens et les images sous une forme stable,
et dépose le résultat dans `content/`, `code/` et `docs/assets/images/`.

Les liens sont réécrits sous forme de jetons résolus ensuite par `build.py` :
    @home                     accueil du site
    @lesson/<slug>            page d'une leçon
    @page/<slug>/<nom>        page annexe d'une leçon (sans l'extension .md)
    @annexes                  index des annexes
    @annexe/<cle>             page d'annexe
    @code/<slug>/<chemin>     fichier de code de la leçon
    @img/<nom>                image

Usage :  python3 tools/ingest.py [--upstream <chemin-du-clone>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
CODE = ROOT / "code"
IMAGES = ROOT / "docs" / "assets" / "images"

UPSTREAM_URL = "https://github.com/microsoft/generative-ai-for-beginners.git"
DEFAULT_UPSTREAM = Path(
    os.environ.get("GENAI_UPSTREAM", "")
) if os.environ.get("GENAI_UPSTREAM") else ROOT.parent / "generative-ai-upstream"

# Motifs sparse-checkout : tout sauf les traductions et images traduites des autres langues.
SPARSE = [
    "/*",
    "!/translations/*",
    "/translations/fr/*",
    "!/translated_images/*",
    "/translated_images/fr/*",
    "!/presentations/*",
]

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
CODE_SKIP_DIRS = {"node_modules", "bin", "obj", ".venv", "__pycache__", ".vscode", "images", "img", ".git"}
MAX_CODE_BYTES = 1_000_000

# `[texte](cible)` et `<img src="cible">` — on ne réécrit que si la cible résout
# vers un fichier existant du dépôt source, ce qui écarte les data: URI des blocs de code.
MD_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
HTML_SRC_RE = re.compile(r"""(<img\b[^>]*?\bsrc=)(["'])([^"']+)\2""", re.IGNORECASE)
TRACKING_RE = re.compile(r"[?&]WT\.mc_id=[^)\s\"'#]*")
HASHED_NAME_RE = re.compile(r"^(?P<stem>.+)\.[0-9a-f]{12,20}(?P<ext>\.[A-Za-z0-9]+)$")
# Encart ajouté automatiquement en pied de page par Co-op Translator.
DISCLAIMER_RE = re.compile(
    r"\n---\s*\n+\*\*(?:Avertissement|Clause de non-responsabilité)\*\*\s*:?.*\Z",
    re.DOTALL,
)


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_upstream(path: Path) -> Path:
    """Clone le dépôt source en sparse-checkout s'il n'est pas déjà présent."""
    if (path / "translations" / "fr" / "README.md").exists():
        log(f"→ dépôt source déjà présent : {path}")
        return path
    if path.exists():
        shutil.rmtree(path)
    log(f"→ clonage de {UPSTREAM_URL} vers {path} (sparse, depth=1)…")
    subprocess.run(
        ["git", "clone", "--no-checkout", "--depth", "1", "--quiet", UPSTREAM_URL, str(path)],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "sparse-checkout", "init", "--no-cone"], check=True)
    (path / ".git" / "info" / "sparse-checkout").write_text("\n".join(SPARSE) + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "checkout", "--quiet"], check=True)
    return path


class Ingest:
    def __init__(self, upstream: Path, meta: dict):
        self.up = upstream
        self.fr = upstream / "translations" / "fr"
        self.meta = meta
        self.lessons: list[str] = [s for t in meta["tracks"] for s in t["lessons"]]
        self.annexes: dict[str, dict] = meta["annexes"]["pages"]
        # source du fichier annexe -> clé d'annexe, pour réécrire les liens vers eux
        self.annexe_by_src = {v["source"]: k for k, v in self.annexes.items()}
        self.image_names: dict[Path, str] = {}   # source absolue -> nom de sortie
        self.used_names: set[str] = set()
        self.__originals: dict[str, Path] | None = None
        self.manifest: dict = {"lessons": {}, "annexes": {}, "images": 0, "skipped": []}
        self.warnings: list[str] = []

    # ---------------------------------------------------------------- images

    def image_target(self, src: Path, slug: str) -> str:
        """Nom de sortie stable pour une image, hash Co-op Translator retiré."""
        if src in self.image_names:
            return self.image_names[src]
        m = HASHED_NAME_RE.match(src.name)
        base = (m.group("stem") + m.group("ext")) if m else src.name
        name = base
        if name in self.used_names:
            name = f"{slug}-{base}"
            n = 2
            while name in self.used_names:
                name = f"{slug}-{n}-{base}"
                n += 1
        self.used_names.add(name)
        self.image_names[src] = name
        IMAGES.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, IMAGES / name)
        self.manifest["images"] += 1
        return name

    def find_original_image(self, missing: Path) -> Path | None:
        """Repli sur l'image anglaise d'origine quand la variante traduite manque.

        Les images traduites s'appellent `<nom>.<hash>.webp` ; l'originale porte le
        même `<nom>` avec son extension d'origine, quelque part dans le dépôt source.
        """
        m = HASHED_NAME_RE.match(missing.name)
        stem = m.group("stem") if m else missing.stem
        if stem not in self._originals:
            return None
        return self._originals[stem]

    @property
    def _originals(self) -> dict[str, Path]:
        if self.__originals is None:
            index: dict[str, Path] = {}
            for lesson in self.lessons:
                for sub in ("images", "img"):
                    d = self.up / lesson / sub
                    if d.is_dir():
                        for f in d.iterdir():
                            if f.is_file() and f.suffix.lower() in IMAGE_EXT:
                                index.setdefault(f.stem, f)
            for f in (self.up / "images").glob("*"):
                if f.is_file() and f.suffix.lower() in IMAGE_EXT:
                    index.setdefault(f.stem, f)
            self.__originals = index
        return self.__originals

    # ----------------------------------------------------------------- liens

    def resolve(self, target: str, md_file: Path, slug: str) -> str | None:
        """Traduit une cible relative du dépôt source en jeton de site, ou None."""
        raw = target.split("#", 1)
        path_part, frag = raw[0], ("#" + raw[1] if len(raw) > 1 else "")
        path_part = TRACKING_RE.sub("", path_part)
        if not path_part:
            return "@self" + frag if frag else None
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", path_part) or path_part.startswith("//"):
            return None  # http:, mailto:, data:…
        if re.fullmatch(r"[^@\s/]+@[^@\s/]+\.[A-Za-z]{2,}", path_part):
            return "mailto:" + path_part  # adresse e-mail écrite sans le schéma

        abspath = (md_file.parent / path_part).resolve()
        try:
            abspath.relative_to(self.up.resolve())
        except ValueError:
            return None  # sort du dépôt source

        # Chemin exprimé relativement à la racine d'une leçon (côté FR ou côté anglais)
        try:
            rel = abspath.relative_to(self.fr.resolve())
            in_fr = True
        except ValueError:
            rel = abspath.relative_to(self.up.resolve())
            in_fr = False
        parts = rel.parts

        if not parts:  # lien vers la racine
            return "@home" + frag

        # Images : on les copie et on renvoie un jeton @img
        if abspath.suffix.lower() in IMAGE_EXT:
            found = abspath if abspath.is_file() else self.find_original_image(abspath)
            if found is None:
                self.warnings.append(f"image absente du dépôt source : {target} (dans {md_file.name})")
                return "@missing"
            return "@img/" + self.image_target(found, slug)

        # Documents transverses (CONTRIBUTING.md, SECURITY.md…) devenus des annexes
        key = self.annexe_by_src.get("/".join(parts))
        if key:
            return f"@annexe/{key}" + frag
        if parts[0] == "docs":
            return "@annexes" + frag

        if parts[0] not in self.lessons:
            return None
        slug_t, rest = parts[0], parts[1:]

        if not rest:
            return f"@lesson/{slug_t}" + frag
        rest_path = "/".join(rest)
        if rest_path == "README.md":
            return f"@lesson/{slug_t}" + frag
        if rest_path.endswith(".md"):
            if (self.fr / slug_t / rest_path).is_file() or not in_fr:
                return f"@page/{slug_t}/{rest_path[:-3]}" + frag
            return None
        # Fichier de code précis, ou dossier de code -> section « Code de la leçon »
        if (CODE / slug_t / rest_path).is_file():
            return f"@code/{slug_t}/{rest_path}"
        if abspath.is_dir() or (CODE / slug_t / rest_path).is_dir():
            return f"@lesson/{slug_t}#code"
        return None

    def rewrite(self, text: str, md_file: Path, slug: str) -> str:
        def md_sub(m: re.Match) -> str:
            token = self.resolve(m.group(2), md_file, slug)
            if token is None:
                return m.group(1) + TRACKING_RE.sub("", m.group(2)) + m.group(3)
            return m.group(1) + token + m.group(3)

        def html_sub(m: re.Match) -> str:
            token = self.resolve(m.group(3), md_file, slug)
            if token is None:
                return m.group(0)
            return f"{m.group(1)}{m.group(2)}{token}{m.group(2)}"

        text = MD_LINK_RE.sub(md_sub, text)
        text = HTML_SRC_RE.sub(html_sub, text)
        # Cibles absentes du dépôt source : on retire l'image, on garde le libellé du lien.
        text = re.sub(r"!\[[^\]]*\]\(@missing\)\s*", "", text)
        text = re.sub(r"\[([^\]]*)\]\(@missing\)", r"\1", text)
        text = re.sub(r"<img\b[^>]*?src=([\"'])@missing\1[^>]*>", "", text, flags=re.IGNORECASE)
        # Liens résiduels portant encore le paramètre de suivi (liens nus, bas de page)
        return TRACKING_RE.sub("", text)

    # -------------------------------------------------------------- fichiers

    def clean(self, text: str) -> str:
        text = DISCLAIMER_RE.sub("\n", text)
        return text.rstrip() + "\n"

    def ingest_markdown(self, src: Path, dest: Path, slug: str) -> bool:
        text = src.read_text(encoding="utf-8")
        if not text.strip():
            return False
        text = self.rewrite(self.clean(text), src, slug)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        return True

    def ingest_code(self, slug: str) -> tuple[list[str], list[dict]]:
        """Copie les fichiers de code de la leçon (le code n'est pas traduit)."""
        src_dir = self.up / slug
        kept: list[str] = []
        skipped: list[dict] = []
        if not src_dir.is_dir():
            return kept, skipped
        for path in sorted(src_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(src_dir)
            if set(rel.parts[:-1]) & CODE_SKIP_DIRS:
                continue
            if rel.suffix.lower() == ".md" or rel.name == "README.md":
                continue
            if rel.suffix.lower() in IMAGE_EXT:
                skipped.append({"path": str(rel), "reason": "image", "size": path.stat().st_size})
                continue
            size = path.stat().st_size
            if size > MAX_CODE_BYTES:
                skipped.append({"path": str(rel), "reason": "trop volumineux", "size": size})
                continue
            dest = CODE / slug / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            kept.append(str(rel).replace(os.sep, "/"))
        return kept, skipped

    # ------------------------------------------------------------------- run

    def run(self) -> None:
        for d in (CONTENT, CODE, IMAGES):
            for child in sorted(d.glob("*")) if d.exists() else []:
                if child.name == "_meta.json":
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()

        for slug in self.lessons:
            fr_dir = self.fr / slug
            if not fr_dir.is_dir():
                self.warnings.append(f"leçon absente de la traduction FR : {slug}")
                continue
            # Le code est copié en premier : la résolution des liens s'appuie dessus.
            code_files, skipped = self.ingest_code(slug)
            pages: list[str] = []
            for md in sorted(fr_dir.rglob("*.md")):
                rel = md.relative_to(fr_dir)
                if self.ingest_markdown(md, CONTENT / slug / rel, slug):
                    pages.append(str(rel).replace(os.sep, "/"))
                else:
                    self.warnings.append(f"page vide ignorée : {slug}/{rel}")
            self.manifest["lessons"][slug] = {
                "pages": pages,
                "code": code_files,
                "skipped": skipped,
            }
            for s in skipped:
                self.manifest["skipped"].append({"lesson": slug, **s})
            log(f"  {slug:<45} {len(pages)} page(s), {len(code_files)} fichier(s) de code")

        for key, info in self.annexes.items():
            src = self.fr / info["source"]
            if not src.is_file():
                self.warnings.append(f"annexe absente : {info['source']}")
                continue
            dest = CONTENT / "_annexes" / f"{key}.md"
            if self.ingest_markdown(src, dest, "_annexes"):
                self.manifest["annexes"][key] = {"source": info["source"]}
                log(f"  annexe {key:<38} ← {info['source']}")

        (CONTENT / "_ingest.json").write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        log("")
        log(f"✓ {len(self.manifest['lessons'])} leçons, {len(self.manifest['annexes'])} annexes, "
            f"{self.manifest['images']} images, {len(self.manifest['skipped'])} fichiers écartés")
        if self.warnings:
            log(f"⚠ {len(self.warnings)} avertissement(s) :")
            for w in self.warnings:
                log(f"   - {w}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM,
                    help="chemin du clone du dépôt source (cloné si absent)")
    args = ap.parse_args()

    upstream = ensure_upstream(args.upstream.resolve())
    meta = json.loads((CONTENT / "_meta.json").read_text(encoding="utf-8"))
    Ingest(upstream, meta).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
