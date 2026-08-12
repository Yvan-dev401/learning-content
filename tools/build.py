#!/usr/bin/env python3
"""Génère le site statique dans `docs/` à partir de `content/` et `code/`.

Le HTML produit est commité : consulter le site ne demande aucune installation,
ni serveur, ni build. Les URL pointent explicitement vers `index.html` pour que
le site fonctionne aussi bien sur GitHub Pages qu'ouvert depuis le disque.

Usage :  python3 tools/build.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DOCS = ROOT / "docs"
CODE = DOCS / "assets" / "code"     # copie unique, servie telle quelle par le site
ASSETS_SRC = Path(__file__).resolve().parent / "assets"

UPSTREAM = "https://github.com/microsoft/generative-ai-for-beginners"
UPSTREAM_FR = f"{UPSTREAM}/blob/main/translations/fr"
APPS_UPSTREAM = "https://github.com/Shubhamsaboo/awesome-llm-apps"
PROMPTS_UPSTREAM = "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools"

LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".js": "javascript", ".cs": "csharp",
    ".json": "json", ".jsonl": "json", ".sh": "bash", ".ps1": "powershell",
    ".bat": "batch", ".xml": "xml", ".csproj": "xml", ".yml": "yaml", ".yaml": "yaml",
    ".html": "html", ".css": "css", ".md": "markdown", ".txt": "text",
    ".dib": "text", ".env-sample": "ini", ".gitignore": "text",
}
# Fichiers d'`assets/` produits par ce script, et donc les seuls qu'il ait le droit
# d'effacer avant de régénérer. Le reste appartient aux scripts d'ingestion.
BUILD_ASSETS = {"style.css", "app.js", "highlight.css", "search-index.js"}
COLLECTIONS = {
    "cours":    {"order": 1, "icon": "📘", "label": "Leçon",  "plural": "Leçons",
                 "verb": "Apprendre", "url": "index.html"},
    "ateliers": {"order": 2, "icon": "🧪", "label": "Atelier", "plural": "Ateliers",
                 "verb": "Construire", "url": "ateliers/index.html"},
    "prompts":  {"order": 3, "icon": "🔍", "label": "Prompt système", "plural": "Prompts système",
                 "verb": "Décortiquer", "url": "prompts-systeme/index.html"},
}
# Sert à ordonner les prompts : les plus instructifs d'abord.
COLLECTION_ORDER_HINT = {"incontournable": 0, "tres-demande": 1, "utile": 2, "survol": 3}
GROUP_LABELS = {
    "python": "Python", "typescript": "TypeScript", "javascript": "JavaScript",
    "js-githubmodels": "JavaScript (GitHub Models)", "dotnet": ".NET", "scripts": "Scripts",
    "": "Fichiers",
}
# Paramètre de suivi Microsoft, encore présent dans les cellules des notebooks.
TRACKING_RE = re.compile(r"[?&]WT\.mc_id=[^)\s\"'#]*")
# Fichiers présents pour être exécutés, pas pour être lus.
NO_RENDER = re.compile(r"(package-lock\.json|\.jsonl)$")
MAX_RENDER_BYTES = 60_000
SEARCH_BODY_CHARS = 6000


# --------------------------------------------------------------------- outils

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text) or "section"


def page_slug(rel_md: str) -> str:
    """`scripts/README.md` -> `scripts`, `data/frameworks.md` -> `data-frameworks`."""
    stem = rel_md[:-3] if rel_md.endswith(".md") else rel_md
    parts = [p for p in stem.split("/") if p]
    if len(parts) > 1 and parts[-1].upper() == "README":
        parts = parts[:-1]
    return slugify("-".join(parts))


def path_anchor(rel: str) -> str:
    """Ancre lisible pour un fichier de code : `python/aoai-app.py` -> `python-aoai-app-py`."""
    return "code-" + slugify(rel.replace("/", "-").replace(".", "-"))


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} o"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} ko"
    return f"{n / 1024 / 1024:.1f} Mo"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def highlight_code(code: str, lang: str) -> str:
    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            return f'<pre class="highlight"><code>{esc(code)}</code></pre>'
    return highlight(code, lexer, HtmlFormatter(nowrap=False, cssclass="highlight"))


def code_block(code: str, lang: str, label: str | None = None) -> str:
    body = highlight_code(code, lang or "text")
    tag = esc(label or lang or "texte")
    return (
        '<div class="codeblock">'
        f'<div class="codeblock__bar"><span class="codeblock__lang">{tag}</span>'
        '<button class="codeblock__copy" type="button" aria-label="Copier le code">Copier</button></div>'
        f"{body}</div>"
    )


# ------------------------------------------------------------------ le modèle

def read_json(path: Path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class Site:
    def __init__(self) -> None:
        self.meta = json.loads((CONTENT / "_meta.json").read_text(encoding="utf-8"))
        self.ingest = json.loads((CONTENT / "_ingest.json").read_text(encoding="utf-8"))
        self.apps = read_json(CONTENT / "_apps.json", {"categories": {}, "projects": {}})
        self.apps_meta = read_json(CONTENT / "_apps_meta.json", {"categories": {}, "projects": {}})
        self.services = read_json(CONTENT / "_services.json", {"categories": {}, "services": {}})
        self.prompts = read_json(CONTENT / "_prompts.json", {"tools": {}, "skipped": []})
        self.prompts_meta = read_json(CONTENT / "_prompts_meta.json", {"tools": {}})
        self.topicdef = read_json(CONTENT / "_topics.json", {"topics": {}})["topics"]
        self.sectiondef = read_json(CONTENT / "_prompt_sections.json", {"sections": {}})["sections"]
        filedef = read_json(CONTENT / "_prompt_files.json", {"files": {}, "status_labels": {}})
        self.filedef = filedef["files"]
        self.status_labels = filedef.get("status_labels", {})
        self.tagdef = self.meta.get("tags", {"groups": {}, "values": {}})
        self.tracks = self.meta["tracks"]
        self.lesson_meta = self.meta["lessons"]
        self.annexe_meta = self.meta["annexes"]
        self.order: list[str] = [s for t in self.tracks for s in t["lessons"]]
        self.track_of: dict[str, dict] = {s: t for t in self.tracks for s in t["lessons"]}
        self.code_index: dict[str, list[dict]] = {}
        self.subpages: dict[str, list[dict]] = {}   # slug -> [{slug, title, rel}]
        self.flat: list[dict] = []                  # ordre de lecture complet
        self.search: list[dict] = []
        self.warnings: list[str] = []
        # Ateliers : catégories triées, projets, et détection de services par page.
        self.cat_order: list[str] = sorted(
            self.apps["categories"],
            key=lambda c: (self.apps_meta["categories"].get(c, {}).get("order", 99), c),
        )
        self.app_order: list[str] = [p for c in self.cat_order
                                     for p in self.apps["categories"][c]["projects"]]
        self.app_subpages: dict[str, list[dict]] = {}
        self.services_of: dict[str, list[str]] = {}   # id de page -> ids de services
        self.tags_of: dict[str, list[str]] = {}       # id de page -> tags résolus
        self.prompt_order: list[str] = sorted(
            self.prompts["tools"],
            key=lambda t: (COLLECTION_ORDER_HINT.get(
                self.prompts_meta["tools"].get(t, {}).get("tags", ["utile"])[0], 9),
                self.prompts_meta["tools"].get(t, {}).get("title", t)),
        )
        # Registre unifié : tout ce qui donne une page de contenu, quelle que soit sa famille.
        # C'est ce qui permet aux sujets, au catalogue et à la recherche de traiter les trois
        # collections de la même façon — et à une quatrième source de ne rien coûter.
        self.items: dict[str, dict] = {}
        self.topics_of: dict[str, list[str]] = {}
        # Les notebooks référencent les images anglaises : on les retrouve par leur nom
        # de base parmi celles déjà publiées (la variante traduite porte le même nom).
        img_dir = DOCS / "assets" / "images"
        self.image_by_stem: dict[str, str] = {
            p.stem: p.name for p in sorted(img_dir.glob("*")) if p.is_file()
        }

    # -- code -------------------------------------------------------------

    def scan_code(self) -> None:
        """Indexe le code des leçons et des ateliers sous un identifiant commun :
        `<slug de leçon>` ou `ateliers/<catégorie>/<projet>`."""
        sources = [(slug, self.ingest["lessons"].get(slug, {}).get("code", []))
                   for slug in self.order]
        sources += [(f"ateliers/{pid}", self.apps["projects"][pid]["code"])
                    for pid in self.app_order]
        for owner, files in sources:
            entries = []
            for rel in files:
                path = CODE / owner / rel
                if not path.is_file():
                    self.warnings.append(f"fichier de code manquant : {owner}/{rel}")
                    continue
                entries.append({
                    "rel": rel,
                    "group": rel.split("/")[0] if "/" in rel else "",
                    "size": path.stat().st_size,
                    "anchor": path_anchor(rel),
                    "path": path,
                })
            self.code_index[owner] = entries

    def code_groups(self, owner: str) -> list[tuple[str, list[dict]]]:
        groups: dict[str, list[dict]] = {}
        for e in self.code_index.get(owner, []):
            groups.setdefault(e["group"], []).append(e)
        return sorted(groups.items(), key=lambda kv: (kv[0] == "", kv[0]))

    # -- services et tags --------------------------------------------------

    def scan_services(self) -> None:
        """Repère, pour chaque page, les services externes réellement exigés.

        Les motifs de `_services.json` visent les identifiants à obtenir (variables
        d'environnement, paquets), pas les simples mentions dans le texte : c'est ce qui
        conditionne vraiment la possibilité d'exécuter l'exercice.
        """
        defs = self.services["services"]
        compiled = {sid: [re.compile(p, re.MULTILINE) for p in s["detect"]]
                    for sid, s in defs.items()}

        def scan(owner: str, md_dir: Path) -> None:
            chunks: list[str] = []
            for md in sorted(md_dir.rglob("*.md")):
                chunks.append(md.read_text(encoding="utf-8", errors="replace"))
            for entry in self.code_index.get(owner, []):
                try:
                    chunks.append(entry["path"].read_text(encoding="utf-8"))
                except (UnicodeDecodeError, OSError):
                    pass
            blob = "\n".join(chunks)
            self.services_of[owner] = [sid for sid, pats in compiled.items()
                                       if any(p.search(blob) for p in pats)]

        for slug in self.order:
            scan(slug, CONTENT / slug)
        for pid in self.app_order:
            scan(f"ateliers/{pid}", CONTENT / "ateliers" / pid)

    def cost_tag(self, owner: str) -> str:
        costs = {self.services["services"][s]["cost"] for s in self.services_of.get(owner, [])}
        if "payant" in costs:
            return "payant"
        if "freemium" in costs:
            return "palier-gratuit"
        return "gratuit"

    def group_of(self, tag: str) -> str:
        return self.tagdef["values"].get(tag, {}).get("group", "")

    def sort_tags(self, tags: list[str]) -> list[str]:
        groups = self.tagdef["groups"]
        return sorted(
            dict.fromkeys(t for t in tags if t in self.tagdef["values"]),
            key=lambda t: groups.get(self.group_of(t), {}).get("order", 99),
        )

    def scan_tags(self) -> None:
        for slug in self.order:
            tags = list(self.lesson_meta[slug].get("tags", []))
            self.tags_of[slug] = self.sort_tags(tags + [self.cost_tag(slug)])

        for pid in self.app_order:
            cat = self.apps["projects"][pid]["category"]
            defaults = self.apps_meta["categories"].get(cat, {}).get("defaults", {})
            chosen = {g: t for g, t in
                      ((self.group_of(t), t) for t in defaults.values()) if g}
            for t in self.apps_meta["projects"].get(pid, {}).get("tags", []):
                g = self.group_of(t)
                if g:
                    chosen[g] = t          # le tag du projet l'emporte sur celui de sa catégorie
            owner = f"ateliers/{pid}"
            chosen["nature"] = chosen.get("nature", "pratique")
            chosen["cout"] = self.cost_tag(owner)
            self.tags_of[owner] = self.sort_tags(list(chosen.values()))

        for tid in self.prompt_order:
            fr = self.prompts_meta["tools"].get(tid, {})
            chosen = {g: t for g, t in
                      ((self.group_of(t), t) for t in fr.get("tags", [])) if g}
            chosen.setdefault("interet", "utile")
            chosen.setdefault("difficulte", "intermediaire")
            # Un prompt se lit : rien à installer, rien à payer.
            chosen["nature"] = chosen.get("nature", "theorie")
            chosen["cout"] = "gratuit"
            self.tags_of[f"prompts/{tid}"] = self.sort_tags(list(chosen.values()))

        unknown = {t for tags in self.tags_of.values() for t in tags} - set(self.tagdef["values"])
        for t in sorted(unknown):
            self.warnings.append(f"tag absent du vocabulaire : {t}")

    # -- ateliers ----------------------------------------------------------

    def app(self, pid: str) -> dict:
        """Vue fusionnée d'un atelier : données extraites + habillage français."""
        raw = self.apps["projects"][pid]
        fr = self.apps_meta["projects"].get(pid, {})
        summary = fr.get("summary")
        if not summary:
            feats = raw.get("features") or []
            summary = (feats[0] if feats else "Projet importé du dépôt awesome-llm-apps.")
        return {
            "id": pid,
            "cat": raw["category"],
            "slug": raw["slug"],
            "path": raw["path"],
            "title": fr.get("title") or raw["title_en"],
            "title_en": raw["title_en"],
            "summary": summary,
            "features": raw.get("features") or [],
            "code": raw["code"],
            "skipped": raw.get("skipped", []),
            "tags": self.tags_of.get(f"ateliers/{pid}", []),
            "services": self.services_of.get(f"ateliers/{pid}", []),
            "url": f"ateliers/{pid}/index.html",
        }

    def category(self, cat: str) -> dict:
        fr = self.apps_meta["categories"].get(cat, {})
        return {
            "id": cat,
            "title": fr.get("title") or cat.replace("-", " ").capitalize(),
            "summary": fr.get("summary", ""),
            "icon": fr.get("icon", "🧰"),
            "lessons": [s for s in fr.get("lessons", []) if s in self.lesson_meta],
            "projects": self.apps["categories"][cat]["projects"],
            "url": f"ateliers/{cat}/index.html",
        }

    def categories_for_lesson(self, slug: str) -> list[dict]:
        return [self.category(c) for c in self.cat_order
                if slug in self.apps_meta["categories"].get(c, {}).get("lessons", [])]

    # -- prompts système ---------------------------------------------------

    def prompt(self, tid: str) -> dict:
        """Vue fusionnée d'un outil : fichiers extraits + habillage français."""
        raw = self.prompts["tools"][tid]
        fr = self.prompts_meta["tools"].get(tid, {})
        owner = f"prompts/{tid}"
        return {
            "id": tid,
            "path": raw["path"],
            "title": fr.get("title") or raw["name"],
            "editor": fr.get("editor", ""),
            "what": fr.get("what", ""),
            "learn": fr.get("learn", []),
            "files": raw["files"],
            "chars": raw["chars"],
            "tool_defs": raw["tool_defs"],
            "lessons": [l for l in fr.get("lessons", []) if l in self.lesson_meta],
            "tags": self.tags_of.get(owner, []),
            "topics": self.topics_of.get(owner, []),
            "url": f"prompts-systeme/{tid}/index.html",
        }

    def prompt_file(self, tid: str, name: str) -> dict:
        """Fiche française d'un fichier de prompt, vide si le fichier n'est pas répertorié."""
        return self.filedef.get(f"{tid}/{name}", {})

    def prompt_observations(self, tid: str) -> list[str]:
        """Constats mesurés sur les fichiers, par opposition à l'analyse rédigée.

        Ce qui est calculé ici ne peut pas se tromper : longueur, mode de structuration,
        nombre d'outils déclarés. L'avis éditorial reste dans `_prompts_meta.json`.
        """
        raw = self.prompts["tools"][tid]
        texts = []
        for f in raw["files"]:
            path = DOCS / "assets" / "prompts-systeme" / tid / f["name"]
            if f["kind"] == "prompt" and path.is_file():
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
        blob = "\n".join(texts)
        if not blob.strip():
            return []
        words = len(blob.split())
        obs = [f"Environ <strong>{words:,} mots</strong> répartis sur "
               f"{len(raw['files'])} fichier(s)."
               .replace(",", " ")]
        xml = len(re.findall(r"^<[a-z][a-z0-9_]*>\s*$", blob, re.MULTILINE))
        md = len(re.findall(r"^#{1,3} \S", blob, re.MULTILINE))
        if xml >= 3:
            obs.append(f"Structuré par <strong>balises</strong> : {xml} blocs délimités "
                       f"(<code>&lt;nom&gt;…&lt;/nom&gt;</code>).")
        elif md >= 3:
            obs.append(f"Structuré par <strong>titres Markdown</strong> : {md} sections.")
        else:
            obs.append("Texte peu structuré : ni balises ni titres marqués.")
        if raw["tool_defs"]:
            obs.append(f"<strong>{raw['tool_defs']} outils</strong> déclarés dans un fichier "
                       f"séparé, avec leurs paramètres.")
        interdits = len(re.findall(r"\b(never|must not|do not|don't|avoid|refuse)\b", blob, re.I))
        if interdits:
            obs.append(f"<strong>{interdits} interdictions</strong> explicites "
                       f"(« never », « must not », « do not »…) — l'essentiel du cadrage "
                       f"passe par ce qu'il ne faut pas faire.")
        return obs

    # -- registre unifié ---------------------------------------------------

    def register_items(self) -> None:
        """Convertit les trois manifestes en éléments de même forme."""
        for slug in self.order:
            lm, track = self.lesson_meta[slug], self.track_of[slug]
            self.items[slug] = {
                "id": slug, "pkey": slug, "collection": "cours", "title": lm["title"],
                "summary": lm["summary"], "url": f"lecons/{slug}/index.html",
                "context": track["title"], "label": f'Leçon {lm["num"]}',
                "declared_topics": lm.get("topics", []),
                "headings": [],
            }
        for pid in self.app_order:
            raw, fr = self.apps["projects"][pid], self.apps_meta["projects"].get(pid, {})
            cat = self.apps_meta["categories"].get(raw["category"], {})
            self.items[f"ateliers/{pid}"] = {
                "id": f"ateliers/{pid}", "pkey": f"atelier:{pid}", "collection": "ateliers",
                "title": fr.get("title") or raw["title_en"],
                "summary": fr.get("summary") or (raw.get("features") or [""])[0],
                "url": f"ateliers/{pid}/index.html",
                "context": cat.get("title", ""), "label": "Atelier",
                "declared_topics": fr.get("topics") or cat.get("topics", []),
                "headings": raw.get("features", []),
            }
        for tid in self.prompt_order:
            fr = self.prompts_meta["tools"].get(tid, {})
            raw = self.prompts["tools"][tid]
            self.items[f"prompts/{tid}"] = {
                "id": f"prompts/{tid}", "pkey": f"prompt:{tid}", "collection": "prompts",
                "title": fr.get("title") or raw["name"],
                "summary": fr.get("what", ""),
                "url": f"prompts-systeme/{tid}/index.html",
                "context": fr.get("editor", ""), "label": "Prompt système",
                "declared_topics": fr.get("topics", []),
                "headings": fr.get("learn", []),
            }

    def scan_topics(self) -> None:
        """Sujet déclaré d'abord ; sinon détection par mots-clés sur titre, résumé et
        intertitres — jamais sur le corps entier, qui produirait trop de faux positifs."""
        patterns = {
            tid: re.compile("|".join(re.escape(k) for k in t["keywords"]), re.IGNORECASE)
            for tid, t in self.topicdef.items() if t.get("keywords")
        }
        for iid, item in self.items.items():
            topics = [t for t in item["declared_topics"] if t in self.topicdef]
            if not topics:
                blob = " ".join([item["title"], item["summary"]] + list(item["headings"]))
                topics = [tid for tid, pat in patterns.items() if pat.search(blob)]
            item["topics"] = self.sort_topics(topics)
            self.topics_of[iid] = item["topics"]
            if not topics:
                self.warnings.append(f"contenu sans sujet : {iid}")

    def sort_topics(self, topics: list[str]) -> list[str]:
        return sorted(dict.fromkeys(t for t in topics if t in self.topicdef),
                      key=lambda t: self.topicdef[t]["order"])

    def items_by_topic(self, topic: str, collection: str | None = None) -> list[dict]:
        return [i for i in self.items.values()
                if topic in i.get("topics", [])
                and (collection is None or i["collection"] == collection)]

    def related_items(self, iid: str, limit: int = 6) -> list[dict]:
        """Contenus des *autres* familles partageant un sujet — c'est le lien entre
        « sujets similaires » que réclamait la réorganisation."""
        item = self.items.get(iid)
        if not item or not item.get("topics"):
            return []
        mine = set(item["topics"])
        scored = []
        for other in self.items.values():
            if other["id"] == iid or other["collection"] == item["collection"]:
                continue
            shared = mine & set(other.get("topics", []))
            if shared:
                scored.append((len(shared), other))
        scored.sort(key=lambda kv: (-kv[0], kv[1]["collection"], kv[1]["title"]))
        out, seen = [], set()
        for _, other in scored:                    # équilibrer entre les familles
            if sum(1 for o in out if o["collection"] == other["collection"]) >= limit // 2:
                continue
            if other["id"] in seen:
                continue
            seen.add(other["id"])
            out.append(other)
            if len(out) >= limit:
                break
        return out

    # -- pages ------------------------------------------------------------

    def scan_app_pages(self) -> None:
        for pid in self.app_order:
            subs = []
            for rel in self.apps["projects"][pid]["pages"]:
                if rel == "README.md":
                    continue
                md = (CONTENT / "ateliers" / pid / rel).read_text(encoding="utf-8")
                subs.append({
                    "slug": page_slug(rel),
                    "rel": rel,
                    "title": first_heading(md) or page_slug(rel).replace("-", " ").capitalize(),
                })
            subs.sort(key=lambda p: p["rel"])
            self.app_subpages[pid] = subs

    def scan_pages(self) -> None:
        for slug in self.order:
            info = self.ingest["lessons"].get(slug, {})
            subs = []
            for rel in info.get("pages", []):
                if rel == "README.md":
                    continue
                md = (CONTENT / slug / rel).read_text(encoding="utf-8")
                subs.append({
                    "slug": page_slug(rel),
                    "rel": rel,
                    "title": first_heading(md) or page_slug(rel).replace("-", " ").capitalize(),
                })
            subs.sort(key=lambda p: p["rel"])
            self.subpages[slug] = subs

        for slug in self.order:
            lm = self.lesson_meta[slug]
            self.flat.append({"kind": "lesson", "slug": slug, "title": lm["title"],
                              "url": f"lecons/{slug}/index.html"})
            for sub in self.subpages[slug]:
                self.flat.append({"kind": "page", "slug": slug, "sub": sub["slug"],
                                  "title": sub["title"],
                                  "url": f"lecons/{slug}/{sub['slug']}/index.html"})

    def neighbours(self, url: str) -> tuple[dict | None, dict | None]:
        for i, item in enumerate(self.flat):
            if item["url"] == url:
                return (self.flat[i - 1] if i > 0 else None,
                        self.flat[i + 1] if i + 1 < len(self.flat) else None)
        return None, None

    # -- résolution des jetons de lien ------------------------------------

    def resolve_token(self, token: str, base: str) -> str:
        if token.startswith("#") or token.startswith("mailto:") or "://" in token:
            return token
        frag = ""
        if "#" in token:
            token, frag = token.split("#", 1)
            frag = "#" + frag
        if token == "@self" or token == "":
            return frag or "#"
        if token == "@home":
            return base + "index.html" + frag
        if token == "@annexes":
            return base + "annexes/index.html" + frag
        if token.startswith("@annexe/"):
            return base + f"annexes/{token[8:]}/index.html" + frag
        if token.startswith("@img/"):
            return base + "assets/images/" + token[5:]
        if token.startswith("@lesson/"):
            return base + f"lecons/{token[8:]}/index.html" + frag
        if token.startswith("@page/"):
            slug, _, rel = token[6:].partition("/")
            return base + f"lecons/{slug}/{page_slug(rel)}/index.html" + frag
        if token.startswith("@code/"):
            slug, _, rel = token[6:].partition("/")
            return base + f"lecons/{slug}/index.html#{path_anchor(rel)}"
        if token == "@apps":
            return base + "ateliers/index.html" + frag
        if token.startswith("@app/"):
            return base + f"ateliers/{token[5:]}/index.html" + frag
        if token.startswith("@apppage/"):
            parts = token[9:].split("/")
            if len(parts) == 3:
                cat, proj, page = parts
                return base + f"ateliers/{cat}/{proj}/{page}/index.html" + frag
        if token.startswith("@appcode/"):
            parts = token[9:].split("/", 2)
            if len(parts) == 3:
                cat, proj, rel = parts
                return base + f"ateliers/{cat}/{proj}/index.html#{path_anchor(rel)}"
        if token == "@tags":
            return base + "tags/index.html" + frag
        return token + frag


# ------------------------------------------------------------------ markdown

def first_heading(md: str) -> str | None:
    m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else None


class Renderer:
    """Rend le Markdown en HTML et collecte le sommaire de la page."""

    def __init__(self, site: Site):
        self.site = site
        self.md = (
            MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": False})
            .enable(["table", "strikethrough"])
        )
        self.base = ""
        self.toc: list[dict] = []
        self.headings = True          # False dans les notebooks : pas d'ancres ni de sommaire
        self.link_hook = None         # résolveur alternatif (notebooks)
        self._ids: set[str] = set()
        self._install_rules()

    def _install_rules(self) -> None:
        rules = self.md.renderer.rules

        def fence(tokens, idx, options, env):
            tok = tokens[idx]
            lang = (tok.info or "").strip().split()[0] if tok.info else ""
            return code_block(tok.content, lang)

        def heading_open(tokens, idx, options, env):
            tok = tokens[idx]
            if not self.headings:
                return f"<{tok.tag}>"
            level = int(tok.tag[1])
            text = re.sub(r"<[^>]+>", "", tokens[idx + 1].content).strip()
            hid = slugify(text)
            n = 2
            while hid in self._ids:
                hid, n = f"{slugify(text)}-{n}", n + 1
            self._ids.add(hid)
            tok.attrSet("id", hid)
            if level in (2, 3) and text:
                self.toc.append({"id": hid, "text": text, "level": level})
            return f'<{tok.tag} id="{hid}">'

        def heading_close(tokens, idx, options, env):
            tok = tokens[idx]
            if not self.headings:
                return f"</{tok.tag}>\n"
            hid = tokens[idx - 2].attrGet("id") if idx >= 2 else ""
            anchor = f'<a class="anchor" href="#{hid}" aria-label="Lien vers cette section">#</a>'
            return f"{anchor}</{tok.tag}>\n"

        def link_open(tokens, idx, options, env):
            tok = tokens[idx]
            href = tok.attrGet("href") or ""
            resolved = self.resolve(href)
            tok.attrSet("href", resolved)
            if "://" in resolved:
                tok.attrSet("target", "_blank")
                tok.attrSet("rel", "noopener noreferrer")
            return self.md.renderer.renderToken(tokens, idx, options, env)

        def image(tokens, idx, options, env):
            tok = tokens[idx]
            tok.attrSet("src", self.resolve(tok.attrGet("src") or ""))
            tok.attrSet("loading", "lazy")
            tok.attrSet("decoding", "async")
            alt = self.md.renderer.renderInlineAsText(tok.children or [], options, env)
            tok.attrSet("alt", alt)
            return self.md.renderer.renderToken(tokens, idx, options, env)

        def html_any(tokens, idx, options, env):
            return self._rewrite_html(tokens[idx].content)

        rules["fence"] = fence
        rules["code_block"] = fence
        rules["heading_open"] = heading_open
        rules["heading_close"] = heading_close
        rules["link_open"] = link_open
        rules["image"] = image
        rules["html_block"] = html_any
        rules["html_inline"] = html_any

    def resolve(self, href: str) -> str:
        """Les jetons `@…` viennent de l'ingestion ; le hook sert aux notebooks,
        dont les liens relatifs n'ont jamais été réécrits."""
        if self.link_hook and not href.startswith("@"):
            return self.link_hook(href)
        return self.site.resolve_token(href, self.base)

    def _rewrite_html(self, raw: str) -> str:
        def sub(m: re.Match) -> str:
            return m.group(1) + m.group(2) + self.resolve(m.group(3)) + m.group(2)
        return re.sub(r"""((?:src|href)=)(["'])([^"']+)\2""", sub, raw)

    def render(self, md_text: str, base: str, *, headings: bool = True,
               link_hook=None) -> tuple[str, list[dict]]:
        self.base, self.toc, self._ids = base, [], set()
        self.headings, self.link_hook = headings, link_hook
        body = self.md.render(md_text)
        self.headings, self.link_hook = True, None
        return body, list(self.toc)


def plain_text(md_text: str) -> str:
    """Texte brut d'une page, pour l'index de recherche."""
    t = re.sub(r"```.*?```", " ", md_text, flags=re.DOTALL)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#>*_`|~-]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------ notebooks

def notebook_link_hook(site: "Site", slug: str, nb_rel: str, base: str, anchor: str):
    """Résout les liens relatifs qui vivent dans les cellules d'un notebook.

    Ces liens n'ont jamais transité par l'ingestion : ils pointent vers des fichiers
    voisins du dépôt source. On les rattache au site quand la cible y existe, sinon
    au dépôt d'origine plutôt que de laisser un lien mort.
    """
    import posixpath

    nb_dir = posixpath.dirname(nb_rel)
    raw_base = f"https://raw.githubusercontent.com/microsoft/generative-ai-for-beginners/main"

    def hook(target: str) -> str:
        t = target.strip()
        if not t or t.startswith(("http://", "https://", "mailto:", "data:", "//")):
            return t
        t = TRACKING_RE.sub("", t)
        if t.startswith("#"):
            return f"#{anchor}"     # ancre interne au notebook : on reste sur le fichier
        path_part, _, frag = t.partition("#")
        if not path_part:
            return f"#{anchor}"
        if re.fullmatch(r"[^@\s/]+@[^@\s/]+\.[A-Za-z]{2,}", path_part):
            return "mailto:" + path_part

        owner = slug
        rel = posixpath.normpath(posixpath.join(nb_dir, path_part))
        while rel.startswith("../"):                 # la cible sort de la leçon
            rel = rel[3:]
            head, _, tail = rel.partition("/")
            if head in site.lesson_meta:
                owner, rel = head, tail
                break

        if not rel or rel == ".":
            return base + f"lecons/{owner}/index.html"
        if rel in {c["rel"] for c in site.code_index.get(owner, [])}:
            return base + f"assets/code/{owner}/{rel}"
        if rel == "README.md":
            return base + f"lecons/{owner}/index.html"
        if rel.endswith(".md") and (CONTENT / owner / rel).is_file():
            return base + f"lecons/{owner}/{page_slug(rel)}/index.html"
        stem = Path(rel).stem
        if Path(rel).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
            local = site.image_by_stem.get(stem)
            if local:
                return base + "assets/images/" + local
            return f"{raw_base}/{owner}/{rel}"
        return f"{UPSTREAM}/blob/main/{owner}/{rel}" + (f"#{frag}" if frag else "")

    return hook


def app_notebook_link_hook(site: "Site", owner: str, anchor: str):
    """Liens relatifs dans les notebooks d'ateliers : ils désignent des fichiers voisins
    du dépôt source, qu'on ne republie pas tous — on renvoie donc vers l'original."""
    pid = owner[len("ateliers/"):]
    path = site.apps["projects"][pid]["path"]

    def hook(target: str) -> str:
        t = target.strip()
        if not t or t.startswith(("http://", "https://", "mailto:", "data:", "//")):
            return t
        if t.startswith("#"):
            return f"#{anchor}"
        return f"{APPS_UPSTREAM}/blob/main/{path}/{t.split('#')[0]}"

    return hook


def render_notebook(path: Path, renderer: Renderer, base: str, hook=None) -> str:
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return '<p class="note">Notebook illisible — utilisez le lien de téléchargement.</p>'
    lang = (nb.get("metadata", {}).get("language_info", {}) or {}).get("name", "python")
    out = ['<div class="notebook">']
    for cell in nb.get("cells", []):
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        if cell.get("cell_type") == "markdown":
            body, _ = renderer.render(source, base, headings=False, link_hook=hook)
            out.append(f'<div class="notebook__md">{body}</div>')
        elif cell.get("cell_type") == "code":
            out.append(code_block(source, lang))
            text = notebook_outputs(cell)
            if text:
                out.append(f'<pre class="notebook__out">{esc(text)}</pre>')
    out.append("</div>")
    return "".join(out)


def notebook_outputs(cell: dict, max_lines: int = 30) -> str:
    chunks: list[str] = []
    for o in cell.get("outputs", []):
        if o.get("output_type") == "stream":
            chunks.append("".join(o.get("text", [])))
        elif o.get("output_type") in ("execute_result", "display_data"):
            data = o.get("data", {})
            if "text/plain" in data:
                chunks.append("".join(data["text/plain"]))
        elif o.get("output_type") == "error":
            chunks.append("\n".join(o.get("traceback", []))[:800])
    text = "".join(chunks).strip()
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"… ({len(text.splitlines()) - max_lines} lignes supplémentaires)"]
    return "\n".join(lines)


