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
CODE = ROOT / "code"
DOCS = ROOT / "docs"
ASSETS_SRC = Path(__file__).resolve().parent / "assets"

UPSTREAM = "https://github.com/microsoft/generative-ai-for-beginners"
UPSTREAM_FR = f"{UPSTREAM}/blob/main/translations/fr"

LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".js": "javascript", ".cs": "csharp",
    ".json": "json", ".jsonl": "json", ".sh": "bash", ".ps1": "powershell",
    ".bat": "batch", ".xml": "xml", ".csproj": "xml", ".yml": "yaml", ".yaml": "yaml",
    ".html": "html", ".css": "css", ".md": "markdown", ".txt": "text",
    ".dib": "text", ".env-sample": "ini", ".gitignore": "text",
}
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

class Site:
    def __init__(self) -> None:
        self.meta = json.loads((CONTENT / "_meta.json").read_text(encoding="utf-8"))
        self.ingest = json.loads((CONTENT / "_ingest.json").read_text(encoding="utf-8"))
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
        # Les notebooks référencent les images anglaises : on les retrouve par leur nom
        # de base parmi celles déjà publiées (la variante traduite porte le même nom).
        img_dir = DOCS / "assets" / "images"
        self.image_by_stem: dict[str, str] = {
            p.stem: p.name for p in sorted(img_dir.glob("*")) if p.is_file()
        }

    # -- code -------------------------------------------------------------

    def scan_code(self) -> None:
        for slug in self.order:
            files = self.ingest["lessons"].get(slug, {}).get("code", [])
            entries = []
            for rel in files:
                path = CODE / slug / rel
                if not path.is_file():
                    self.warnings.append(f"fichier de code manquant : {slug}/{rel}")
                    continue
                group = rel.split("/")[0] if "/" in rel else ""
                entries.append({
                    "rel": rel,
                    "group": group if group in GROUP_LABELS else group,
                    "size": path.stat().st_size,
                    "anchor": path_anchor(rel),
                    "path": path,
                })
            self.code_index[slug] = entries

    def code_groups(self, slug: str) -> list[tuple[str, list[dict]]]:
        groups: dict[str, list[dict]] = {}
        for e in self.code_index.get(slug, []):
            groups.setdefault(e["group"], []).append(e)
        return sorted(groups.items(), key=lambda kv: (kv[0] == "", kv[0]))

    # -- pages ------------------------------------------------------------

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
  <a class="topbar__brand" href="{base}index.html"><span aria-hidden="true">🧠</span> IA Générative — le cours</a>
  <div class="search" role="search">
    <input class="search__input" type="search" placeholder="Rechercher dans le cours…"
           aria-label="Rechercher dans le cours" autocomplete="off">
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


def sidebar_html(site: Site, base: str, current: str | None, current_sub: str | None = None) -> str:
    out = ['<nav class="sidebar" aria-label="Sommaire du cours"><div class="sidebar__inner">']
    out.append(f'<a class="sidebar__home" href="{base}index.html">Accueil du cours</a>')
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
    out.append(
        f'<section class="sidebar__track"><h2 class="sidebar__track-title">'
        f'<span class="sidebar__icon" aria-hidden="true">📎</span>'
        f'<a href="{base}annexes/index.html">Annexes</a></h2></section>'
    )
    out.append("</div></nav>")
    return "".join(out)


def toc_html(toc: list[dict]) -> str:
    if len(toc) < 2:
        return ""
    items = "".join(
        f'<li class="toc__item toc__item--h{t["level"]}"><a href="#{t["id"]}">{esc(t["text"])}</a></li>'
        for t in toc
    )
    return ('<aside class="toc" aria-label="Sommaire de la page"><div class="toc__inner">'
            f'<p class="toc__title">Sur cette page</p><ul class="toc__list">{items}</ul></div></aside>')


def code_section(site: Site, slug: str, renderer: Renderer, base: str) -> str:
    entries = site.code_index.get(slug, [])
    skipped = site.ingest["lessons"].get(slug, {}).get("skipped", [])
    if not entries:
        return ""
    groups = site.code_groups(slug)
    out = ['<section class="codepanel" id="code">',
           '<h2 id="code-de-la-lecon">Code de la leçon'
           '<a class="anchor" href="#code-de-la-lecon" aria-label="Lien vers cette section">#</a></h2>',
           '<p class="codepanel__intro">Tous les fichiers d\'exemple de cette leçon, copiés depuis le dépôt '
           'd\'origine. Chaque fichier est lisible ici et téléchargeable.</p>']
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
            out.append(render_code_file(f, slug, renderer, base))
        out.append("</div>")
    if skipped:
        items = "".join(
            f'<li><code>{esc(s["path"])}</code> — {esc(s["reason"])} ({human_size(s["size"])})</li>'
            for s in skipped
        )
        out.append(
            '<details class="codepanel__skipped"><summary>Fichiers volumineux non embarqués '
            f'({len(skipped)})</summary><ul>{items}</ul>'
            f'<p>Ils restent disponibles dans le <a href="{UPSTREAM}/tree/main/{slug}" '
            'target="_blank" rel="noopener noreferrer">dépôt d\'origine</a>.</p></details>'
        )
    out.append("</section>")
    return "".join(out)


