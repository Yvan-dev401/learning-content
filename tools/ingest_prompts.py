#!/usr/bin/env python3
"""Importe les prompts système d'outils d'IA (dépôt x1xhlol, GPL-3.0).

Contrairement aux deux autres sources, il n'y a ici ni cours ni README par projet : juste
des fichiers de prompts bruts, un dossier par outil. La valeur pédagogique ne vient donc pas
du texte importé — elle vient de l'analyse française écrite dans `content/_prompts_meta.json`
et posée par `build.py` au-dessus de ces fichiers.

Un « outil » est le dossier le plus profond contenant directement des fichiers de prompt.
Cette règle sépare correctement `Anthropic/Claude Code` de `Anthropic`, ou les six produits
rangés sous `Open Source prompts`, sans liste codée en dur.

Les fichiers sont publiés tels quels sous `docs/assets/prompts-systeme/<outil>/`, à l'octet
près : ce sont des documents d'étude, les retoucher n'aurait aucun sens.

Usage :  python3 tools/ingest_prompts.py [--upstream <chemin-du-clone>]
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

from common import ROOT, log, shallow_clone

UPSTREAM_URL = "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools.git"
UPSTREAM_WEB = "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools"
DEFAULT_UPSTREAM = (
    Path(os.environ["PROMPTS_UPSTREAM"]) if os.environ.get("PROMPTS_UPSTREAM")
    else ROOT.parent / "system-prompts-upstream"
)

CONTENT = ROOT / "content"
PUBLISHED = ROOT / "docs" / "assets" / "prompts-systeme"

# Extensions considérées comme du contenu de prompt.
PROMPT_EXT = {".txt", ".md", ".yaml", ".yml"}
TOOLS_EXT = {".json"}
# Dossiers et fichiers du dépôt lui-même, sans rapport avec les outils décrits.
SKIP_DIRS = {".git", ".github", "assets", "node_modules"}
SKIP_ROOT_FILES = {"README.md", "LICENSE.md", "FUNDING.yml"}
MAX_FILE_BYTES = 1_000_000


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s.-]", " ", text.lower())
    text = re.sub(r"[\s_.]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text) or "outil"


def is_clean(path: Path, root: Path) -> bool:
    return not (set(path.relative_to(root).parts) & SKIP_DIRS)


def kind_of(path: Path) -> str | None:
    if path.name in SKIP_ROOT_FILES:
        return None
    suffix = path.suffix.lower()
    if suffix in TOOLS_EXT:
        return "outils"
    if suffix in PROMPT_EXT or not suffix:      # `plan_mode_prompts` n'a pas d'extension
        return "prompt"
    return None


def find_tools(root: Path) -> list[Path]:
    """Dossiers contenant *directement* au moins un fichier de prompt.

    Un dossier qui ne fait que regrouper des sous-dossiers n'est pas un outil ; un dossier
    qui a ses propres fichiers *et* des sous-dossiers donne un outil pour lui-même, plus un
    par sous-dossier (cas d'`Anthropic`).
    """
    out = []
    for d in sorted(p for p in root.rglob("*") if p.is_dir() and is_clean(p, root)):
        if any(f.is_file() and kind_of(f) for f in d.iterdir()):
            out.append(d)
    return out


def type_label(value) -> str:
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return str(value or "")


def read_tool_definitions(path: Path) -> list[dict] | None:
    """Extrait une liste d'outils d'un `.json`, quelle que soit sa forme."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if isinstance(data, dict):
        for key in ("tools", "functions", "definitions"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        return None
    tools = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") if isinstance(entry.get("function"), dict) else entry
        name = fn.get("name") or entry.get("name") or entry.get("type")
        if not name:
            continue
        params = fn.get("parameters") or fn.get("input_schema") or {}
        props = params.get("properties") if isinstance(params, dict) else None
        required = set(params.get("required") or []) if isinstance(params, dict) else set()
        tools.append({
            "name": str(name),
            "description": str(fn.get("description") or entry.get("description") or "").strip(),
            "params": [
                {
                    "name": str(pname),
                    # Un schéma JSON accepte `"type": ["string", "null"]` : on normalise ici
                    # plutôt que de laisser la surprise au générateur.
                    "type": type_label((pinfo or {}).get("type", "")),
                    "required": pname in required,
                    "description": str((pinfo or {}).get("description", "")).strip(),
                }
                for pname, pinfo in (props or {}).items()
                if isinstance(pname, str)
            ],
        })
    return tools or None


class PromptIngest:
    def __init__(self, upstream: Path):
        self.up = upstream
        self.manifest: dict = {"tools": {}, "skipped": []}
        self.warnings: list[str] = []
        self.used_ids: set[str] = set()

    def tool_id(self, rel: Path) -> str:
        tid = slugify("-".join(rel.parts))
        base, n = tid, 2
        while tid in self.used_ids:
            tid, n = f"{base}-{n}", n + 1
        self.used_ids.add(tid)
        return tid

    def run(self) -> None:
        if PUBLISHED.exists():
            shutil.rmtree(PUBLISHED)

        for d in find_tools(self.up):
            rel = d.relative_to(self.up)
            tid = self.tool_id(rel)
            files, tools_total, chars = [], 0, 0

            for f in sorted(d.iterdir()):
                if not f.is_file():
                    continue
                kind = kind_of(f)
                if kind is None:
                    self.manifest["skipped"].append(
                        {"tool": tid, "path": f.name, "reason": "hors périmètre",
                         "size": f.stat().st_size})
                    continue
                size = f.stat().st_size
                if size > MAX_FILE_BYTES:
                    self.manifest["skipped"].append(
                        {"tool": tid, "path": f.name, "reason": "trop volumineux", "size": size})
                    continue
                try:
                    text = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    self.manifest["skipped"].append(
                        {"tool": tid, "path": f.name, "reason": "binaire", "size": size})
                    continue

                entry = {"name": f.name, "kind": kind, "size": size,
                         "lines": text.count("\n") + 1}
                if kind == "outils":
                    defs = read_tool_definitions(f)
                    if defs:
                        entry["tools"] = defs
                        tools_total += len(defs)
                    else:
                        entry["kind"] = "prompt"      # JSON non reconnu : affiché tel quel
                chars += len(text)

                dest = PUBLISHED / tid / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)                 # copie à l'octet près, volontairement
                files.append(entry)

            if not files:
                self.warnings.append(f"outil sans fichier exploitable : {rel}")
                continue

            self.manifest["tools"][tid] = {
                "path": rel.as_posix(),
                "name": rel.name,
                "group": rel.parts[0] if len(rel.parts) > 1 else "",
                "files": files,
                "chars": chars,
                "tool_defs": tools_total,
            }

        CONTENT.mkdir(parents=True, exist_ok=True)
        (CONTENT / "_prompts.json").write_text(
            json.dumps(self.manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

        n_files = sum(len(t["files"]) for t in self.manifest["tools"].values())
        n_defs = sum(t["tool_defs"] for t in self.manifest["tools"].values())
        chars = sum(t["chars"] for t in self.manifest["tools"].values())
        log("")
        log(f"✓ {len(self.manifest['tools'])} outils · {n_files} fichiers · "
            f"{n_defs} définitions d'outils · {chars // 1000} k caractères de prompt · "
            f"{len(self.manifest['skipped'])} fichiers écartés")
        for tid, t in sorted(self.manifest["tools"].items()):
            log(f"  {tid:<40} {len(t['files'])} fichier(s), {t['chars'] // 1000} k car.")
        if self.warnings:
            log(f"⚠ {len(self.warnings)} avertissement(s) :")
            for w in self.warnings:
                log(f"   - {w}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM,
                    help="chemin du clone du dépôt de prompts (cloné si absent)")
    args = ap.parse_args()
    upstream = shallow_clone(UPSTREAM_URL, args.upstream.resolve(),
                             marker=args.upstream.resolve() / "README.md")
    PromptIngest(upstream).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