# ------------------------------------------------------------------ gabarits

def layout(*, site: Site, base: str, title: str, description: str, body: str,
           sidebar: str = "", toc: str = "", body_class: str = "") -> str:
    year = 2026
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🧠</text></svg>">
<link rel="stylesheet" href="{base}assets/style.css">
<link rel="stylesheet" href="{base}assets/highlight.css">
<script>
  (function () {{
    try {{
      var t = localStorage.getItem('genai-theme');
      if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
    }} catch (e) {{}}
  }})();
</script>
</head>
<body class="{body_class}" data-base="{base}">
<a class="skip" href="#contenu">Aller au contenu</a>
<header class="topbar">
  <button class="topbar__menu" type="button" aria-label="Ouvrir le sommaire" aria-expanded="false">☰</button>
  <a class="topbar__brand" href="{base}index.html"><span aria-hidden="true">🧠</span> IA Générative</a>
  <div class="search" role="search">
    <input class="search__input" type="search" placeholder="Rechercher sur tout le site…"
           aria-label="Rechercher sur tout le site" autocomplete="off">
    <div class="search__results" hidden></div>
  </div>
  <button class="topbar__theme" type="button" aria-label="Changer de thème" title="Changer de thème">
    <span class="topbar__theme-light" aria-hidden="true">☀</span><span class="topbar__theme-dark" aria-hidden="true">☾</span>
  </button>
</header>
<div class="shell">
  {sidebar}
  <main id="contenu" class="main">
{body}
  </main>
  {toc}
</div>
<footer class="footer">
  <p>Contenu issu de <a href="{UPSTREAM}" target="_blank" rel="noopener noreferrer">microsoft/generative-ai-for-beginners</a>,
     sous licence MIT — traduction française officielle du dépôt. Ce site en est une réorganisation pédagogique.</p>
  <p class="footer__meta">© {year} Microsoft pour le contenu du cours · mise en forme et navigation : Softscar Learning Content</p>
