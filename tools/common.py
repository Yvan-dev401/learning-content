#!/usr/bin/env python3
"""Mécaniques partagées par les deux scripts d'ingestion.

`ingest.py` (cours Microsoft) et `ingest_apps.py` (ateliers awesome-llm-apps) importent
deux dépôts très différents, mais avec les mêmes contraintes : nommer et dédoublonner les
images dans un pool commun, ne copier que le code utile, et écarter ce qui est trop lourd.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
# Code et images vivent directement là où le site les sert : ce sont les seules copies
# du dépôt. Les dupliquer ailleurs coûterait une vingtaine de mégaoctets pour rien.
CODE = ROOT / "docs" / "assets" / "code"
IMAGES = ROOT / "docs" / "assets" / "images"

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
CODE_SKIP_DIRS = {
    "node_modules", "bin", "obj", ".venv", "venv", "__pycache__", ".vscode", ".idea",
    "images", "img", "assets", ".git", ".next", "dist", "build", ".pytest_cache",
}
MAX_CODE_BYTES = 1_000_000
# Au-delà, l'image n'est pas embarquée : les dépôts sources contiennent des GIF de
# démonstration de plusieurs dizaines de Mo, hors de proportion pour un dépôt de cours.
MAX_IMAGE_BYTES = 2_000_000

# `[texte](cible)` et `<img src="cible">`. On ne réécrit une cible que si elle résout vers
# un fichier existant du dépôt source, ce qui écarte d'office les data: URI des blocs de code.
MD_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
HTML_SRC_RE = re.compile(r"""(<img\b[^>]*?\bsrc=)(["'])([^"']+)\2""", re.IGNORECASE)
# Images traduites par Co-op Translator : `<nom>.<hash>.webp`.
HASHED_NAME_RE = re.compile(r"^(?P<stem>.+)\.[0-9a-f]{12,20}(?P<ext>\.[A-Za-z0-9]+)$")


def log(msg: str) -> None:
    print(msg, flush=True)


def shallow_clone(url: str, path: Path, marker: Path | None = None) -> Path:
    """Clone `url` en profondeur 1 si `path` ne contient pas déjà le dépôt."""
    if (marker or path / ".git").exists():
        log(f"→ dépôt source déjà présent : {path}")
        return path
    if path.exists():
        shutil.rmtree(path)
    log(f"→ clonage de {url} vers {path} (depth=1)…")
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, str(path)], check=True)
    return path


class ImagePool:
    """Pool d'images commun à `docs/assets/images/`.

    Les deux dépôts sources contiennent des noms très génériques (`demo.png`, `banner.png`).
    Le préfixe passé à `target()` sert à désambiguïser, et un compteur tranche les collisions
    restantes — deux sources distinctes n'écrasent jamais le même fichier.
    """

    def __init__(self) -> None:
        self.by_source: dict[Path, str] = {}
        self.used: set[str] = set()
        self.count = 0
        self.oversized: list[tuple[Path, int]] = []

    def target(self, src: Path, prefix: str = "") -> str | None:
        """Nom publié de l'image, ou None si elle dépasse le plafond — à charge de
        l'appelant de renvoyer alors vers le dépôt d'origine."""
        if src in self.by_source:
            return self.by_source[src]
        size = src.stat().st_size
        if size > MAX_IMAGE_BYTES:
            self.oversized.append((src, size))
            return None
        m = HASHED_NAME_RE.match(src.name)
        base = (m.group("stem") + m.group("ext")) if m else src.name
        base = re.sub(r"[^\w.\-]+", "-", base).strip("-") or "image.png"
        name = base
        if name in self.used:
            name = f"{prefix}-{base}" if prefix else base
            n = 2
            while name in self.used:
                name = f"{prefix}-{n}-{base}" if prefix else f"{n}-{base}"
                n += 1
        self.used.add(name)
        self.by_source[src] = name
        IMAGES.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, IMAGES / name)
        self.count += 1
        return name


def copy_code_tree(src_dir: Path, dest_dir: Path, *,
                   skip_dirs: set[str] = CODE_SKIP_DIRS,
                   max_bytes: int = MAX_CODE_BYTES,
                   skip_markdown: bool = True) -> tuple[list[str], list[dict]]:
    """Copie les fichiers de code d'un dossier, en écartant images, binaires et poids lourds.

    Renvoie (fichiers conservés, fichiers écartés avec leur motif) — les écartés sont
    signalés sur le site plutôt que passés sous silence.
    """
    kept: list[str] = []
    skipped: list[dict] = []
    if not src_dir.is_dir():
        return kept, skipped
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src_dir)
        if set(rel.parts[:-1]) & skip_dirs:
            continue
        if skip_markdown and rel.suffix.lower() == ".md":
            continue
        if rel.suffix.lower() in IMAGE_EXT:
            skipped.append({"path": str(rel), "reason": "image", "size": path.stat().st_size})
            continue
        size = path.stat().st_size
        if size > max_bytes:
            skipped.append({"path": str(rel), "reason": "trop volumineux", "size": size})
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append({"path": str(rel), "reason": "binaire", "size": size})
            continue
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        kept.append(rel.as_posix())
    return kept, skipped