def render_code_file(entry: dict, slug: str, renderer: Renderer, base: str) -> str:
    rel, path = entry["rel"], entry["path"]
    dl = f"{base}assets/code/{slug}/{rel}"
    head = (
        f'<summary class="codefile__head"><span class="codefile__name">{esc(rel)}</span>'
        f'<span class="codefile__size">{human_size(entry["size"])}</span></summary>'
    )
    actions = (f'<p class="codefile__actions"><a href="{dl}" download>Télécharger ce fichier</a></p>')

    if NO_RENDER.search(rel) or entry["size"] > MAX_RENDER_BYTES:
        body = ('<p class="note">Fichier généré ou volumineux : il n\'est pas affiché ici.</p>' + actions)
    elif rel.endswith(".ipynb"):
        hook = notebook_link_hook(renderer.site, slug, rel, base, entry["anchor"])
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
                     summary: str, md_text: str, toc: list[dict]) -> None:
        self.site.search.append({
            "u": url, "t": title, "k": kind, "c": context, "s": summary,
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

        dest = DOCS / "assets" / "code"
        if dest.exists():
            shutil.rmtree(dest)
        if CODE.exists():
            shutil.copytree(CODE, dest)

    # -- pages ------------------------------------------------------------

    def build_home(self) -> None:
        s, meta = self.site, self.site.meta["site"]
        total = len(s.order)
        cards = []
        for track in s.tracks:
            items = "".join(
                f'<li class="tcard__lesson" data-lesson="{slug}">'
                f'<a href="lecons/{slug}/index.html">'
                f'<span class="tcard__num">{s.lesson_meta[slug]["num"]}</span>'
                f'<span class="tcard__label">{esc(s.lesson_meta[slug]["title"])}</span>'
                f'<span class="sidebar__check" aria-hidden="true"></span></a></li>'
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
        annexes = "".join(
            f'<li><a href="annexes/{k}/index.html">{esc(v["title"])}</a> — {esc(v["summary"])}</li>'
            for k, v in s.annexe_meta["pages"].items()
        )
        body = f"""
<div class="hero">
  <p class="hero__eyebrow">Cours complet · {total} leçons · en français</p>
  <h1 class="hero__title">{esc(meta["title"])}</h1>
  <p class="hero__tagline">{esc(meta["tagline"])}</p>
  <p class="hero__intro">{meta["intro"]}</p>
  <div class="hero__actions">
    <a class="btn btn--primary" href="lecons/{s.order[0]}/index.html">Commencer le cours</a>
    <a class="btn" href="lecons/01-introduction-to-genai/index.html">J'ai déjà mon environnement</a>
  </div>
  <div class="progress" data-global-progress>
    <div class="progress__bar"><span class="progress__fill"></span></div>
    <p class="progress__label">Progression : <strong class="progress__text">0 / {total}</strong> leçons terminées
      <button class="progress__reset" type="button">réinitialiser</button></p>
  </div>
</div>

<section class="section">
  <h2 class="section__title">Les {len(s.tracks)} parcours</h2>
  <p class="section__intro">Suivez-les dans l'ordre : chaque parcours s'appuie sur le précédent.
     Vous pouvez aussi piocher directement la leçon qui vous intéresse.</p>
  <div class="tcards">{"".join(cards)}</div>
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
                + extra + "</article>"
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
</header>
<article class="prose">
{body_html}
</article>
{subs_html}
{code}
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

    def run(self) -> None:
        s = self.site
        s.scan_code()
        s.scan_pages()

        if DOCS.exists():
            for child in DOCS.iterdir():
                if child.name == "assets":
                    for a in child.iterdir():
                        if a.name != "images":
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
        self.build_annexes()
        self.build_404()

        # Chargé par une balise <script> plutôt que par fetch() : la recherche
        # fonctionne ainsi même quand le site est ouvert depuis le disque (file://).
        (DOCS / "assets" / "search-index.js").write_text(
            "window.GENAI_INDEX="
            + json.dumps(s.search, ensure_ascii=False, separators=(",", ":"))
            + ";\n",
            encoding="utf-8",
        )

        pages = len(list(DOCS.rglob("index.html"))) + 1
        print(f"✓ {pages} pages HTML générées dans docs/ "
              f"({len(s.order)} leçons, {sum(len(v) for v in s.subpages.values())} pages annexes de leçon, "
              f"{len(s.search)} entrées de recherche)")
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