</footer>
<script src="{base}assets/app.js" defer></script>
</body>
</html>
"""


def sidebar_html(site: Site, base: str, current: str | None, current_sub: str | None = None,
                 current_cat: str | None = None) -> str:
    out = ['<nav class="sidebar" aria-label="Sommaire du cours"><div class="sidebar__inner">']
    out.append(f'<a class="sidebar__home" href="{base}index.html">Accueil</a>')
    for track in site.tracks:
        out.append('<section class="sidebar__track">')
        out.append(
            f'<h2 class="sidebar__track-title">'
            f'<span class="sidebar__icon" aria-hidden="true">{track["icon"]}</span>'
            f'<a href="{base}parcours/{track["id"]}/index.html">{esc(track["title"])}</a></h2>'
        )
        out.append('<ul class="sidebar__list">')
        for slug in track["lessons"]:
            lm = site.lesson_meta[slug]
            active = " is-active" if slug == current else ""
            out.append(
                f'<li class="sidebar__item{active}" data-lesson="{slug}">'
                f'<a href="{base}lecons/{slug}/index.html">'
                f'<span class="sidebar__num">{lm["num"]}</span>'
                f'<span class="sidebar__label">{esc(lm["title"])}</span>'
                f'<span class="sidebar__check" aria-hidden="true"></span></a>'
            )
            subs = site.subpages.get(slug, [])
            if subs and slug == current:
                out.append('<ul class="sidebar__sublist">')
                for sub in subs:
                    a = " is-active" if sub["slug"] == current_sub else ""
                    out.append(
                        f'<li class="sidebar__subitem{a}">'
                        f'<a href="{base}lecons/{slug}/{sub["slug"]}/index.html">{esc(sub["title"])}</a></li>'
                    )
                out.append("</ul>")
            out.append("</li>")
        out.append("</ul></section>")
    if site.cat_order:
        out.append('<section class="sidebar__track sidebar__track--apps">')
        out.append(
            f'<h2 class="sidebar__track-title"><span class="sidebar__icon" aria-hidden="true">🧪</span>'
            f'<a href="{base}ateliers/index.html">Ateliers pratiques</a></h2>'
        )
        out.append('<ul class="sidebar__list">')
        for cat in site.cat_order:
            c = site.category(cat)
            active = " is-active" if cat == current_cat else ""
            out.append(
                f'<li class="sidebar__item sidebar__item--cat{active}">'
                f'<a href="{base}{c["url"]}">'
                f'<span class="sidebar__num" aria-hidden="true">{c["icon"]}</span>'
                f'<span class="sidebar__label">{esc(c["title"])}</span>'
                f'<span class="sidebar__count">{len(c["projects"])}</span></a></li>'
            )
        out.append("</ul></section>")
    if site.prompt_order:
        out.append('<section class="sidebar__track">')
        out.append(
            f'<h2 class="sidebar__track-title"><span class="sidebar__icon" aria-hidden="true">🔍</span>'
            f'<a href="{base}prompts-systeme/index.html">Prompts système</a></h2>'
            f'<ul class="sidebar__list"><li class="sidebar__item sidebar__item--cat">'
            f'<a href="{base}prompts-systeme/index.html">'
            f'<span class="sidebar__num" aria-hidden="true">📄</span>'
            f'<span class="sidebar__label">Les {len(site.prompt_order)} outils</span></a></li></ul>'
        )
        out.append("</section>")
    out.append(
        f'<section class="sidebar__track"><h2 class="sidebar__track-title">'
        f'<span class="sidebar__icon" aria-hidden="true">🗺️</span>'
        f'<a href="{base}sujets/index.html">Par sujet</a></h2>'
        f'<ul class="sidebar__list">'
        + "".join(
            f'<li class="sidebar__item sidebar__item--cat"><a href="{base}sujets/{tid}/index.html">'
            f'<span class="sidebar__num" aria-hidden="true">{t["icon"]}</span>'
            f'<span class="sidebar__label">{esc(t["title"])}</span>'
            f'<span class="sidebar__count">{len(site.items_by_topic(tid))}</span></a></li>'
            for tid, t in sorted(site.topicdef.items(), key=lambda kv: kv[1]["order"])
        )
        + "</ul></section>"
    )
    out.append(
        f'<section class="sidebar__track"><h2 class="sidebar__track-title">'
        f'<span class="sidebar__icon" aria-hidden="true">📎</span>'
        f'<a href="{base}annexes/index.html">Annexes</a></h2>'
        f'<ul class="sidebar__list"><li class="sidebar__item sidebar__item--cat">'
        f'<a href="{base}catalogue/index.html">'
        f'<span class="sidebar__num" aria-hidden="true">🗂️</span>'
        f'<span class="sidebar__label">Catalogue complet</span></a></li></ul>'
        f'<ul class="sidebar__list"><li class="sidebar__item sidebar__item--cat">'
        f'<a href="{base}annexes/alternatives-gratuites/index.html">'
        f'<span class="sidebar__num" aria-hidden="true">🆓</span>'
        f'<span class="sidebar__label">Alternatives gratuites</span></a></li>'
        f'<li class="sidebar__item sidebar__item--cat"><a href="{base}tags/index.html">'
        f'<span class="sidebar__num" aria-hidden="true">🏷️</span>'
        f'<span class="sidebar__label">Légende des tags</span></a></li></ul></section>'
    )
    out.append("</div></nav>")
    return "".join(out)


def tag_chips(site: Site, tags: list[str], base: str = "", *, link: bool = False) -> str:
    """Puces de tags. `link` renvoie vers la légende, pour les en-têtes de page."""
    if not tags:
        return ""
    out = []
    for t in tags:
        v = site.tagdef["values"].get(t)
        if not v:
            continue
        inner = (f'<span class="tag__icon" aria-hidden="true">{v["icon"]}</span>'
                 f'<span class="tag__label">{esc(v["label"])}</span>')
        title = esc(v["desc"])
        if link:
            out.append(f'<li class="tag tag--{v["group"]}">'
                       f'<a href="{base}tags/index.html#{t}" title="{title}">{inner}</a></li>')
        else:
            out.append(f'<li class="tag tag--{v["group"]}" title="{title}">{inner}</li>')
    return f'<ul class="tags">{"".join(out)}</ul>'


def tag_attr(tags: list[str]) -> str:
    return " ".join(tags)


def facet_group(legend: str, facet: str, buttons: str) -> str:
    return (f'<div class="filters__group"><span class="filters__legend">{esc(legend)}</span>'
            f'<div class="filters__row" data-facet="{facet}">{buttons}</div></div>')


def filter_bar(site: Site, base: str, *, target: str, noun: str,
               facets: tuple[str, ...] = ("tags",)) -> str:
    """Barre de filtrage. Chaque groupe est une facette indépendante ; le filtrage client
    combine les facettes en ET, ce qui permet « incontournable » × « RAG » × « atelier »."""
    blocks = []

    if "type" in facets:
        btns = "".join(
            f'<button class="filters__tag tag tag--type" type="button" data-facet-value="{cid}" '
            f'aria-pressed="false" title="{esc(c["plural"])}">'
            f'<span class="tag__icon" aria-hidden="true">{c["icon"]}</span>'
            f'<span class="tag__label">{esc(c["plural"])}</span></button>'
            for cid, c in sorted(COLLECTIONS.items(), key=lambda kv: kv[1]["order"])
        )
        blocks.append(facet_group("Type", "type", btns))

    if "topics" in facets:
        btns = "".join(
            f'<button class="filters__tag tag tag--topic" type="button" data-facet-value="{tid}" '
            f'aria-pressed="false" title="{esc(t["summary"])}">'
            f'<span class="tag__icon" aria-hidden="true">{t["icon"]}</span>'
            f'<span class="tag__label">{esc(t["title"])}</span></button>'
            for tid, t in sorted(site.topicdef.items(), key=lambda kv: kv[1]["order"])
        )
        blocks.append(facet_group("Sujet", "topics", btns))

    if "tags" in facets:
        for gid, g in sorted(site.tagdef["groups"].items(), key=lambda kv: kv[1]["order"]):
            values = [(t, v) for t, v in site.tagdef["values"].items() if v["group"] == gid]
            if not values:
                continue
            btns = "".join(
                f'<button class="filters__tag tag tag--{gid}" type="button" data-facet-value="{t}" '
                f'aria-pressed="false" title="{esc(v["desc"])}">'
                f'<span class="tag__icon" aria-hidden="true">{v["icon"]}</span>'
                f'<span class="tag__label">{esc(v["label"])}</span></button>'
                for t, v in values
            )
            blocks.append(facet_group(g["title"], "tags", btns))

    hint = ("Cumulez les filtres pour cibler ce qui vous intéresse. "
            f'<a href="{base}tags/index.html">Que veulent dire ces tags ?</a>')
    if "topics" in facets:
        hint = ("Combinez type, sujet et tags. "
                f'<a href="{base}sujets/index.html">Voir les sujets</a> · '
                f'<a href="{base}tags/index.html">comprendre les tags</a>')
    return (
        f'<section class="filters" data-filter-target="{target}" data-filter-noun="{noun}">'
        f'<div class="filters__head"><h2 class="filters__title">Filtrer</h2>'
        f'<p class="filters__hint">{hint}</p></div>'
        f'{"".join(blocks)}'
        f'<p class="filters__status" role="status" aria-live="polite"></p>'
        f'<button class="filters__reset" type="button" hidden>Tout afficher</button>'
        f'</section>'
    )


def topic_chips(site: Site, topics: list[str], base: str) -> str:
    if not topics:
        return ""
    out = "".join(
        f'<li class="tag tag--topic"><a href="{base}sujets/{t}/index.html" '
        f'title="{esc(site.topicdef[t]["summary"])}">'
        f'<span class="tag__icon" aria-hidden="true">{site.topicdef[t]["icon"]}</span>'
        f'<span class="tag__label">{esc(site.topicdef[t]["title"])}</span></a></li>'
        for t in topics if t in site.topicdef
    )
    return f'<ul class="tags tags--topics">{out}</ul>'


def item_card(site: Site, item: dict, base: str, *, show_type: bool = False) -> str:
    """Carte d'un contenu, identique quelle que soit sa famille — c'est ce qui permet au
    catalogue et aux pages de sujet de mélanger les trois sans code dédié."""
    c = COLLECTIONS[item["collection"]]
    tags = site.tags_of.get(item["id"], [])
    kind = (f'<span class="lcard__kind"><span aria-hidden="true">{c["icon"]}</span> '
            f'{esc(c["label"])}</span>') if show_type else ""
    context = f'<span class="lcard__ctx">{esc(item["context"])}</span>' if item["context"] else ""
    return (
        f'<article class="lcard" data-item="{item["pkey"]}" data-type="{item["collection"]}" '
        f'data-topics="{" ".join(item.get("topics", []))}" data-tags="{tag_attr(tags)}">'
        f'<a class="lcard__link" href="{base}{item["url"]}">'
        f'{kind}{context}'
        f'<h3 class="lcard__title">{esc(item["title"])}'
        f'<span class="sidebar__check" aria-hidden="true"></span></h3>'
        f'<p class="lcard__summary">{esc(item["summary"])}</p></a>'
        f'{tag_chips(site, tags)}'
        f'{topic_chips(site, item.get("topics", []), base)}'
        f'</article>'
    )


def related_block(site: Site, iid: str, base: str) -> str:
    related = site.related_items(iid)
    if not related:
        return ""
    items = "".join(
        f'<li class="related__item"><a href="{base}{r["url"]}">'
        f'<span class="related__kind" aria-hidden="true">{COLLECTIONS[r["collection"]]["icon"]}</span>'
        f'<span class="related__title">{esc(r["title"])}</span>'
        f'<span class="related__summary">{esc(r["summary"])}</span></a></li>'
        for r in related
    )
    return ('<section class="related"><h2 id="sur-le-meme-sujet">Sur le même sujet'
            '<a class="anchor" href="#sur-le-meme-sujet" aria-label="Lien vers cette section">#</a></h2>'
            '<p class="related__intro">Les mêmes notions, vues sous un autre angle :</p>'
            f'<ul class="related__list">{items}</ul></section>')


def alternatives_box(site: Site, owner: str, base: str) -> str:
    """Encadré listant les services exigés par la page et leurs substituts gratuits."""
    sids = site.services_of.get(owner, [])
    if not sids:
        return ""
    defs = site.services["services"]
    billed = [s for s in sids if defs[s]["cost"] != "gratuit" and defs[s]["free"]]
    free_only = [s for s in sids if defs[s]["cost"] == "gratuit"]
    if not billed:
        if not free_only:
            return ""
        names = ", ".join(esc(defs[s]["name"]) for s in sorted(free_only))
        return (f'<aside class="alts alts--free"><p class="alts__lead">'
                f'<span aria-hidden="true">🆓</span> Rien à payer ici : {names}. '
                f'<a href="{base}annexes/alternatives-gratuites/index.html">'
                f'Voir toutes les alternatives gratuites</a>.</p></aside>')

    rows = []
    for sid in sorted(billed, key=lambda s: defs[s]["name"]):
        s = defs[sid]
        cost = site.services["cost_labels"].get(s["cost"], s["cost"])
        subs = "".join(
            f'<li><a href="{esc(f["url"])}" target="_blank" rel="noopener noreferrer">'
            f'{esc(f["name"])}</a> — {esc(f["note"])}</li>' for f in s["free"]
        )
        rows.append(
            f'<div class="alts__item"><p class="alts__service">'
            f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["name"])}</a>'
            f'<span class="alts__cost">{esc(cost)}</span></p>'
            f'<p class="alts__note">{esc(s.get("note", ""))}</p>'
            f'<ul class="alts__list">{subs}</ul></div>'
        )
    return (
        '<aside class="alts">'
        '<p class="alts__lead"><span aria-hidden="true">💳</span> '
        'Cette page s\'appuie sur des services facturés. Voici par quoi les remplacer '
        'sans dépenser :</p>'
        f'{"".join(rows)}'
        f'<p class="alts__more"><a href="{base}annexes/alternatives-gratuites/index.html">'
        'Table complète des alternatives gratuites</a></p></aside>'
    )


def toc_html(toc: list[dict]) -> str:
    if len(toc) < 2:
        return ""
    items = "".join(
        f'<li class="toc__item toc__item--h{t["level"]}"><a href="#{t["id"]}">{esc(t["text"])}</a></li>'
        for t in toc
    )
    return ('<aside class="toc" aria-label="Sommaire de la page"><div class="toc__inner">'
            f'<p class="toc__title">Sur cette page</p><ul class="toc__list">{items}</ul></div></aside>')


def code_section(site: Site, owner: str, renderer: Renderer, base: str, *,
                 title: str = "Code de la leçon", intro: str | None = None,
                 skipped: list[dict] | None = None, upstream_tree: str | None = None) -> str:
    entries = site.code_index.get(owner, [])
    if skipped is None:
        skipped = site.ingest["lessons"].get(owner, {}).get("skipped", [])
    if not entries:
        return ""
    groups = site.code_groups(owner)
    intro = intro or ("Tous les fichiers d'exemple de cette leçon, copiés depuis le dépôt "
                      "d'origine. Chaque fichier est lisible ici et téléchargeable.")
    out = ['<section class="codepanel" id="code">',
           f'<h2 id="code-de-la-lecon">{esc(title)}'
           '<a class="anchor" href="#code-de-la-lecon" aria-label="Lien vers cette section">#</a></h2>',
           f'<p class="codepanel__intro">{esc(intro)}</p>']
    if len(groups) > 1:
        out.append('<div class="tabs" role="tablist">')
        for i, (g, _files) in enumerate(groups):
            sel = "true" if i == 0 else "false"
            out.append(
                f'<button class="tabs__btn" role="tab" aria-selected="{sel}" '
                f'data-tab="{slugify(g or "fichiers")}">{esc(GROUP_LABELS.get(g, g or "Fichiers"))}</button>'
            )
        out.append("</div>")
    for i, (g, files) in enumerate(groups):
        hidden = "" if i == 0 or len(groups) == 1 else " hidden"
        out.append(f'<div class="tabs__panel" data-tab="{slugify(g or "fichiers")}"{hidden}>')
        for f in files:
            out.append(render_code_file(f, owner, renderer, base))
        out.append("</div>")
    if skipped:
        items = "".join(
            f'<li><code>{esc(s["path"])}</code> — {esc(s["reason"])} ({human_size(s["size"])})</li>'
            for s in skipped
        )
        tree = upstream_tree or f"{UPSTREAM}/tree/main/{owner}"
        out.append(
            '<details class="codepanel__skipped"><summary>Fichiers non embarqués '
            f'({len(skipped)})</summary><ul>{items}</ul>'
            f'<p>Ils restent disponibles dans le <a href="{tree}" '
            'target="_blank" rel="noopener noreferrer">dépôt d\'origine</a>.</p></details>'
        )
    out.append("</section>")
    return "".join(out)


def render_code_file(entry: dict, owner: str, renderer: Renderer, base: str) -> str:
    rel, path = entry["rel"], entry["path"]
    dl = f"{base}assets/code/{owner}/{rel}"
    head = (
        f'<summary class="codefile__head"><span class="codefile__name">{esc(rel)}</span>'
        f'<span class="codefile__size">{human_size(entry["size"])}</span></summary>'
    )
    actions = (f'<p class="codefile__actions"><a href="{dl}" download>Télécharger ce fichier</a></p>')

    if NO_RENDER.search(rel) or entry["size"] > MAX_RENDER_BYTES:
        body = ('<p class="note">Fichier généré ou volumineux : il n\'est pas affiché ici.</p>' + actions)
    elif rel.endswith(".ipynb"):
        if owner.startswith("ateliers/"):
            hook = app_notebook_link_hook(renderer.site, owner, entry["anchor"])
        else:
            hook = notebook_link_hook(renderer.site, owner, rel, base, entry["anchor"])
        body = render_notebook(path, renderer, base, hook) + actions
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            body = '<p class="note">Fichier binaire.</p>' + actions
        else:
            ext = "." + rel.rsplit(".", 1)[-1] if "." in rel else ""
            lang = LANG_BY_EXT.get(ext, LANG_BY_EXT.get(Path(rel).name, "text"))
            body = code_block(text, lang) + actions
    return f'<details class="codefile" id="{entry["anchor"]}">{head}<div class="codefile__body">{body}</div></details>'


TOOLS_NOTE = (
    '<div class="toolsnote"><p><strong>Ce fichier n\'est pas un prompt : c\'est un catalogue '
    'd\'outils.</strong> Il déclare les {n} actions que le modèle peut demander au produit '
    'd\'exécuter — lire un fichier, lancer une commande, chercher sur le web. Pour chacune : un '
    'nom, une description, et des paramètres typés.</p>'
    '<p>Le point à retenir : <strong>c\'est la description qui décide du bon appel</strong>, pas '
    'le prompt principal. Un outil mal décrit sera appelé au mauvais moment, quelles que soient '
    'les consignes par ailleurs. '
    '<a href="{base}prompts-systeme/guide/index.html#outils">Comment lire une définition d\'outil</a> '
    '· <a href="{base}lecons/11-integrating-with-function-calling/index.html">Leçon 11</a></p></div>'
)
# Ce qu'une section devient une fois envoyée. Déclaré dans `_prompt_sections.json`, jamais
# deviné : une section hors glossaire n'affiche pas de nature.
NATURES = {
    "regle": ("règle permanente", "Vaut tout le temps, sans ordre d'application."),
    "procedure": ("procédure", "Des étapes à suivre dans l'ordre, mais seulement quand le cas "
                               "décrit se présente."),
    "exemples": ("exemples", "Des démonstrations, pas des consignes."),
    "contexte": ("contexte injecté", "Rempli à l'exécution : le contenu change à chaque "
                                     "session, il n'est pas écrit par l'éditeur."),
    "outils": ("catalogue d'outils", "Déclare ce que le modèle peut appeler."),
}
NUM_RULE = re.compile(r"^\s{0,3}\d{1,2}[.)]\s+\S")


def numbered_rules(body: str) -> int:
    """Nombre de points numérotés en tête de ligne. Un constat, pas une interprétation."""
    return sum(1 for line in body.splitlines() if NUM_RULE.match(line))


def nature_badge(gloss: dict | None, body: str) -> str:
    """Pastille disant ce que la section devient une fois envoyée.

    Deux sources, dans cet ordre : la nature déclarée au glossaire, sinon un simple
    dénombrement des points numérotés. Une section ni répertoriée ni numérotée n'affiche
    rien — une pastille inventée vaudrait moins que pas de pastille du tout.
    """
    nat = (gloss or {}).get("nature")
    if nat in NATURES:
        label, why = NATURES[nat]
        return f'<span class="nat nat--{nat}" title="{esc(why)}">{label}</span>'
    n = numbered_rules(body)
    if n >= 3:
        return (f'<span class="nat nat--compte" title="Constat mesuré sur le texte, sans '
                f'interprétation.">{n} points numérotés</span>')
    return ""


TAG_OPEN = re.compile(r"^<([a-z][a-z0-9_]*)>\s*$")
TAG_CLOSE = re.compile(r"^</([a-z][a-z0-9_]*)>\s*$")
MD_HEAD = re.compile(r"^(#{1,3})\s+(.{2,80})$")


def normalize_section(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def split_prompt(text: str) -> tuple[str, list[dict]]:
    """Découpe un prompt en sections de premier niveau.

    Trois régimes, dans l'ordre : balises racine (ouvertes et fermées en colonne 0, sans
    imbrication — sinon on découperait sur les `<example>` internes), titres Markdown, puis
    rien. Le troisième cas n'est pas un échec : un cinquième des prompts n'a aucune
    structure, et le prétendre serait mentir sur ce qu'on montre.

    Renvoie (mode, sections) où chaque section est {name, body, lines}.
    """
    lines = text.splitlines()

    sections, depth, cur, start = [], 0, None, 0
    for i, line in enumerate(lines):
        mo, mc = TAG_OPEN.match(line), TAG_CLOSE.match(line)
        if mo:
            if depth == 0:
                if cur is None and lines[start:i] and any(l.strip() for l in lines[start:i]):
                    sections.append({"name": "", "body": "\n".join(lines[start:i])})
                cur, start = mo.group(1), i
            depth += 1
        elif mc:
            depth -= 1
            if depth == 0 and cur == mc.group(1):
                sections.append({"name": cur, "body": "\n".join(lines[start:i + 1])})
                cur, start = None, i + 1
            depth = max(depth, 0)
    if sections:
        rest = "\n".join(lines[start:])
        if rest.strip():
            sections.append({"name": "", "body": rest})
        mode = "balises"
    else:
        heads = [(i, MD_HEAD.match(l)) for i, l in enumerate(lines)]
        heads = [(i, m) for i, m in heads if m]
        if len(heads) >= 3:
            if heads[0][0] > 0 and any(l.strip() for l in lines[: heads[0][0]]):
                sections.append({"name": "", "body": "\n".join(lines[: heads[0][0]])})
            for n, (i, m) in enumerate(heads):
                end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
                sections.append({"name": m.group(2).strip(),
                                 "body": "\n".join(lines[i:end])})
            mode = "titres"
        else:
            sections = [{"name": "", "body": text}]
            mode = "brut"

    # Plusieurs prompts alignent sept ou huit `<example>` de suite à la racine. Les lister
    # un par un noie le plan sous du bruit : on regroupe les sections consécutives de même
    # nom en une seule entrée, en gardant leur nombre.
    grouped: list[dict] = []
    for sec in sections:
        if not sec["body"].strip():
            continue
        if grouped and grouped[-1]["name"] == sec["name"] and sec["name"]:
            grouped[-1]["body"] += "\n" + sec["body"]
            grouped[-1]["count"] += 1
        else:
            grouped.append({**sec, "count": 1})
    # Étiquette et identifiant, calculés une fois pour toutes : le plan et le texte doivent
    # nommer et ancrer chaque section de la même façon, sinon les liens du plan tombent à côté.
    used: dict[str, int] = {}
    seen_free = False
    for sec in grouped:
        sec["lines"] = sec["body"].count("\n") + 1
        label = sec["name"]
        if not label:
            # Un bloc sans balise commence parfois par son propre titre Markdown : le lecteur
            # a alors un nom sous les yeux, autant s'en servir plutôt que d'écrire « texte ».
            head = next((l for l in sec["body"].splitlines() if l.strip()), "")
            mo = MD_HEAD.match(head)
            if mo:
                label = mo.group(2).strip()
            else:
                label = "préambule" if not seen_free else "texte hors section"
                seen_free = True
        sec["label"] = label
        key = slugify(label) or "section"
        used[key] = used.get(key, 0) + 1
        sec["key"] = key if used[key] == 1 else f"{key}-{used[key]}"
    return mode, grouped


def tool_definitions_html(tools: list[dict]) -> str:
    """Rend un catalogue d'outils en liste lisible plutôt qu'en JSON brut : c'est la
    description des outils, pas leur sérialisation, qui a une valeur pédagogique."""
    out = ['<div class="tooldefs">']
    for t in tools:
        params = "".join(
            f'<li><code>{esc(p["name"])}</code>'
            + (f' <span class="tooldefs__type">{esc(p["type"])}</span>' if p["type"] else "")
            + (' <span class="tooldefs__req">requis</span>' if p["required"] else "")
            + (f' — {esc(p["description"][:300])}' if p["description"] else "")
            + "</li>"
            for p in t["params"]
        )
        desc = esc(t["description"][:1200]) + ("…" if len(t["description"]) > 1200 else "")
        out.append(
            f'<details class="tooldef"><summary class="tooldef__head">'
            f'<code class="tooldef__name">{esc(t["name"])}</code>'
            f'<span class="tooldef__count">{len(t["params"])} paramètre(s)</span></summary>'
            f'<div class="tooldef__body"><p class="tooldef__desc">{desc}</p>'
            + (f'<ul class="tooldef__params">{params}</ul>' if params else "")
            + "</div></details>"
        )
    out.append("</div>")
    return "".join(out)


def prevnext_html(site: Site, url: str, base: str) -> str:
    prev, nxt = site.neighbours(url)
    if not prev and not nxt:
        return ""
    left = (f'<a class="prevnext__link prevnext__prev" href="{base}{prev["url"]}">'
            f'<span class="prevnext__dir">← Précédent</span>'
            f'<span class="prevnext__title">{esc(prev["title"])}</span></a>') if prev else "<span></span>"
    right = (f'<a class="prevnext__link prevnext__next" href="{base}{nxt["url"]}">'
             f'<span class="prevnext__dir">Suivant →</span>'
             f'<span class="prevnext__title">{esc(nxt["title"])}</span></a>') if nxt else "<span></span>"
    return f'<nav class="prevnext" aria-label="Navigation entre les leçons">{left}{right}</nav>'


# ---------------------------------------------------------------- génération

class Builder:
    def __init__(self, site: Site):
        self.site = site
        self.renderer = Renderer(site)

    def write(self, rel: str, content: str) -> None:
        path = DOCS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def index_search(self, *, url: str, title: str, kind: str, context: str,
                     summary: str, md_text: str, toc: list[dict],
                     ctype: str = "") -> None:
        self.site.search.append({
            "u": url, "t": title, "k": kind, "c": context, "s": summary, "y": ctype,
            "h": [t["text"] for t in toc][:25],
            "b": plain_text(md_text)[:SEARCH_BODY_CHARS],
        })

    # -- assets -----------------------------------------------------------

    def build_assets(self) -> None:
        (DOCS / "assets").mkdir(parents=True, exist_ok=True)
        (DOCS / ".nojekyll").write_text("", encoding="utf-8")
        for name in ("style.css", "app.js"):
            shutil.copy2(ASSETS_SRC / name, DOCS / "assets" / name)

        light = HtmlFormatter(style="stata-light").get_style_defs(".highlight")
        dark_theme = HtmlFormatter(style="one-dark")
        dark_auto = dark_theme.get_style_defs('html:not([data-theme="light"]) .highlight')
        dark_forced = dark_theme.get_style_defs('html[data-theme="dark"] .highlight')
        (DOCS / "assets" / "highlight.css").write_text(
            "/* Coloration syntaxique — généré par tools/build.py (Pygments) */\n"
            f"{light}\n"
            f"@media (prefers-color-scheme: dark) {{\n{dark_auto}\n}}\n"
            f"{dark_forced}\n",
            encoding="utf-8",
        )

    # -- pages ------------------------------------------------------------

    def build_home(self) -> None:
        s, meta = self.site, self.site.meta["site"]
        total = len(s.order)
        cards = []
        for track in s.tracks:
            items = "".join(
                f'<li class="tcard__lesson" data-lesson="{slug}" '
                f'data-tags="{tag_attr(s.tags_of.get(slug, []))}">'
                f'<a href="lecons/{slug}/index.html">'
                f'<span class="tcard__num">{s.lesson_meta[slug]["num"]}</span>'
                f'<span class="tcard__label">{esc(s.lesson_meta[slug]["title"])}</span>'
                f'<span class="sidebar__check" aria-hidden="true"></span></a>'
                f'{tag_chips(s, s.tags_of.get(slug, []))}</li>'
                for slug in track["lessons"]
            )
            mins = sum(s.lesson_meta[x]["minutes"] for x in track["lessons"])
            cards.append(
                f'<article class="tcard" data-track="{track["id"]}">'
                f'<a class="tcard__head" href="parcours/{track["id"]}/index.html">'
                f'<span class="tcard__icon" aria-hidden="true">{track["icon"]}</span>'
                f'<span class="tcard__step">Parcours {track["num"]}</span>'
                f'<h3 class="tcard__title">{esc(track["title"])}</h3></a>'
                f'<p class="tcard__summary">{esc(track["summary"])}</p>'
                f'<ul class="tcard__lessons">{items}</ul>'
                f'<p class="tcard__meta">{len(track["lessons"])} leçon(s) · environ {mins} min '
                f'<span class="tcard__progress" data-track-progress="{track["id"]}"></span></p>'
                "</article>"
            )
        app_cats = "".join(
            f'<a class="chipcat" href="{s.category(c)["url"]}">'
            f'<span aria-hidden="true">{s.category(c)["icon"]}</span> {esc(s.category(c)["title"])}'
            f'<span class="chipcat__count">{len(s.category(c)["projects"])}</span></a>'
            for c in s.cat_order
        )
        n_rag = len(s.apps["categories"].get("rag-tutorials", {}).get("projects", []))
        doors = "".join(
            f'<a class="door door--{cid}" href="{c["url"]}">'
            f'<span class="door__icon" aria-hidden="true">{c["icon"]}</span>'
            f'<span class="door__verb">{esc(c["verb"])}</span>'
            f'<span class="door__what">{esc(label)}</span>'
            f'<span class="door__why">{esc(why)}</span></a>'
            for cid, c, label, why in [
                ("cours", COLLECTIONS["cours"], f"{total} leçons en 7 parcours",
                 "Les concepts, dans l'ordre. Commencez ici si vous débutez."),
                ("ateliers", COLLECTIONS["ateliers"], f"{len(s.app_order)} applications complètes",
                 "Du code qui tourne, à lire et à détourner."),
                ("prompts", COLLECTIONS["prompts"], f"{len(s.prompt_order)} outils décortiqués",
                 "Les consignes internes de produits réels — du prompt engineering grandeur nature."),
            ]
        )
        topic_chips_home = "".join(
            f'<a class="chipcat" href="sujets/{tid}/index.html">'
            f'<span aria-hidden="true">{t["icon"]}</span> {esc(t["title"])}'
            f'<span class="chipcat__count">{len(s.items_by_topic(tid))}</span></a>'
            for tid, t in sorted(s.topicdef.items(), key=lambda kv: kv[1]["order"])
        )
        annexes = "".join(
            f'<li><a href="annexes/{k}/index.html">{esc(v["title"])}</a> — {esc(v["summary"])}</li>'
            for k, v in s.annexe_meta["pages"].items()
        ) + (
            '<li><a href="annexes/alternatives-gratuites/index.html">Alternatives gratuites aux '
            'outils payants</a> — par quoi remplacer chaque service facturé du cours.</li>'
            '<li><a href="tags/index.html">Légende des tags</a> — ce que signifient '
            'intérêt, difficulté, coût et nature.</li>'
        )
        body = f"""
<div class="hero">
  <p class="hero__eyebrow">{total} leçons · {len(s.app_order)} ateliers · {len(s.prompt_order)} prompts système · en français</p>
  <h1 class="hero__title">{esc(meta["title"])}</h1>
  <p class="hero__tagline">{esc(meta["tagline"])}</p>
  <p class="hero__intro">{meta["intro"]}</p>
  <div class="doors">{doors}</div>
  <div class="progress" data-global-progress>
    <div class="progress__bar"><span class="progress__fill"></span></div>
    <p class="progress__label">Progression : <strong class="progress__text">0 / {total}</strong> leçons terminées
      <button class="progress__reset" type="button">réinitialiser</button></p>
  </div>
</div>

<section class="section">
  <h2 class="section__title">Les {len(s.tracks)} parcours</h2>
  <p class="section__intro">Suivez-les dans l'ordre : chaque parcours s'appuie sur le précédent.
     Vous pouvez aussi piocher directement la leçon qui vous intéresse — les tags indiquent
     où le temps investi rapporte le plus.</p>
  {filter_bar(s, "", target=".tcard__lesson", noun="leçon")}
  <div class="tcards">{"".join(cards)}</div>
</section>

<section class="section">
  <h2 class="section__title">Par sujet</h2>
  <p class="section__intro">Le cours, les ateliers et les prompts système parlent souvent des
     mêmes choses. Chaque sujet les rassemble : la théorie, la mise en pratique, et ce qu'en
     fait l'industrie.</p>
  <div class="chipcats">{topic_chips_home}</div>
  <p><a class="btn" href="sujets/index.html">Voir les {len(s.topicdef)} sujets</a>
     <a class="btn" href="catalogue/index.html">Catalogue complet ({len(s.items)} contenus)</a></p>
</section>

<section class="section">
  <h2 class="section__title">{len(s.app_order)} ateliers pratiques</h2>
  <p class="section__intro">Le cours explique ; ces projets font construire. Applications
     complètes issues du dépôt <em>awesome-llm-apps</em>, code compris — dont
     {n_rag} implémentations du RAG.</p>
  <div class="chipcats">{app_cats}</div>
  <p><a class="btn btn--primary" href="ateliers/index.html">Parcourir les ateliers</a>
     <a class="btn" href="annexes/alternatives-gratuites/index.html">Alternatives gratuites aux outils payants</a></p>
</section>

<section class="section">
  <h2 class="section__title">Comment utiliser ce site</h2>
  <div class="howto">
    <div class="howto__item"><h3>Lisez la leçon</h3><p>Chaque page reprend l'intégralité du cours
      d'origine, illustrations comprises, avec un sommaire pour naviguer dans les sections.</p></div>
    <div class="howto__item"><h3>Ouvrez le code</h3><p>Les exemples Python, TypeScript, JavaScript et .NET
      sont affichés en bas de chaque leçon, avec les notebooks rendus cellule par cellule.</p></div>
    <div class="howto__item"><h3>Suivez votre avancée</h3><p>Cochez une leçon terminée : la progression
      est conservée dans votre navigateur, aucune inscription n'est nécessaire.</p></div>
    <div class="howto__item"><h3>Cherchez</h3><p>La recherche en haut de page couvre le texte de toutes
      les leçons — utile pour retrouver une notion précise.</p></div>
  </div>
</section>

<section class="section">
  <h2 class="section__title">Annexes</h2>
  <ul class="linklist">{annexes}</ul>
</section>
"""
        self.write("index.html", layout(
            site=s, base="", title=f'{meta["title"]} — apprendre l\'IA générative en français',
            description=meta["tagline"], body=body, body_class="page-home",
        ))
        self.index_search(url="index.html", title=meta["title"], kind="Accueil",
                          context="", summary=meta["tagline"], md_text=meta["tagline"], toc=[])

    def build_track(self, track: dict) -> None:
        s, base = self.site, "../../"
        cards = []
        for slug in track["lessons"]:
            lm = s.lesson_meta[slug]
            subs = s.subpages.get(slug, [])
            extra = ("<ul class='lcard__subs'>" + "".join(
                f'<li><a href="{base}lecons/{slug}/{x["slug"]}/index.html">{esc(x["title"])}</a></li>'
                for x in subs) + "</ul>") if subs else ""
            ncode = len(s.code_index.get(slug, []))
            cards.append(
                f'<article class="lcard" data-lesson="{slug}">'
                f'<a class="lcard__link" href="{base}lecons/{slug}/index.html">'
                f'<span class="lcard__num">{lm["num"]}</span>'
                f'<h3 class="lcard__title">{esc(lm["title"])}<span class="sidebar__check" aria-hidden="true"></span></h3>'
                f'<p class="lcard__summary">{esc(lm["summary"])}</p></a>'
                f'<p class="lcard__meta">≈ {lm["minutes"]} min'
                + (f' · {ncode} fichier(s) de code' if ncode else "") + "</p>"
                + tag_chips(s, s.tags_of.get(slug, [])) + extra + "</article>"
            )
        idx = s.tracks.index(track)
        prev = s.tracks[idx - 1] if idx > 0 else None
        nxt = s.tracks[idx + 1] if idx + 1 < len(s.tracks) else None
        nav = ""
        if prev or nxt:
            l = (f'<a class="prevnext__link prevnext__prev" href="{base}parcours/{prev["id"]}/index.html">'
                 f'<span class="prevnext__dir">← Parcours précédent</span>'
                 f'<span class="prevnext__title">{esc(prev["title"])}</span></a>') if prev else "<span></span>"
            r = (f'<a class="prevnext__link prevnext__next" href="{base}parcours/{nxt["id"]}/index.html">'
                 f'<span class="prevnext__dir">Parcours suivant →</span>'
                 f'<span class="prevnext__title">{esc(nxt["title"])}</span></a>') if nxt else "<span></span>"
            nav = f'<nav class="prevnext" aria-label="Navigation entre les parcours">{l}{r}</nav>'
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <span>Parcours {track["num"]}</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">{track["icon"]}</span> Parcours {track["num"]}</p>
  <h1 class="pagehead__title">{esc(track["title"])}</h1>
  <p class="pagehead__summary">{esc(track["summary"])}</p>
</header>
{filter_bar(s, base, target=".lcards > .lcard", noun="leçon")}
<div class="lcards">{"".join(cards)}</div>
{nav}
"""
        self.write(f'parcours/{track["id"]}/index.html', layout(
            site=s, base=base, title=f'{track["title"]} — IA Générative',
            description=track["summary"], body=body,
            sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url=f'parcours/{track["id"]}/index.html', title=track["title"],
                          kind="Parcours", context=f'Parcours {track["num"]}',
                          summary=track["summary"], md_text=track["summary"], toc=[])

    def build_lesson(self, slug: str) -> None:
        s, base = self.site, "../../"
        lm, track = s.lesson_meta[slug], s.track_of[slug]
        md_text = (CONTENT / slug / "README.md").read_text(encoding="utf-8")
        body_html, toc = self.renderer.render(md_text, base)
        if not re.search(r"<h1[ >]", body_html):
            body_html = f'<h1 id="titre">{esc(lm["title"])}</h1>' + body_html

        subs = s.subpages.get(slug, [])
        subs_html = ""
        if subs:
            items = "".join(
                f'<li><a href="{base}lecons/{slug}/{x["slug"]}/index.html">{esc(x["title"])}</a></li>'
                for x in subs)
            subs_html = ('<section class="subpages"><h2 id="pages-de-la-lecon">Pages de cette leçon'
                         '<a class="anchor" href="#pages-de-la-lecon" aria-label="Lien vers cette section">#</a></h2>'
                         f'<ul class="linklist">{items}</ul></section>')

        code = code_section(s, slug, self.renderer, base)
        if code:
            toc = toc + [{"id": "code-de-la-lecon", "text": "Code de la leçon", "level": 2}]

        cats = s.categories_for_lesson(slug)
        practice = ""
        if cats:
            blocks = "".join(
                f'<li><a href="{base}{c["url"]}">'
                f'<span aria-hidden="true">{c["icon"]}</span> {esc(c["title"])}</a>'
                f'<span class="practice__count">{len(c["projects"])} atelier(s)</span>'
                f'<span class="practice__summary">{esc(c["summary"])}</span></li>'
                for c in cats)
            practice = (
                '<section class="practice"><h2 id="mettez-le-en-pratique">Mettez-le en pratique'
                '<a class="anchor" href="#mettez-le-en-pratique" aria-label="Lien vers cette section">#</a></h2>'
                '<p class="practice__intro">Des applications complètes qui mettent en œuvre ce que '
                'cette leçon explique :</p>'
                f'<ul class="practice__list">{blocks}</ul></section>')

        url = f"lecons/{slug}/index.html"
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}parcours/{track["id"]}/index.html">{esc(track["title"])}</a> <span aria-hidden="true">›</span>
  <span>Leçon {lm["num"]}</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow">Leçon {lm["num"]} · {esc(track["title"])} · ≈ {lm["minutes"]} min</p>
  <p class="pagehead__summary">{esc(lm["summary"])}</p>
  {tag_chips(s, s.tags_of.get(slug, []), base, link=True)}
  {topic_chips(s, s.topics_of.get(slug, []), base)}
</header>
{alternatives_box(s, slug, base)}
<article class="prose">
{body_html}
</article>
{subs_html}
{code}
{practice}
{related_block(s, slug, base)}
<section class="done" data-lesson-toggle="{slug}">
  <label class="done__label">
    <input class="done__box" type="checkbox">
    <span>J'ai terminé la leçon {lm["num"]} — {esc(lm["title"])}</span>
  </label>
</section>
{prevnext_html(s, url, base)}
<p class="sourcelink">Version d'origine :
  <a href="{UPSTREAM_FR}/{slug}/README.md" target="_blank" rel="noopener noreferrer">
    translations/fr/{slug}/README.md</a> ·
  <a href="{UPSTREAM}/tree/main/{slug}" target="_blank" rel="noopener noreferrer">version anglaise</a>
</p>
"""
        self.write(url, layout(
            site=s, base=base, title=f'{lm["num"]} · {lm["title"]} — IA Générative',
            description=lm["summary"], body=body,
            sidebar=sidebar_html(s, base, slug), toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(url=url, title=f'{lm["num"]} · {lm["title"]}', kind="Leçon",
                          context=track["title"], summary=lm["summary"], md_text=md_text, toc=toc)

    def build_subpage(self, slug: str, sub: dict) -> None:
        s, base = self.site, "../../../"
        lm, track = s.lesson_meta[slug], s.track_of[slug]
        md_text = (CONTENT / slug / sub["rel"]).read_text(encoding="utf-8")
        body_html, toc = self.renderer.render(md_text, base)
        if not re.search(r"<h1[ >]", body_html):
            body_html = f'<h1 id="titre">{esc(sub["title"])}</h1>' + body_html
        url = f'lecons/{slug}/{sub["slug"]}/index.html'
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}parcours/{track["id"]}/index.html">{esc(track["title"])}</a> <span aria-hidden="true">›</span>
  <a href="{base}lecons/{slug}/index.html">Leçon {lm["num"]}</a> <span aria-hidden="true">›</span>
  <span>{esc(sub["title"])}</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow">Page annexe de la leçon {lm["num"]} — {esc(lm["title"])}</p>
</header>
<article class="prose">
{body_html}
</article>
{prevnext_html(s, url, base)}
<p class="sourcelink">Version d'origine :
  <a href="{UPSTREAM_FR}/{slug}/{sub["rel"]}" target="_blank" rel="noopener noreferrer">
    translations/fr/{slug}/{sub["rel"]}</a></p>
"""
        self.write(url, layout(
            site=s, base=base, title=f'{sub["title"]} — leçon {lm["num"]}',
            description=f'{sub["title"]} — page annexe de la leçon {lm["num"]}, {lm["title"]}.',
            body=body, sidebar=sidebar_html(s, base, slug, sub["slug"]),
            toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(url=url, title=sub["title"], kind="Page",
                          context=f'Leçon {lm["num"]} — {lm["title"]}',
                          summary="", md_text=md_text, toc=toc)

    def build_annexes(self) -> None:
        s = self.site
        pages = s.annexe_meta["pages"]
        base = "../"
        items = "".join(
            f'<li><a href="{base}annexes/{k}/index.html">{esc(v["title"])}</a> — {esc(v["summary"])}</li>'
            for k, v in pages.items() if (CONTENT / "_annexes" / f"{k}.md").is_file()
        )
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Annexes</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">📎</span> Annexes</p>
  <h1 class="pagehead__title">{esc(s.annexe_meta["title"])}</h1>
  <p class="pagehead__summary">{esc(s.annexe_meta["summary"])}</p>
</header>
<ul class="linklist linklist--cards">{items}</ul>
"""
        self.write("annexes/index.html", layout(
            site=s, base=base, title="Annexes — IA Générative",
            description=s.annexe_meta["summary"], body=body,
            sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="annexes/index.html", title="Annexes", kind="Annexe", context="",
                          summary=s.annexe_meta["summary"], md_text=s.annexe_meta["summary"], toc=[])

        for key, info in pages.items():
            src = CONTENT / "_annexes" / f"{key}.md"
            if not src.is_file():
                continue
            b = "../../"
            md_text = src.read_text(encoding="utf-8")
            body_html, toc = self.renderer.render(md_text, b)
            if not re.search(r"<h1[ >]", body_html):
                body_html = f'<h1 id="titre">{esc(info["title"])}</h1>' + body_html
            page = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{b}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{b}annexes/index.html">Annexes</a> <span aria-hidden="true">›</span>
  <span>{esc(info["title"])}</span>
</nav>
<header class="pagehead"><p class="pagehead__eyebrow">Annexe</p>
<p class="pagehead__summary">{esc(info["summary"])}</p></header>
<article class="prose">
{body_html}
</article>
<p class="sourcelink">Version d'origine :
  <a href="{UPSTREAM_FR}/{info["source"]}" target="_blank" rel="noopener noreferrer">
    translations/fr/{info["source"]}</a></p>
"""
            self.write(f"annexes/{key}/index.html", layout(
                site=s, base=b, title=f'{info["title"]} — IA Générative',
                description=info["summary"], body=page,
                sidebar=sidebar_html(s, b, None), toc=toc_html(toc), body_class="page-lesson",
            ))
            self.index_search(url=f"annexes/{key}/index.html", title=info["title"], kind="Annexe",
                              context="Annexes", summary=info["summary"], md_text=md_text, toc=toc)

    # -- ateliers ---------------------------------------------------------

    def app_card(self, pid: str, base: str) -> str:
        return item_card(self.site, self.site.items[f"ateliers/{pid}"], base)

    def build_apps_index(self) -> None:
        s, base = self.site, "../"
        sec = s.apps_meta.get("section", {})
        cards = "".join(self.app_card(pid, base) for pid in s.app_order)
        cats = "".join(
            f'<a class="chipcat" href="{base}{s.category(c)["url"]}">'
            f'<span aria-hidden="true">{s.category(c)["icon"]}</span> {esc(s.category(c)["title"])}'
            f'<span class="chipcat__count">{len(s.category(c)["projects"])}</span></a>'
            for c in s.cat_order
        )
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Ateliers pratiques</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🧪</span> Ateliers pratiques</p>
  <h1 class="pagehead__title">{esc(sec.get("title", "Ateliers pratiques"))}</h1>
  <p class="pagehead__summary">{esc(sec.get("tagline", ""))}</p>
  <p class="pagehead__intro">{sec.get("intro", "")}</p>
</header>
<nav class="chipcats" aria-label="Catégories d'ateliers">{cats}</nav>
{filter_bar(s, base, target=".lcards > .lcard", noun="atelier")}
<div class="lcards">{cards}</div>
"""
        self.write("ateliers/index.html", layout(
            site=s, base=base, title="Ateliers pratiques — IA Générative",
            description=sec.get("tagline", "Applications d'IA à lire et à exécuter."),
            body=body, sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="ateliers/index.html", title="Ateliers pratiques", kind="Ateliers",
                          context="", summary=sec.get("tagline", ""),
                          md_text=sec.get("tagline", ""), toc=[])

    def build_app_category(self, cat: str) -> None:
        s, base = self.site, "../../"
        c = s.category(cat)
        cards = "".join(self.app_card(pid, base) for pid in c["projects"])
        lessons = "".join(
            f'<li><a href="{base}lecons/{sl}/index.html">'
            f'{s.lesson_meta[sl]["num"]} · {esc(s.lesson_meta[sl]["title"])}</a></li>'
            for sl in c["lessons"]
        )
        theory = (f'<section class="linkback"><h2>La théorie correspondante</h2>'
                  f'<ul class="linklist">{lessons}</ul></section>') if lessons else ""
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}ateliers/index.html">Ateliers</a> <span aria-hidden="true">›</span>
  <span>{esc(c["title"])}</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">{c["icon"]}</span> Catégorie d'ateliers</p>
  <h1 class="pagehead__title">{esc(c["title"])}</h1>
  <p class="pagehead__summary">{esc(c["summary"])}</p>
</header>
{filter_bar(s, base, target=".lcards > .lcard", noun="atelier")}
<div class="lcards">{cards}</div>
{theory}
"""
        self.write(c["url"], layout(
            site=s, base=base, title=f'{c["title"]} — ateliers',
            description=c["summary"], body=body,
            sidebar=sidebar_html(s, base, None, current_cat=cat), body_class="page-track",
        ))
        self.index_search(url=c["url"], title=c["title"], kind="Catégorie d'ateliers",
                          context="Ateliers pratiques", summary=c["summary"],
                          md_text=c["summary"], toc=[])

    def build_app(self, pid: str) -> None:
        s, base = self.site, "../../../"
        a, c = s.app(pid), s.category(s.apps["projects"][pid]["category"])
        owner = f"ateliers/{pid}"
        md_text = (CONTENT / "ateliers" / pid / "README.md").read_text(encoding="utf-8")
        body_html, toc = self.renderer.render(md_text, base)
        if not re.search(r"<h1[ >]", body_html):
            body_html = f'<h1 id="titre">{esc(a["title_en"])}</h1>' + body_html

        subs = s.app_subpages.get(pid, [])
        subs_html = ""
        if subs:
            items = "".join(
                f'<li><a href="{base}ateliers/{pid}/{x["slug"]}/index.html">{esc(x["title"])}</a></li>'
                for x in subs)
            subs_html = ('<section class="subpages"><h2 id="pages-de-l-atelier">Pages de cet atelier'
                         '<a class="anchor" href="#pages-de-l-atelier" aria-label="Lien vers cette section">#</a></h2>'
                         f'<ul class="linklist">{items}</ul></section>')

        code = code_section(
            s, owner, self.renderer, base,
            title="Code de l'atelier",
            intro="Tous les fichiers du projet, copiés depuis le dépôt d'origine. "
                  "Lisibles ici, et téléchargeables un par un.",
            skipped=a["skipped"],
            upstream_tree=f'{APPS_UPSTREAM}/tree/main/{a["path"]}',
        )
        if code:
            toc = toc + [{"id": "code-de-la-lecon", "text": "Code de l'atelier", "level": 2}]

        feats = ""
        if a["features"]:
            items = "".join(f"<li>{esc(f)}</li>" for f in a["features"])
            feats = ('<section class="feats"><h2 id="ce-que-fait-cet-atelier">Ce que fait cet atelier'
                     '<a class="anchor" href="#ce-que-fait-cet-atelier" aria-label="Lien vers cette section">#</a></h2>'
                     '<p class="feats__note">Extrait de la section « Features » du README d\'origine.</p>'
                     f'<ul>{items}</ul></section>')

        lessons = "".join(
            f'<li><a href="{base}lecons/{sl}/index.html">'
            f'{s.lesson_meta[sl]["num"]} · {esc(s.lesson_meta[sl]["title"])}</a></li>'
            for sl in c["lessons"])
        theory = (f'<section class="linkback"><h2 id="la-theorie">La théorie correspondante'
                  f'<a class="anchor" href="#la-theorie" aria-label="Lien vers cette section">#</a></h2>'
                  f'<ul class="linklist">{lessons}</ul></section>') if lessons else ""

        idx = s.app_order.index(pid)
        prev = s.app_order[idx - 1] if idx > 0 else None
        nxt = s.app_order[idx + 1] if idx + 1 < len(s.app_order) else None
        left = (f'<a class="prevnext__link prevnext__prev" href="{base}ateliers/{prev}/index.html">'
                f'<span class="prevnext__dir">← Atelier précédent</span>'
                f'<span class="prevnext__title">{esc(s.app(prev)["title"])}</span></a>'
                ) if prev else "<span></span>"
        right = (f'<a class="prevnext__link prevnext__next" href="{base}ateliers/{nxt}/index.html">'
                 f'<span class="prevnext__dir">Atelier suivant →</span>'
                 f'<span class="prevnext__title">{esc(s.app(nxt)["title"])}</span></a>'
                 ) if nxt else "<span></span>"

        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}ateliers/index.html">Ateliers</a> <span aria-hidden="true">›</span>
  <a href="{base}{c["url"]}">{esc(c["title"])}</a>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">{c["icon"]}</span> {esc(c["title"])}</p>
  <h1 class="pagehead__title">{esc(a["title"])}</h1>
  <p class="pagehead__summary">{esc(a["summary"])}</p>
  {tag_chips(s, a["tags"], base, link=True)}
  {topic_chips(s, s.topics_of.get(owner, []), base)}
</header>
{alternatives_box(s, owner, base)}
{feats}
<p class="langnote"><span aria-hidden="true">🌐</span> Le README ci-dessous est celui du dépôt
   d'origine et n'a pas été traduit : les commandes et noms de paquets restent en anglais.</p>
<article class="prose">
{body_html}
</article>
{subs_html}
{code}
{theory}
{related_block(s, owner, base)}
<section class="done" data-lesson-toggle="atelier:{pid}">
  <label class="done__label">
    <input class="done__box" type="checkbox">
    <span>J'ai fait tourner cet atelier</span>
  </label>
</section>
<nav class="prevnext" aria-label="Navigation entre les ateliers">{left}{right}</nav>
<p class="sourcelink">Source :
  <a href="{APPS_UPSTREAM}/tree/main/{a["path"]}" target="_blank" rel="noopener noreferrer">
    {esc(a["path"])}</a> dans awesome-llm-apps (Apache-2.0).
  Seuls les chemins d'images et les liens internes ont été réécrits.</p>
"""
        self.write(a["url"], layout(
            site=s, base=base, title=f'{a["title"]} — atelier',
            description=a["summary"], body=body,
            sidebar=sidebar_html(s, base, None, current_cat=c["id"]),
            toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(url=a["url"], title=a["title"], kind="Atelier",
                          context=c["title"], summary=a["summary"], md_text=md_text, toc=toc)

        for sub in subs:
            self.build_app_subpage(pid, sub)

    def build_app_subpage(self, pid: str, sub: dict) -> None:
        s, base = self.site, "../../../../"
        a, c = s.app(pid), s.category(s.apps["projects"][pid]["category"])
        md_text = (CONTENT / "ateliers" / pid / sub["rel"]).read_text(encoding="utf-8")
        body_html, toc = self.renderer.render(md_text, base)
        if not re.search(r"<h1[ >]", body_html):
            body_html = f'<h1 id="titre">{esc(sub["title"])}</h1>' + body_html
        url = f'ateliers/{pid}/{sub["slug"]}/index.html'
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}ateliers/index.html">Ateliers</a> <span aria-hidden="true">›</span>
  <a href="{base}{c["url"]}">{esc(c["title"])}</a> <span aria-hidden="true">›</span>
  <a href="{base}{a["url"]}">{esc(a["title"])}</a>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow">Page de l'atelier {esc(a["title"])}</p>
</header>
<article class="prose">
{body_html}
</article>
<p class="sourcelink">Source :
  <a href="{APPS_UPSTREAM}/blob/main/{a["path"]}/{sub["rel"]}" target="_blank" rel="noopener noreferrer">
    {esc(a["path"])}/{esc(sub["rel"])}</a></p>
"""
        self.write(url, layout(
            site=s, base=base, title=f'{sub["title"]} — {a["title"]}',
            description=f'{sub["title"]} — page de l\'atelier {a["title"]}.',
            body=body, sidebar=sidebar_html(s, base, None, current_cat=c["id"]),
            toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(url=url, title=sub["title"], kind="Page d'atelier",
                          context=a["title"], summary="", md_text=md_text, toc=toc)

    # -- prompts système ---------------------------------------------------

    def build_prompts_index(self) -> None:
        s, base = self.site, "../"
        sec = s.prompts_meta.get("section", {})
        cards = "".join(item_card(s, s.items[f"prompts/{t}"], base) for t in s.prompt_order)
        n_files = sum(len(s.prompts["tools"][t]["files"]) for t in s.prompt_order)
        n_defs = sum(s.prompts["tools"][t]["tool_defs"] for t in s.prompt_order)
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Prompts système</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🔍</span> Décortiquer</p>
  <h1 class="pagehead__title">{esc(sec.get("title", "Prompts système"))}</h1>
  <p class="pagehead__summary">{esc(sec.get("tagline", ""))}</p>
  <p class="pagehead__intro">{sec.get("intro", "")}</p>
</header>
<aside class="alts alts--warn">
  <p class="alts__lead"><span aria-hidden="true">⚠️</span> <strong>À lire avant de commencer.</strong>
     {esc(sec.get("disclaimer", ""))}</p>
</aside>
<p class="langnote"><span aria-hidden="true">🌐</span> Les prompts sont reproduits
   <strong>en anglais et sans aucune modification</strong> — c'est leur intérêt. Le titre,
   le résumé et l'analyse qui les accompagnent sont en français.</p>
<p><a class="btn btn--primary" href="{base}prompts-systeme/guide/index.html">
   Commencer par le guide de lecture</a></p>
<p class="statline">{len(s.prompt_order)} outils · {n_files} fichiers ·
   {n_defs} définitions d'outils · {sum(s.prompts["tools"][t]["chars"] for t in s.prompt_order) // 1000} k caractères</p>
{filter_bar(s, base, target=".lcards > .lcard", noun="outil", facets=("topics", "tags"))}
<div class="lcards">{cards}</div>
"""
        self.write("prompts-systeme/index.html", layout(
            site=s, base=base, title="Prompts système — IA Générative",
            description=sec.get("tagline", ""), body=body,
            sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="prompts-systeme/index.html", title="Prompts système",
                          kind="Prompts système", context="", summary=sec.get("tagline", ""),
                          md_text=sec.get("tagline", ""), toc=[], ctype="prompts")

    def gloss(self, name: str) -> dict | None:
        """Entrée de glossaire pour un nom de section, alias résolus."""
        entry = self.site.sectiondef.get(normalize_section(name))
        seen = 0
        while entry and "alias" in entry and seen < 5:
            entry = self.site.sectiondef.get(entry["alias"])
            seen += 1
        return entry if entry and "title" in entry else None

    def chrono_html(self, base: str) -> str:
        """Ce qui part ensemble, et ce qui s'enchaîne — la confusion la plus fréquente."""
        steps = [
            ("Le prompt système, en entier",
             "Toutes ses sections d'un seul bloc, dans l'ordre du fichier. Aucune n'est "
             "envoyée « plus tard » : ce n'est pas un déroulé, c'est un mode d'emploi."),
            ("Vos propres règles",
             "Fichier de règles du projet, préférences, instructions permanentes : ajoutées "
             "à la suite du prompt de l'éditeur, sans le remplacer."),
            ("Le contexte injecté",
             "Fichiers ouverts, système d'exploitation, arborescence du projet : rempli par "
             "le produit à l'exécution. C'est ce que sont les sections du type "
             "<code>user_info</code> ou <code>project_layout</code> — des trous, pas des consignes."),
            ("Votre message",
             "Il arrive en dernier, donc à la position la plus proche de la réponse : c'est "
             "aussi pour cela que plusieurs éditeurs répètent leurs consignes critiques à la fin."),
            ("La boucle d'outils",
             "Appel d'outil, résultat, nouvel appel, jusqu'à la réponse finale. À chaque tour, "
             "tout ce qui précède repart en entier — et se paie de nouveau."),
        ]
        items = "".join(
            f'<li class="chrono__step"><span class="chrono__n" aria-hidden="true">{n}</span>'
            f'<strong class="chrono__title">{t}</strong>'
            f'<span class="chrono__desc">{d}</span></li>'
            for n, (t, d) in enumerate(steps, 1))
        return (
            '<section class="chrono"><h2 id="chronologie">La chronologie d\'un tour'
            '<a class="anchor" href="#chronologie" aria-label="Lien vers cette section">#</a></h2>'
            '<p class="chrono__lead">Les sections d\'un prompt système <strong>ne sont pas des '
            'étapes</strong> : elles partent toutes ensemble, en tête de contexte, à chaque '
            'requête. Ce qui est chronologique, c\'est le tour de conversation.</p>'
            f'<ol class="chrono__steps">{items}</ol>'
            '<p class="chrono__note">Copier-coller ou procédure&nbsp;? Le texte se colle d\'un '
            'seul tenant. En revanche, <em>à l\'intérieur</em>, certaines sections décrivent bien '
            'une suite d\'étapes : elles portent la pastille <span class="nat nat--procedure">'
            'procédure</span> dans le plan ci-dessous. '
            f'<a href="{base}prompts-systeme/guide/index.html#chronologie">Le détail dans le '
            'guide</a></p></section>')

    def file_card_html(self, tid: str, f: dict, base: str) -> str:
        """Situer un fichier avant d'en montrer le texte."""
        fr = self.site.prompt_file(tid, f["name"])
        if not fr:
            return ""
        label = self.site.status_labels.get(fr.get("status", ""), "")
        badge = (f'<span class="fstatus fstatus--{esc(fr["status"])}">{esc(label)}</span>'
                 if label else "")
        rows = "".join(
            f"<dt>{k}</dt><dd>{esc(v)}</dd>"
            for k, v in (("Où ça s'applique", fr.get("surface", "")),
                         ("Quel modèle", fr.get("model", "")),
                         ("Quand il est envoyé", fr.get("when", "")),
                         ("Pourquoi celui-ci", fr.get("read", ""))) if v)
        return (f'<div class="filecard"><p class="filecard__head">'
                f'<span class="filecard__title">{esc(fr.get("title", f["name"]))}</span>'
                f'{badge}</p><dl class="filecard__list">{rows}</dl></div>')

    def file_table_html(self, tid: str, files: list[dict], base: str) -> str:
        """« Quel fichier, et où ? » — la vue qui manquait aux outils à plusieurs fichiers."""
        fr_tool = self.site.prompts_meta["tools"].get(tid, {})
        rows = []
        for f in files:
            fr = self.site.prompt_file(tid, f["name"])
            anchor = "fichier-" + slugify(f["name"])
            label = self.site.status_labels.get(fr.get("status", ""), "")
            badge = (f'<span class="fstatus fstatus--{esc(fr["status"])}">{esc(label)}</span>'
                     if label else "")
            star = ('<span class="filerow__first">à lire en premier</span>'
                    if fr.get("first") else "")
            # Le tableau doit rester lisible : on n'y garde que le nom du modèle, la
            # précision (« annoncé en première ligne », « sans objet ») reste sur la fiche.
            model = fr.get("model", "")
            short = model.split(" (")[0].rstrip(".")
            if short.startswith(("Le fichier", "Sans objet")) or not short:
                short = "—"
            cls = ' class="filerow--first"' if fr.get("first") else ""
            rows.append(
                f'<tr{cls}>'
                f'<td class="filerow__name"><a href="#{anchor}"><code>{esc(f["name"])}</code></a>'
                f'{star}<span class="filerow__what">{esc(fr.get("title", ""))} {badge}</span></td>'
                f'<td>{esc(fr.get("surface", "—"))}</td>'
                f'<td>{esc(short)}</td>'
                f'<td class="filerow__size">{human_size(f["size"])}</td></tr>')
        note = (f'<p class="filetable__intro">{fr_tool["files_note"]}</p>'
                if fr_tool.get("files_note") else "")
        return (
            '<section class="filetable"><h2 id="quel-fichier">Quel fichier, et où&nbsp;?'
            '<a class="anchor" href="#quel-fichier" aria-label="Lien vers cette section">#</a></h2>'
            + note +
            '<div class="filetable__wrap"><table><thead><tr><th>Fichier</th>'
            '<th>Où ça s\'applique</th><th>Quel modèle</th><th>Taille</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="filetable__warn"><strong>Ces textes ne se collent nulle part dans le '
            'produit.</strong> Ce ne sont pas des réglages à activer : ce sont les consignes que '
            'l\'éditeur envoie lui-même, à votre insu, selon l\'endroit où vous êtes. On les lit '
            'pour apprendre à écrire les siens.</p></section>')

    def prompt_outline_html(self, outline: list, base: str) -> str:
        """« Le plan du prompt » : la construction du texte, lisible sans un mot d'anglais."""
        if not outline:
            return ""
        blocks = []
        for fname, mode, secs, anchor in outline:
            if mode == "brut":
                blocks.append(
                    f'<div class="outline__file"><p class="outline__name">{esc(fname)}</p>'
                    f'<p class="note">Ce prompt n\'est pas découpé en sections : c\'est un texte '
                    f'continu de {secs[0]["lines"]} lignes. Ce n\'est pas un défaut d\'import — '
                    f'un cinquième des prompts du corpus est écrit ainsi.</p></div>')
                continue
            rows = []
            for sec in secs:
                g = self.gloss(sec["label"])
                label = esc(sec["label"])
                sid = f'{anchor}-{sec["key"]}'
                title = (f'<a href="#{sid}"><code>{label}</code></a>'
                         + (f' <span class="outline__fr">{esc(g["title"])}</span>' if g else ""))
                role = f'<span class="outline__role">{esc(g["role"])}</span>' if g else ""
                times = (f'<span class="outline__times">×{sec["count"]}</span>'
                         if sec.get("count", 1) > 1 else "")
                rows.append(f'<li class="outline__item">{title}{times}'
                            f'<span class="outline__size">{sec["lines"]} l.</span>'
                            f'{nature_badge(g, sec["body"])}{role}</li>')
            label = "balises" if mode == "balises" else "titres"
            blocks.append(
                f'<div class="outline__file"><p class="outline__name">{esc(fname)}'
                f'<span class="outline__meta">{len(secs)} sections, repérées par {label}</span></p>'
                f'<ol class="outline__list">{"".join(rows)}</ol></div>')
        return ('<section class="outline"><h2 id="plan-du-prompt">Le plan du prompt'
                '<a class="anchor" href="#plan-du-prompt" aria-label="Lien vers cette section">#</a></h2>'
                '<p class="outline__intro">La construction du prompt, avant son contenu. Les noms '
                'entre chevrons sont ceux de l\'éditeur ; l\'explication en regard vient de notre '
                f'<a href="{base}prompts-systeme/guide/index.html#glossaire">glossaire des sections</a> '
                'et vaut pour ce type de section en général.</p>'
                + "".join(blocks) + "</section>")

    def prompt_sections_html(self, secs: list[dict], mode: str, anchor: str, base: str) -> str:
        """Le texte, une section par bloc repliable — la première ouverte."""
        if mode == "brut":
            return code_block(secs[0]["body"], "text")
        out = []
        for n, sec in enumerate(secs):
            g = self.gloss(sec["label"])
            label = sec["label"]
            sid = f'{anchor}-{sec["key"]}'
            fr = f'<span class="promptsec__fr">{esc(g["title"])}</span>' if g else ""
            note = ""
            if g:
                lesson = g.get("lesson")
                link = (f' <a href="{base}lecons/{lesson}/index.html">'
                        f'Leçon {self.site.lesson_meta[lesson]["num"]}</a>'
                        if lesson in self.site.lesson_meta else "")
                note = f'<p class="promptsec__role">{esc(g["role"])}{link}</p>'
            out.append(
                f'<details class="promptsec" id="{sid}"{" open" if n == 0 else ""}>'
                f'<summary class="promptsec__head"><code class="promptsec__name">{esc(label)}</code>'
                f'{fr}{nature_badge(g, sec["body"])}'
                f'<span class="promptsec__size">{sec["lines"]} lignes</span></summary>'
                f'<div class="promptsec__body">{note}{code_block(sec["body"], "text")}</div></details>')
        return "".join(out)

    def build_prompt_guide(self) -> None:
        """La page qui manquait : ce qu'on regarde, et comment le regarder."""
        s, base = self.site, "../../"
        gloss_rows = "".join(
            f'<tr><td><code>{esc(k)}</code></td><td>{esc(v["title"])}</td>'
            f'<td>{nature_badge(v, "")}</td>'
            f'<td>{esc(v["role"])}'
            + (f' <a href="{base}lecons/{v["lesson"]}/index.html">'
               f'Leçon {s.lesson_meta[v["lesson"]]["num"]}</a>'
               if v.get("lesson") in s.lesson_meta else "")
            + "</td></tr>"
            for k, v in sorted(s.sectiondef.items()) if "title" in v
        )
        n_alias = sum(1 for v in s.sectiondef.values() if "alias" in v)
        per_tool: dict[str, int] = {}
        for key in s.filedef:
            per_tool[key.split("/")[0]] = per_tool.get(key.split("/")[0], 0) + 1
        n_files, n_multi = len(s.filedef), sum(1 for v in per_tool.values() if v > 1)
        nat_rows = "".join(
            f'<tr><td>{nature_badge({"nature": k}, "")}</td><td>{esc(why)}</td></tr>'
            for k, (_, why) in NATURES.items())
        toc = [
            {"id": "ce-que-cest", "text": "Ce qu'est un prompt système", "level": 2},
            {"id": "quand", "text": "Quand il est envoyé", "level": 2},
            {"id": "chronologie", "text": "La chronologie d'un tour", "level": 2},
            {"id": "ce-quil-change", "text": "Ce qu'il change", "level": 2},
            {"id": "ce-quil-coute", "text": "Ce qu'il coûte", "level": 2},
            {"id": "comment-lire", "text": "Comment en lire un", "level": 2},
            {"id": "plusieurs-fichiers", "text": "Plusieurs fichiers pour un même outil", "level": 2},
            {"id": "outils", "text": "Lire une définition d'outil", "level": 2},
            {"id": "glossaire", "text": "Glossaire des sections", "level": 2},
            {"id": "statut", "text": "Ce qu'on a le droit d'en faire", "level": 2},
        ]
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}prompts-systeme/index.html">Prompts système</a> <span aria-hidden="true">›</span>
  <span>Guide de lecture</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🧭</span> Guide</p>
  <h1 class="pagehead__title">Comment lire un prompt système</h1>
  <p class="pagehead__summary">Avant d'ouvrir les 40 fiches : ce que vous allez regarder, à quoi
     ça sert, et comment en tirer quelque chose pour vos propres projets.</p>
</header>

<article class="prose">
<h2 id="ce-que-cest">Ce qu'est un prompt système<a class="anchor" href="#ce-que-cest">#</a></h2>
<p>Quand vous écrivez à un assistant, votre message n'est pas le premier que le modèle reçoit.
   L'éditeur en a glissé un avant, que vous ne voyez jamais : le <strong>prompt système</strong>.
   Il dit au modèle qui il est, ce qu'il doit faire, comment répondre, ce qu'il ne doit jamais
   faire, et quels outils il peut appeler.</p>
<p>C'est du texte ordinaire, en langage naturel. Pas de code, pas de configuration : des
   phrases. C'est précisément ce qui rend ces documents lisibles — et instructifs.</p>

<h2 id="quand">Quand il est envoyé<a class="anchor" href="#quand">#</a></h2>
<p><strong>À chaque requête, en tête de contexte.</strong> C'est le point le plus souvent mal
   compris : le modèle n'« apprend » pas le prompt système une fois pour toutes. Il le relit
   intégralement à chaque échange, parce qu'il ne garde aucun souvenir d'un appel à l'autre.</p>
<p>Concrètement, l'ordre est toujours le même : prompt système, puis historique de la
   conversation, puis votre message. Ce qui est proche de la question pèse davantage — d'où
   les sections « rappels critiques » que plusieurs éditeurs placent tout à la fin.</p>

<h2 id="chronologie">La chronologie d'un tour<a class="anchor" href="#chronologie">#</a></h2>
<p>C'est la question qui revient le plus souvent en découvrant ces fichiers : <em>les sections
   sont-elles des étapes à suivre l'une après l'autre, ou faut-il tout coller ensemble ?</em>
   La réponse est nette : <strong>tout part ensemble</strong>. Un prompt système est un seul
   message, envoyé d'un bloc, avant la conversation. Son ordre interne est un ordre de lecture,
   pas un déroulé dans le temps.</p>
<p>Ce qui est réellement chronologique, c'est le tour de conversation :</p>
<ol>
  <li><strong>Le prompt système</strong>, en entier, toutes sections confondues.</li>
  <li><strong>Vos propres règles</strong> — fichier de règles du projet, préférences —
      ajoutées à la suite, sans remplacer les précédentes.</li>
  <li><strong>Le contexte injecté</strong> par le produit : fichiers ouverts, système,
      arborescence. Ces sections-là ne sont pas écrites par l'éditeur, elles sont
      <em>remplies</em> à l'exécution.</li>
  <li><strong>Votre message</strong>, en dernier — donc en position forte.</li>
  <li><strong>La boucle d'outils</strong> : appel, résultat, nouvel appel. À chaque tour,
      l'ensemble repart en entier, et se paie de nouveau.</li>
</ol>
<p>À l'intérieur du prompt, en revanche, toutes les sections n'ont pas le même statut. Le site
   les distingue par une pastille, dans le plan de chaque fiche :</p>
<div class="glosstable">
<table><thead><tr><th>Pastille</th><th>Ce que ça veut dire</th></tr></thead>
<tbody>{nat_rows}</tbody></table>
</div>
<p class="note">Cette pastille ne s'affiche que si le type de section est répertorié au
   glossaire. À défaut, le site se contente d'un décompte mesuré — « 9 points numérotés » —
   qui est un fait, pas une interprétation.</p>

<h2 id="ce-quil-change">Ce qu'il change<a class="anchor" href="#ce-quil-change">#</a></h2>
<p>Tout ce qui fait la personnalité d'un produit. Le même modèle, avec deux prompts systèmes
   différents, donne deux assistants qu'on ne reconnaîtrait pas comme parents :</p>
<ul>
  <li><strong>le ton et la longueur</strong> — bavard ou télégraphique ;</li>
  <li><strong>le format</strong> — Markdown, listes, blocs de code, citations ;</li>
  <li><strong>les refus</strong> — ce qu'il accepte de faire, et comment il décline le reste ;</li>
  <li><strong>l'usage des outils</strong> — quand chercher, quand exécuter, quand demander
      confirmation ;</li>
  <li><strong>l'initiative</strong> — anticiper, ou s'en tenir strictement à la demande.</li>
</ul>
<p>Ce qu'il ne change pas : ce que le modèle <em>sait</em>. Un prompt système ne lui apprend
   aucun fait nouveau — il ne fait que cadrer l'usage de ce qu'il sait déjà. Pour ajouter des
   connaissances, il faut du <a href="{base}sujets/rag/index.html">RAG</a> ou du
   <a href="{base}sujets/fine-tuning/index.html">fine-tuning</a>.</p>

<h2 id="ce-quil-coute">Ce qu'il coûte<a class="anchor" href="#ce-quil-coute">#</a></h2>
<p>Relu à chaque requête, il se paie à chaque requête. Un prompt de 10 000 mots, c'est de
   l'ordre de 13 000 jetons ajoutés à <em>chaque</em> appel — avant même que l'utilisateur ait
   parlé. À l'échelle de millions de requêtes, la facture est réelle, et la latence aussi.</p>
<p>C'est pourquoi les éditeurs les taillent en permanence, et pourquoi certains chargent des
   consignes <em>à la demande</em> plutôt que tout d'un bloc. Quand vous verrez une section
   très courte à côté d'une section fleuve, souvenez-vous que quelqu'un a arbitré.</p>

<h2 id="comment-lire">Comment en lire un<a class="anchor" href="#comment-lire">#</a></h2>
<p>N'essayez pas de lire ces textes de bout en bout : ils ne sont pas écrits pour ça. Sur
   chaque fiche du site, commencez par <strong>« Le plan du prompt »</strong>, qui montre sa
   construction avant son contenu. Puis dépliez seulement les sections qui vous intéressent.</p>
<p>Quatre choses valent le détour :</p>
<ol>
  <li><strong>La structure.</strong> Balises, titres, ou rien du tout ? Un prompt structuré est
      un prompt qui a été relu et corrigé plusieurs fois.</li>
  <li><strong>Les interdictions.</strong> Chaque « never » et chaque « do not » est la trace
      d'un échec constaté en production. C'est la partie la plus instructive.</li>
  <li><strong>Les exemples.</strong> Quand un éditeur montre un cas plutôt que d'énoncer une
      règle, c'est que la règle seule ne suffisait pas.</li>
  <li><strong>Les répétitions.</strong> Une consigne répétée en fin de texte est une consigne
      que le modèle oubliait.</li>
</ol>

<h2 id="plusieurs-fichiers">Plusieurs fichiers pour un même outil<a class="anchor" href="#plusieurs-fichiers">#</a></h2>
<p>Sur {n_multi} des 40 outils, le dépôt contient plusieurs fichiers — {n_files} en tout. Le nom
   du fichier ne dit pas lequel regarde quoi, et c'est là que la confusion commence. Il y a en
   réalité cinq cas, et chaque fiche du site les distingue par une pastille :</p>
<ul>
  <li><strong>Des versions successives.</strong> Cursor en a quatre pour son agent
      (v1.0, v1.2, 2.0, puis un état daté). Ce ne sont pas des variantes à choisir : ce sont
      des photos du même texte à des moments différents. Les comparer est l'exercice le plus
      formateur du site.</li>
  <li><strong>Des surfaces différentes du produit.</strong> Chez Cursor toujours, le volet de
      discussion, l'agent de l'éditeur et la ligne de commande ont chacun leur prompt. Vous
      n'en choisissez aucun : c'est l'endroit où vous êtes qui décide.</li>
  <li><strong>Des variantes par modèle.</strong> VS Code en publie six, une par modèle servi.
      Le produit est le même ; le texte est ajusté au modèle qui le recevra.</li>
  <li><strong>Un prompt et son catalogue d'outils.</strong> La découpe la plus fréquente : les
      deux partent dans la même requête, mais dans deux champs différents de l'API.</li>
  <li><strong>Des morceaux d'un même texte</strong>, découpés par celui qui les a extraits.
      Les six fichiers numérotés de Poke sont un seul prompt, pas six.</li>
</ul>
<p>D'où la mise en garde qui vaut pour tout le site : <strong>ces fichiers ne se collent nulle
   part</strong>. Ce ne sont pas des réglages à activer dans Cursor ou dans VS Code, mais les
   consignes que ces produits envoient déjà, à votre insu. On les lit pour apprendre à écrire
   les siens — chaque fiche dit, outil par outil, ce qui se transpose et ce qui ne se
   transpose pas.</p>

<h2 id="outils">Lire une définition d'outil<a class="anchor" href="#outils">#</a></h2>
<p>Plusieurs outils publient, à côté du prompt, un fichier <code>Tools.json</code>. Ce n'est pas
   un prompt : c'est le <strong>catalogue des actions</strong> que le modèle peut demander au
   produit d'exécuter — lire un fichier, lancer une commande, chercher sur le web.</p>
<p>Chaque entrée comporte trois choses :</p>
<ul>
  <li>un <strong>nom</strong>, que le modèle emploiera pour appeler l'outil ;</li>
  <li>une <strong>description</strong> en langage naturel ;</li>
  <li>des <strong>paramètres</strong> typés, dont certains obligatoires.</li>
</ul>
<p>Le point à retenir : <strong>c'est la description qui décide du bon appel</strong>, pas le
   prompt principal. Le modèle choisit son outil en lisant ces descriptions ; si l'une est
   vague, il l'appellera au mauvais moment quelles que soient les consignes par ailleurs. C'est
   pour cette raison que les descriptions des produits sérieux sont longues et donnent des
   exemples d'usage. La <a href="{base}lecons/11-integrating-with-function-calling/index.html">leçon 11</a>
   couvre le mécanisme côté code.</p>

<h2 id="glossaire">Glossaire des sections<a class="anchor" href="#glossaire">#</a></h2>
<p>Les éditeurs réutilisent les mêmes noms de section d'un produit à l'autre. Voici ceux que le
   site sait reconnaître : quand une section porte l'un de ces noms, son explication apparaît
   automatiquement dans le plan du prompt et au-dessus du texte.</p>
<p class="note">{sum(1 for v in s.sectiondef.values() if "title" in v)} types expliqués,
   {n_alias} variantes de nommage reconnues. Une section absente de cette table garde son nom
   brut, sans commentaire : mieux vaut ne rien dire que d'inventer une intention d'auteur.</p>
<div class="glosstable">
<table><thead><tr><th>Nom rencontré</th><th>Ce que c'est</th><th>Nature</th>
<th>À quoi ça sert</th></tr></thead>
<tbody>{gloss_rows}</tbody></table>
</div>

<h2 id="statut">Ce qu'on a le droit d'en faire<a class="anchor" href="#statut">#</a></h2>
<p>Ces textes n'ont été publiés par aucun éditeur. Ils ont été extraits de produits commerciaux
   par des tiers, puis rassemblés dans un dépôt public. Trois conséquences :</p>
<ul>
  <li><strong>Ils ne sont pas officiels</strong> et leur exactitude n'est pas vérifiable.</li>
  <li><strong>Ils vieillissent vite</strong> : un éditeur modifie son prompt sans prévenir.</li>
  <li><strong>Ils appartiennent à leurs auteurs.</strong> Les étudier est une chose ; les
      recopier dans un produit concurrent en est une autre.</li>
</ul>
<p>Lisez-les pour comprendre comment ces équipes s'y prennent, pas pour les reprendre tels
   quels. <a href="{base}prompts-systeme/index.html">Voir les 40 outils</a></p>
</article>
"""
        self.write("prompts-systeme/guide/index.html", layout(
            site=s, base=base, title="Comment lire un prompt système — guide",
            description="Ce qu'est un prompt système, quand il est envoyé, ce qu'il change, "
                        "ce qu'il coûte, et comment lire une définition d'outil.",
            body=body, sidebar=sidebar_html(s, base, None), toc=toc_html(toc),
            body_class="page-lesson",
        ))
        self.index_search(
            url="prompts-systeme/guide/index.html", title="Comment lire un prompt système",
            kind="Guide", context="Prompts système",
            summary="Ce qu'est un prompt système, quand il est envoyé, ce qu'il coûte.",
            md_text="prompt système contexte jetons outils définition tool_calling glossaire "
                    "chronologie ordre étapes copier-coller versions surfaces variantes modèle "
                    + " ".join(v.get("title", "") + " " + v.get("role", "")
                               for v in s.sectiondef.values()),
            toc=toc, ctype="prompts")

    def build_prompt(self, tid: str) -> None:
        s, base = self.site, "../../"
        p, item = s.prompt(tid), s.items[f"prompts/{tid}"]
        toc: list[dict] = []

        fr = s.prompts_meta["tools"].get(tid, {})
        situate = ""
        if fr.get("role"):
            situate = (
                '<section class="situate"><h2 id="a-quoi-il-sert">À quoi sert ce prompt'
                '<a class="anchor" href="#a-quoi-il-sert" aria-label="Lien vers cette section">#</a></h2>'
                '<dl class="situate__list">'
                f'<dt>Son rôle</dt><dd>{esc(fr["role"])}</dd>'
                f'<dt>Quand il est envoyé</dt><dd>{esc(fr.get("when", ""))}</dd>'
                f'<dt>Ce qu\'il produit</dt><dd>{esc(fr.get("output", ""))}</dd>'
                '</dl>'
                f'<p class="situate__guide">Première visite ? '
                f'<a href="{base}prompts-systeme/guide/index.html">Commencez par le guide</a> : '
                f'ce qu\'est un prompt système, quand il est envoyé et ce qu\'il coûte.</p>'
                '</section>')
            toc.append({"id": "a-quoi-il-sert", "text": "À quoi sert ce prompt", "level": 2})

        analysis = ""
        if fr.get("analysis"):
            analysis = ('<section class="analysis"><h2 id="analyse">Ce que ce prompt apprend'
                        '<a class="anchor" href="#analyse" aria-label="Lien vers cette section">#</a></h2>'
                        + "".join(f"<p>{x}</p>" for x in fr["analysis"]) + "</section>")
            toc.append({"id": "analyse", "text": "Ce que ce prompt apprend", "level": 2})

        learn = ""
        if p["learn"]:
            learn = ('<section class="feats"><h2 id="ce-quon-en-retient">Ce qu\'on en retient'
                     '<a class="anchor" href="#ce-quon-en-retient" aria-label="Lien vers cette section">#</a></h2>'
                     + "<ul>" + "".join(f"<li>{x}</li>" for x in p["learn"]) + "</ul></section>")
            toc.append({"id": "ce-quon-en-retient", "text": "Ce qu'on en retient", "level": 2})

        reuse = ""
        if fr.get("reuse"):
            reuse = ('<section class="reuse"><h2 id="reutiliser">Le réutiliser chez vous'
                     '<a class="anchor" href="#reutiliser" aria-label="Lien vers cette section">#</a></h2>'
                     '<p class="reuse__lead">Ce qui se transpose dans vos propres prompts, et ce '
                     'qui ne se transpose pas parce que cela n\'existe que dans ce produit.</p>'
                     "<ul>" + "".join(f"<li>{x}</li>" for x in fr["reuse"]) + "</ul></section>")
            toc.append({"id": "reutiliser", "text": "Le réutiliser chez vous", "level": 2})

        obs = s.prompt_observations(tid)
        obs_html = ""
        if obs:
            obs_html = ('<section class="obs"><h2 id="constats">Constats mesurés'
                        '<a class="anchor" href="#constats" aria-label="Lien vers cette section">#</a></h2>'
                        '<p class="obs__note">Calculés sur les fichiers eux-mêmes, sans interprétation.</p>'
                        + "<ul>" + "".join(f"<li>{x}</li>" for x in obs) + "</ul></section>")
            toc.append({"id": "constats", "text": "Constats mesurés", "level": 2})

        outline, blocks, tabs = [], [], []
        # Le fichier « à lire en premier » ouvre les onglets : sans cela, c'est l'ordre
        # alphabétique du dépôt qui décide de ce qu'on voit en arrivant.
        files = sorted(p["files"], key=lambda f: not s.prompt_file(tid, f["name"]).get("first"))
        multi = len(files) > 1
        for n, f in enumerate(files):
            anchor = "fichier-" + slugify(f["name"])
            tabs.append(
                f'<button class="tabs__btn" role="tab" aria-selected="{"true" if n == 0 else "false"}" '
                f'data-tab="{anchor}">{esc(f["name"])}</button>')
            dl = f'{base}assets/prompts-systeme/{tid}/{f["name"]}'
            head = (f'<h3 id="{anchor}">{esc(f["name"])}'
                    f'<a class="anchor" href="#{anchor}" aria-label="Lien vers cette section">#</a></h3>'
                    f'<p class="promptfile__meta">{human_size(f["size"])} · {f["lines"]} lignes · '
                    f'<a href="{dl}" download>télécharger le fichier d\'origine</a></p>')

            if f["kind"] == "outils" and f.get("tools"):
                body = TOOLS_NOTE.format(base=base, n=len(f["tools"])) + tool_definitions_html(f["tools"])
            else:
                path = DOCS / "assets" / "prompts-systeme" / tid / f["name"]
                text = path.read_text(encoding="utf-8", errors="replace")
                mode, secs = split_prompt(text)
                body = self.prompt_sections_html(secs, mode, anchor, base)
                outline.append((f["name"], mode, secs, anchor))

            card = self.file_card_html(tid, f, base)
            hidden = "" if n == 0 or not multi else " hidden"
            blocks.append(
                f'<div class="tabs__panel" data-tab="{anchor}"{hidden}>{head}{card}{body}</div>')

        table_html = self.file_table_html(tid, files, base) if multi else ""
        if table_html:
            toc.append({"id": "quel-fichier", "text": "Quel fichier, et où ?", "level": 2})

        chrono = self.chrono_html(base)
        toc.append({"id": "chronologie", "text": "La chronologie d'un tour", "level": 2})

        plan_html = self.prompt_outline_html(outline, base)
        if plan_html:
            toc.append({"id": "plan-du-prompt", "text": "Le plan du prompt", "level": 2})

        tabs_html = (f'<div class="tabs" role="tablist">{"".join(tabs)}</div>'
                     if multi else "")
        files_html = ('<section class="promptfiles codepanel"><h2 id="le-texte">Le texte, section par section'
                      '<a class="anchor" href="#le-texte" aria-label="Lien vers cette section">#</a></h2>'
                      '<p class="promptfiles__note">Le texte est reproduit <strong>intégralement et sans '
                      'modification</strong> ; seul son découpage à l\'écran est de nous. Chaque bloc se '
                      'déplie, et le fichier d\'origine reste téléchargeable.</p>'
                      + tabs_html + "".join(blocks) + "</section>")
        toc.append({"id": "le-texte", "text": "Le texte, section par section", "level": 2})

        lessons = "".join(
            f'<li><a href="{base}lecons/{sl}/index.html">'
            f'{s.lesson_meta[sl]["num"]} · {esc(s.lesson_meta[sl]["title"])}</a></li>'
            for sl in p["lessons"])
        theory = (f'<section class="linkback"><h2 id="la-theorie">La théorie correspondante'
                  f'<a class="anchor" href="#la-theorie" aria-label="Lien vers cette section">#</a></h2>'
                  f'<ul class="linklist">{lessons}</ul></section>') if lessons else ""

        idx = s.prompt_order.index(tid)
        prev = s.prompt_order[idx - 1] if idx > 0 else None
        nxt = s.prompt_order[idx + 1] if idx + 1 < len(s.prompt_order) else None
        left = (f'<a class="prevnext__link prevnext__prev" href="{base}prompts-systeme/{prev}/index.html">'
                f'<span class="prevnext__dir">← Précédent</span>'
                f'<span class="prevnext__title">{esc(s.prompt(prev)["title"])}</span></a>'
                ) if prev else "<span></span>"
        right = (f'<a class="prevnext__link prevnext__next" href="{base}prompts-systeme/{nxt}/index.html">'
                 f'<span class="prevnext__dir">Suivant →</span>'
                 f'<span class="prevnext__title">{esc(s.prompt(nxt)["title"])}</span></a>'
                 ) if nxt else "<span></span>"

        editor = f' · {esc(p["editor"])}' if p["editor"] else ""
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}prompts-systeme/index.html">Prompts système</a>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🔍</span> Prompt système{editor}</p>
  <h1 class="pagehead__title">{esc(p["title"])}</h1>
  <p class="pagehead__summary">{esc(p["what"])}</p>
  {tag_chips(s, p["tags"], base, link=True)}
  {topic_chips(s, p["topics"], base)}
</header>
<aside class="alts alts--warn"><p class="alts__lead"><span aria-hidden="true">⚠️</span>
  Texte extrait d'un produit commercial par un tiers : ni officiel, ni vérifiable, et
  possiblement périmé. Reproduit ici à des fins d'étude.</p></aside>
{situate}
{analysis}
{learn}
{reuse}
{obs_html}
{table_html}
{chrono}
{plan_html}
{files_html}
{theory}
{related_block(s, item["id"], base)}
<section class="done" data-lesson-toggle="prompt:{tid}">
  <label class="done__label">
    <input class="done__box" type="checkbox">
    <span>J'ai lu ce prompt</span>
  </label>
</section>
<nav class="prevnext" aria-label="Navigation entre les prompts">{left}{right}</nav>
<p class="sourcelink">Source :
  <a href="{PROMPTS_UPSTREAM}/tree/main/{p["path"].replace(" ", "%20")}"
     target="_blank" rel="noopener noreferrer">{esc(p["path"])}</a>
  dans system-prompts-and-models-of-ai-tools (GPL-3.0). Fichiers repris à l'octet près.</p>
"""
        self.write(p["url"], layout(
            site=s, base=base, title=f'{p["title"]} — prompt système',
            description=p["what"] or f'Le prompt système de {p["title"]}.', body=body,
            sidebar=sidebar_html(s, base, None), toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(url=p["url"], title=p["title"], kind="Prompt système",
                          context=p["editor"], summary=p["what"],
                          md_text=" ".join([p["what"]] + [re.sub(r"<[^>]+>", "", x) for x in p["learn"]]),
                          toc=toc, ctype="prompts")

    # -- sujets et catalogue -----------------------------------------------

    def build_topics_index(self) -> None:
        s, base = self.site, "../"
        cards = []
        for tid, t in sorted(s.topicdef.items(), key=lambda kv: kv[1]["order"]):
            counts = "".join(
                f'<span class="tcard__count"><span aria-hidden="true">{c["icon"]}</span> '
                f'{len(s.items_by_topic(tid, cid))}</span>'
                for cid, c in sorted(COLLECTIONS.items(), key=lambda kv: kv[1]["order"])
                if s.items_by_topic(tid, cid)
            )
            cards.append(
                f'<article class="tcard"><a class="tcard__head" href="{base}sujets/{tid}/index.html">'
                f'<span class="tcard__icon" aria-hidden="true">{t["icon"]}</span>'
                f'<h3 class="tcard__title">{esc(t["title"])}</h3></a>'
                f'<p class="tcard__summary">{esc(t["summary"])}</p>'
                f'<p class="tcard__meta">{counts}</p></article>'
            )
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Sujets</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🗺️</span> Par thème</p>
  <h1 class="pagehead__title">Les {len(s.topicdef)} sujets</h1>
  <p class="pagehead__summary">Le cours, les ateliers et les prompts système parlent souvent
     des mêmes choses. Chaque sujet rassemble au même endroit ce que les trois familles en
     disent — la théorie, la mise en pratique, et ce qu'en fait l'industrie.</p>
</header>
<div class="tcards">{"".join(cards)}</div>
"""
        self.write("sujets/index.html", layout(
            site=s, base=base, title="Sujets — IA Générative",
            description="Les grands thèmes du site, chacun croisant leçons, ateliers et prompts système.",
            body=body, sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="sujets/index.html", title="Les sujets", kind="Sujets", context="",
                          summary="Les grands thèmes, croisant les trois familles de contenu.",
                          md_text=" ".join(t["title"] + " " + t["summary"] for t in s.topicdef.values()),
                          toc=[])

    def build_topic(self, tid: str) -> None:
        s, base = self.site, "../../"
        t = s.topicdef[tid]
        sections, toc = [], []
        for cid, c in sorted(COLLECTIONS.items(), key=lambda kv: kv[1]["order"]):
            found = sorted(s.items_by_topic(tid, cid), key=lambda i: i["title"])
            if not found:
                continue
            anchor = slugify(c["verb"])
            toc.append({"id": anchor, "text": f'{c["verb"]} ({len(found)})', "level": 2})
            cards = "".join(item_card(s, i, base) for i in found)
            sections.append(
                f'<section class="topicsec"><h2 id="{anchor}">'
                f'<span aria-hidden="true">{c["icon"]}</span> {esc(c["verb"])}'
                f'<span class="topicsec__count">{len(found)} {esc(c["label"].lower())}'
                f'{"s" if len(found) > 1 else ""}</span>'
                f'<a class="anchor" href="#{anchor}" aria-label="Lien vers cette section">#</a></h2>'
                f'<div class="lcards">{cards}</div></section>'
            )
        others = "".join(
            f'<a class="chipcat" href="{base}sujets/{o}/index.html">'
            f'<span aria-hidden="true">{s.topicdef[o]["icon"]}</span> {esc(s.topicdef[o]["title"])}</a>'
            for o in sorted(s.topicdef, key=lambda x: s.topicdef[x]["order"]) if o != tid
        )
        total = len(s.items_by_topic(tid))
        content = "".join(sections) or (
            '<p class="note">Aucun contenu rattaché à ce sujet pour le moment.</p>')
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}sujets/index.html">Sujets</a> <span aria-hidden="true">›</span>
  <span>{esc(t["title"])}</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">{t["icon"]}</span> Sujet</p>
  <h1 class="pagehead__title">{esc(t["title"])}</h1>
  <p class="pagehead__summary">{esc(t["summary"])}</p>
  <p class="statline">{total} contenu(s) sur ce sujet</p>
</header>
{content}
<section class="othertopics"><h2>Les autres sujets</h2>
  <div class="chipcats">{others}</div></section>
"""
        self.write(f"sujets/{tid}/index.html", layout(
            site=s, base=base, title=f'{t["title"]} — sujet', description=t["summary"],
            body=body, sidebar=sidebar_html(s, base, None), toc=toc_html(toc),
            body_class="page-track",
        ))
        self.index_search(url=f"sujets/{tid}/index.html", title=t["title"], kind="Sujet",
                          context="Sujets", summary=t["summary"], md_text=t["summary"], toc=toc)

    def build_catalogue(self) -> None:
        s, base = self.site, "../"
        order = sorted(s.items.values(),
                       key=lambda i: (COLLECTIONS[i["collection"]]["order"], i["title"]))
        cards = "".join(item_card(s, i, base, show_type=True) for i in order)
        counts = " · ".join(
            f'{sum(1 for i in order if i["collection"] == cid)} {c["plural"].lower()}'
            for cid, c in sorted(COLLECTIONS.items(), key=lambda kv: kv[1]["order"]))
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Catalogue</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🗂️</span> Tout le contenu</p>
  <h1 class="pagehead__title">Catalogue</h1>
  <p class="pagehead__summary">Les {len(order)} contenus du site en une seule liste :
     {counts}. Croisez type, sujet et tags pour trouver exactement ce que vous cherchez.</p>
</header>
{filter_bar(s, base, target=".lcards > .lcard", noun="contenu",
            facets=("type", "topics", "tags"))}
<div class="lcards">{cards}</div>
"""
        self.write("catalogue/index.html", layout(
            site=s, base=base, title="Catalogue — IA Générative",
            description=f"Les {len(order)} contenus du site, filtrables par type, sujet et tags.",
            body=body, sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="catalogue/index.html", title="Catalogue", kind="Catalogue",
                          context="", summary="Tout le contenu, filtrable.",
                          md_text="catalogue tout le contenu filtrer type sujet tags", toc=[])

    # -- tags et alternatives ---------------------------------------------

    def build_tags_page(self) -> None:
        s, base = self.site, "../"
        groups = sorted(s.tagdef["groups"].items(), key=lambda kv: kv[1]["order"])
        blocks = []
        for gid, g in groups:
            rows = "".join(
                f'<li class="legend__row" id="{t}">'
                f'<span class="tag tag--{gid}"><span class="tag__icon" aria-hidden="true">{v["icon"]}</span>'
                f'<span class="tag__label">{esc(v["label"])}</span></span>'
                f'<span class="legend__desc">{esc(v["desc"])}</span></li>'
                for t, v in s.tagdef["values"].items() if v["group"] == gid
            )
            blocks.append(
                f'<section class="legend"><h2 id="{gid}">{esc(g["title"])}'
                f'<a class="anchor" href="#{gid}" aria-label="Lien vers cette section">#</a></h2>'
                f'<p class="legend__help">{esc(g["help"])}</p>'
                f'<ul class="legend__list">{rows}</ul></section>'
            )
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span><span>Légende des tags</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🏷️</span> Repères</p>
  <h1 class="pagehead__title">Que veulent dire les tags ?</h1>
  <p class="pagehead__summary">Chaque leçon et chaque atelier porte quelques tags, pour vous
     aider à choisir quoi faire ensuite. Ils sont filtrables depuis l'accueil et le catalogue
     des ateliers.</p>
</header>
<aside class="alts alts--free"><p class="alts__lead"><span aria-hidden="true">ℹ️</span>
  Les tags d'intérêt, de difficulté et de nature sont un avis pédagogique — utile comme
  point de départ, pas comme verdict. Le tag de coût, lui, est calculé automatiquement à
  partir des services que la page exige réellement.</p></aside>
{"".join(blocks)}
"""
        self.write("tags/index.html", layout(
            site=s, base=base, title="Légende des tags — IA Générative",
            description="Ce que signifient les tags d'intérêt, de difficulté, de coût et de nature.",
            body=body, sidebar=sidebar_html(s, base, None), body_class="page-track",
        ))
        self.index_search(url="tags/index.html", title="Légende des tags", kind="Repères",
                          context="", summary="Intérêt, difficulté, coût, nature.",
                          md_text=" ".join(v["label"] + " " + v["desc"]
                                           for v in s.tagdef["values"].values()), toc=[])

    def build_alternatives_page(self) -> None:
        s, base = self.site, "../../"
        defs = s.services["services"]
        users: dict[str, list[tuple[str, str]]] = {}
        for slug in s.order:
            for sid in s.services_of.get(slug, []):
                users.setdefault(sid, []).append(
                    (f'{base}lecons/{slug}/index.html',
                     f'Leçon {s.lesson_meta[slug]["num"]} — {s.lesson_meta[slug]["title"]}'))
        for pid in s.app_order:
            for sid in s.services_of.get(f"ateliers/{pid}", []):
                users.setdefault(sid, []).append((f'{base}ateliers/{pid}/index.html',
                                                  s.app(pid)["title"]))

        cats = sorted(s.services["categories"].items(), key=lambda kv: kv[1]["order"])
        blocks, toc = [], []
        for cid, cat in cats:
            services = [(sid, sv) for sid, sv in defs.items() if sv["category"] == cid]
            if not services:
                continue
            toc.append({"id": cid, "text": cat["title"], "level": 2})
            rows = []
            for sid, sv in sorted(services, key=lambda kv: kv[1]["name"]):
                used = users.get(sid, [])
                if not sv["free"] and sv["cost"] == "gratuit":
                    subs = '<em>Déjà gratuit — c\'est lui, l\'alternative.</em>'
                else:
                    subs = "<ul>" + "".join(
                        f'<li><a href="{esc(f["url"])}" target="_blank" rel="noopener noreferrer">'
                        f'{esc(f["name"])}</a> — {esc(f["note"])}</li>' for f in sv["free"]
                    ) + "</ul>"
                pages = ""
                if used:
                    shown = "".join(f'<li><a href="{u}">{esc(t)}</a></li>' for u, t in used[:8])
                    more = (f'<li class="alttable__more">et {len(used) - 8} autre(s)</li>'
                            if len(used) > 8 else "")
                    pages = f'<ul class="alttable__pages">{shown}{more}</ul>'
                else:
                    pages = '<span class="alttable__none">—</span>'
                rows.append(
                    f'<tr id="service-{sid}"><td><a href="{esc(sv["url"])}" target="_blank" '
                    f'rel="noopener noreferrer">{esc(sv["name"])}</a>'
                    f'<span class="alttable__cost alttable__cost--{sv["cost"]}">'
                    f'{esc(s.services["cost_labels"].get(sv["cost"], sv["cost"]))}</span>'
                    f'<span class="alttable__note">{esc(sv.get("note", ""))}</span></td>'
                    f'<td>{subs}</td><td>{pages}</td></tr>'
                )
            blocks.append(
                f'<section class="alttable"><h2 id="{cid}">'
                f'<span aria-hidden="true">{cat["icon"]}</span> {esc(cat["title"])}'
                f'<a class="anchor" href="#{cid}" aria-label="Lien vers cette section">#</a></h2>'
                f'<table><thead><tr><th>Service</th><th>Alternatives gratuites</th>'
                f'<th>Où il apparaît</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>'
            )
        body = f"""
<nav class="crumbs" aria-label="Fil d'Ariane">
  <a href="{base}index.html">Accueil</a> <span aria-hidden="true">›</span>
  <a href="{base}annexes/index.html">Annexes</a> <span aria-hidden="true">›</span>
  <span>Alternatives gratuites</span>
</nav>
<header class="pagehead">
  <p class="pagehead__eyebrow"><span aria-hidden="true">🆓</span> Apprendre sans dépenser</p>
  <h1 class="pagehead__title">Alternatives gratuites aux outils payants</h1>
  <p class="pagehead__summary">Le cours et les ateliers s'appuient sur des services souvent
     facturés. Pour chacun, voici ce qui le remplace gratuitement, et les pages du site où
     il intervient. Cette table est aussi ce qui calcule le tag de coût de chaque page.</p>
</header>
<aside class="alts alts--free"><p class="alts__lead"><span aria-hidden="true">💡</span>
  <strong>Le plus court chemin :</strong> un compte GitHub donne accès à
  <a href="https://github.com/marketplace/models" target="_blank" rel="noopener noreferrer">GitHub Models</a>
  gratuitement, et <a href="https://ollama.com" target="_blank" rel="noopener noreferrer">Ollama</a>
  fait tourner les modèles ouverts sur votre machine. À eux deux, ils couvrent la quasi-totalité
  du cours sans carte bancaire.</p></aside>
{"".join(blocks)}
"""
        self.write("annexes/alternatives-gratuites/index.html", layout(
            site=s, base=base, title="Alternatives gratuites — IA Générative",
            description="Pour chaque service payant utilisé par le cours et les ateliers, "
                        "les substituts gratuits et les pages concernées.",
            body=body, sidebar=sidebar_html(s, base, None),
            toc=toc_html(toc), body_class="page-lesson",
        ))
        self.index_search(
            url="annexes/alternatives-gratuites/index.html",
            title="Alternatives gratuites aux outils payants", kind="Annexe", context="Annexes",
            summary="Substituts gratuits aux services facturés du cours et des ateliers.",
            md_text=" ".join(
                f'{sv["name"]} ' + " ".join(f["name"] + " " + f["note"] for f in sv["free"])
                for sv in defs.values()),
            toc=toc)

    def build_404(self) -> None:
        body = """
<div class="hero">
  <p class="hero__eyebrow">Erreur 404</p>
  <h1 class="hero__title">Cette page n'existe pas</h1>
  <p class="hero__tagline">Le lien est peut-être obsolète. Reprenez depuis l'accueil du cours.</p>
  <div class="hero__actions"><a class="btn btn--primary" href="index.html">Retour à l'accueil</a></div>
</div>
"""
        self.write("404.html", layout(site=self.site, base="", title="Page introuvable — IA Générative",
                                      description="Page introuvable.", body=body, body_class="page-home"))

    def prune_images(self) -> int:
        """Supprime les images plus référencées par aucune page.

        Les deux scripts d'ingestion alimentent le même dossier `assets/images/` ; aucun
        des deux ne peut donc le vider sans effacer le travail de l'autre. C'est ici,
        une fois toutes les pages écrites, qu'on sait ce qui sert encore.
        """
        img_dir = DOCS / "assets" / "images"
        if not img_dir.is_dir():
            return 0
        used: set[str] = set()
        for page in DOCS.rglob("*.html"):
            if "assets" in page.relative_to(DOCS).parts:
                continue
            for m in re.finditer(r'assets/images/([^"\'\s>)]+)', page.read_text(encoding="utf-8")):
                used.add(m.group(1))
        removed = 0
        for img in img_dir.iterdir():
            if img.is_file() and img.name not in used:
                img.unlink()
                removed += 1
        return removed

    def run(self) -> None:
        s = self.site
        s.scan_code()
        s.scan_pages()
        s.scan_app_pages()
        s.scan_services()
        s.scan_tags()
        s.register_items()
        s.scan_topics()

        if DOCS.exists():
            for child in DOCS.iterdir():
                if child.name == "assets":
                    # N'effacer que ce que *ce* script produit. Tout le reste d'`assets/`
                    # vient de l'ingestion (images, code, prompts) et serait perdu ; la
                    # liste est en positif pour qu'une future source survive d'office.
                    for a in child.iterdir():
                        if a.name in BUILD_ASSETS:
                            shutil.rmtree(a) if a.is_dir() else a.unlink()
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()

        self.build_assets()
        self.build_home()
        for track in s.tracks:
            self.build_track(track)
        for slug in s.order:
            self.build_lesson(slug)
            for sub in s.subpages.get(slug, []):
                self.build_subpage(slug, sub)
        if s.app_order:
            self.build_apps_index()
            for cat in s.cat_order:
                self.build_app_category(cat)
            for pid in s.app_order:
                self.build_app(pid)
        if s.prompt_order:
            self.build_prompts_index()
            self.build_prompt_guide()
            for tid in s.prompt_order:
                self.build_prompt(tid)
        self.build_topics_index()
        for tid in s.topicdef:
            self.build_topic(tid)
        self.build_catalogue()
        self.build_annexes()
        self.build_alternatives_page()
        self.build_tags_page()
        self.build_404()

        pruned = self.prune_images()

        # Chargé par une balise <script> plutôt que par fetch() : la recherche
        # fonctionne ainsi même quand le site est ouvert depuis le disque (file://).
        (DOCS / "assets" / "search-index.js").write_text(
            "window.GENAI_INDEX="
            + json.dumps(s.search, ensure_ascii=False, separators=(",", ":"))
            + ";\n",
            encoding="utf-8",
        )

        # Ne compter que les pages du site : `assets/code/` contient des .html
        # appartenant aux projets copiés.
        pages = sum(1 for p in DOCS.rglob("*.html")
                    if "assets" not in p.relative_to(DOCS).parts)
        paid = sum(1 for o in s.tags_of if "payant" in s.tags_of[o])
        print(f"✓ {pages} pages HTML générées dans docs/")
        print(f"  {len(s.order)} leçons + {sum(len(v) for v in s.subpages.values())} pages annexes")
        print(f"  {len(s.app_order)} ateliers dans {len(s.cat_order)} catégories "
              f"+ {sum(len(v) for v in s.app_subpages.values())} pages d'atelier")
        print(f"  {len(s.prompt_order)} prompts système · {len(s.topicdef)} sujets "
              f"· {len(s.items)} contenus au catalogue")
        print(f"  {len(s.search)} entrées de recherche · {paid} pages exigeant un service payant "
              f"(alternatives affichées)")
        if pruned:
            print(f"  {pruned} image(s) orpheline(s) supprimée(s)")
        for w in s.warnings:
            print(f"⚠ {w}")


def main() -> int:
    if not (CONTENT / "_ingest.json").exists():
        print("Lancez d'abord `python3 tools/ingest.py`.", file=sys.stderr)
        return 1
    Builder(Site()).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
