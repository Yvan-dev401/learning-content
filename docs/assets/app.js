/* IA Générative — le cours · comportements du site
   Sans dépendance : thème, sommaire mobile, recherche, progression, copie de code.
   L'index de recherche est chargé via une balise <script> (et non fetch) afin que
   la recherche fonctionne aussi quand le site est ouvert depuis le disque. */

(function () {
  "use strict";

  var BASE = document.body.getAttribute("data-base") || "";
  var THEME_KEY = "genai-theme";
  var PROGRESS_KEY = "genai-progress";

  function store(key, value) {
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (e) { /* stockage indisponible : on continue sans persistance */ }
  }
  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  /* ------------------------------------------------------------- thème */

  function currentTheme() {
    var explicit = document.documentElement.getAttribute("data-theme");
    if (explicit) return explicit;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  var themeBtn = document.querySelector(".topbar__theme");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store(THEME_KEY, next);
      themeBtn.setAttribute("title", next === "dark" ? "Passer au thème clair" : "Passer au thème sombre");
    });
  }

  /* La barre supérieure passe sur deux lignes en dessous de 900px : on mesure sa
     hauteur réelle plutôt que de la coder en dur, car sidebar, sommaire collant et
     `scroll-padding-top` s'alignent tous dessus. */

  var topbar = document.querySelector(".topbar");
  if (topbar) {
    var syncTopbar = function () {
      document.documentElement.style.setProperty(
        "--topbar-h", topbar.getBoundingClientRect().height + "px");
    };
    syncTopbar();
    window.addEventListener("resize", syncTopbar);
    if ("ResizeObserver" in window) new ResizeObserver(syncTopbar).observe(topbar);
  }

  /* ------------------------------------------------- sommaire mobile */

  var sidebar = document.querySelector(".sidebar");
  var menuBtn = document.querySelector(".topbar__menu");
  if (sidebar && menuBtn) {
    var backdrop = document.createElement("button");
    backdrop.className = "sidebar__backdrop";
    backdrop.setAttribute("aria-label", "Fermer le sommaire");
    document.body.appendChild(backdrop);

    var setNav = function (open) {
      sidebar.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    };
    menuBtn.addEventListener("click", function () { setNav(!sidebar.classList.contains("is-open")); });
    backdrop.addEventListener("click", function () { setNav(false); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) setNav(false);
    });
    sidebar.addEventListener("click", function (e) {
      if (e.target.closest("a")) setNav(false);
    });
  }

  /* ------------------------------------------------- copie des blocs */

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".codeblock__copy");
    if (!btn) return;
    var block = btn.closest(".codeblock");
    var code = block && block.querySelector("pre");
    if (!code) return;
    var done = function () {
      btn.textContent = "Copié";
      btn.classList.add("is-done");
      setTimeout(function () { btn.textContent = "Copier"; btn.classList.remove("is-done"); }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code.innerText).then(done, function () { btn.textContent = "Échec"; });
    } else {
      var sel = window.getSelection();
      var range = document.createRange();
      range.selectNodeContents(code);
      sel.removeAllRanges();
      sel.addRange(range);
      try { document.execCommand("copy"); done(); } catch (err) { btn.textContent = "Échec"; }
      sel.removeAllRanges();
    }
  });

  /* ------------------------------------------------------- onglets code */

  document.querySelectorAll(".codepanel").forEach(function (panel) {
    var buttons = panel.querySelectorAll(".tabs__btn");
    if (!buttons.length) return;
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var name = btn.getAttribute("data-tab");
        buttons.forEach(function (b) {
          b.setAttribute("aria-selected", b === btn ? "true" : "false");
        });
        panel.querySelectorAll(".tabs__panel").forEach(function (p) {
          p.hidden = p.getAttribute("data-tab") !== name;
        });
      });
    });
  });

  /* Un lien du cours peut viser un fichier de code précis : on ouvre l'onglet
     et le bloc correspondants avant de laisser le navigateur y sauter. */
  function revealTarget() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var panel = target.closest(".tabs__panel");
    if (panel) {
      var name = panel.getAttribute("data-tab");
      var root = panel.closest(".codepanel");
      root.querySelectorAll(".tabs__panel").forEach(function (p) {
        p.hidden = p.getAttribute("data-tab") !== name;
      });
      root.querySelectorAll(".tabs__btn").forEach(function (b) {
        b.setAttribute("aria-selected", b.getAttribute("data-tab") === name ? "true" : "false");
      });
    }
    var details = target.closest("details");
    while (details) {
      details.open = true;
      details = details.parentElement && details.parentElement.closest("details");
    }
    target.scrollIntoView({ block: "start" });
  }
  window.addEventListener("hashchange", revealTarget);
  revealTarget();

  /* --------------------------------------------------------- progression */

  function getProgress() {
    try { return JSON.parse(read(PROGRESS_KEY) || "{}") || {}; } catch (e) { return {}; }
  }
  function setProgress(p) { store(PROGRESS_KEY, JSON.stringify(p)); }

  function paintProgress() {
    var done = getProgress();
    document.querySelectorAll("[data-lesson]").forEach(function (el) {
      el.classList.toggle("is-done", !!done[el.getAttribute("data-lesson")]);
    });

    var toggle = document.querySelector("[data-lesson-toggle]");
    if (toggle) {
      var slug = toggle.getAttribute("data-lesson-toggle");
      var box = toggle.querySelector(".done__box");
      box.checked = !!done[slug];
      toggle.classList.toggle("is-done", box.checked);
    }

    document.querySelectorAll("[data-track-progress]").forEach(function (el) {
      var card = el.closest(".tcard");
      if (!card) return;
      var lessons = card.querySelectorAll(".tcard__lesson");
      var n = 0;
      lessons.forEach(function (li) { if (done[li.getAttribute("data-lesson")]) n++; });
      el.textContent = n ? n + "/" + lessons.length + " ✓" : "";
    });

    var global = document.querySelector("[data-global-progress]");
    if (global) {
      var all = document.querySelectorAll(".tcard__lesson");
      var count = 0;
      all.forEach(function (li) { if (done[li.getAttribute("data-lesson")]) count++; });
      var pct = all.length ? Math.round((count / all.length) * 100) : 0;
      global.querySelector(".progress__fill").style.width = pct + "%";
      global.querySelector(".progress__text").textContent = count + " / " + all.length;
    }
  }

  var lessonToggle = document.querySelector("[data-lesson-toggle]");
  if (lessonToggle) {
    lessonToggle.querySelector(".done__box").addEventListener("change", function (e) {
      var p = getProgress();
      var slug = lessonToggle.getAttribute("data-lesson-toggle");
      if (e.target.checked) p[slug] = true; else delete p[slug];
      setProgress(p);
      paintProgress();
    });
  }

  var resetBtn = document.querySelector(".progress__reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      if (!window.confirm("Réinitialiser votre progression ?")) return;
      store(PROGRESS_KEY, null);
      paintProgress();
    });
  }

  paintProgress();

  /* ------------------------------------------------------------ recherche */

  var input = document.querySelector(".search__input");
  var results = document.querySelector(".search__results");

  function fold(s) {
    return s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  var indexState = "idle";
  var pending = [];
  function loadIndex(then) {
    if (indexState === "ready") return then();
    if (indexState === "error") return;
    pending.push(then);
    if (indexState === "loading") return;
    indexState = "loading";
    var s = document.createElement("script");
    s.src = BASE + "assets/search-index.js";
    s.onload = function () {
      indexState = "ready";
      (window.GENAI_INDEX || []).forEach(function (e) {
        e._t = fold(e.t);
        e._c = fold(e.c || "");
        e._b = fold((e.s || "") + " " + (e.h || []).join(" ") + " " + (e.b || ""));
      });
      var queued = pending.splice(0);
      queued.forEach(function (cb) { cb(); });
    };
    s.onerror = function () {
      indexState = "error";
      pending.length = 0;
      results.innerHTML = '<p class="search__empty">Index de recherche indisponible.</p>';
      results.hidden = false;
    };
    document.head.appendChild(s);
  }

  function snippet(entry, terms) {
    var body = entry.b || entry.s || "";
    var lower = fold(body);
    var at = -1;
    for (var i = 0; i < terms.length && at < 0; i++) at = lower.indexOf(terms[i]);
    if (at < 0) return (entry.s || body).slice(0, 130);
    var start = Math.max(0, at - 55);
    var text = (start > 0 ? "…" : "") + body.slice(start, start + 150) + "…";
    return text;
  }

  function mark(text, terms) {
    var out = text.replace(/[&<>]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c];
    });
    terms.forEach(function (t) {
      if (t.length < 2) return;
      var re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }

  function search(query) {
    var terms = fold(query).split(/\s+/).filter(function (t) { return t.length > 1; });
    if (!terms.length) return [];
    var hits = [];
    (window.GENAI_INDEX || []).forEach(function (e) {
      var score = 0;
      var all = true;
      terms.forEach(function (t) {
        var s = 0;
        if (e._t.indexOf(t) >= 0) s += 12;
        if (e._c.indexOf(t) >= 0) s += 4;
        var n = e._b.split(t).length - 1;
        if (n) s += Math.min(n, 6);
        if (!s) all = false;
        score += s;
      });
      if (all && score) hits.push({ e: e, score: score });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    return hits.slice(0, 12).map(function (h) { return h.e; });
  }

  function render(query) {
    var terms = fold(query).split(/\s+/).filter(function (t) { return t.length > 1; });
    var hits = search(query);
    if (!hits.length) {
      results.innerHTML = '<p class="search__empty">Aucun résultat pour « ' +
        query.replace(/[&<>]/g, "") + ' ».</p>';
      results.hidden = false;
      return;
    }
    results.innerHTML = hits.map(function (e) {
      return '<a class="search__hit" href="' + BASE + e.u + '">' +
        '<span class="search__hit-kind">' + e.k + (e.c ? " · " + e.c : "") + "</span>" +
        '<span class="search__hit-title">' + mark(e.t, terms) + "</span>" +
        '<span class="search__hit-snippet">' + mark(snippet(e, terms), terms) + "</span></a>";
    }).join("");
    results.hidden = false;
  }

  if (input && results) {
    var timer = null;
    var run = function () {
      var q = input.value.trim();
      if (q.length < 2) { results.hidden = true; return; }
      loadIndex(function () { render(q); });
    };
    input.addEventListener("focus", function () { loadIndex(function () {}); });
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(run, 120);
    });
    input.addEventListener("keydown", function (e) {
      var hits = Array.prototype.slice.call(results.querySelectorAll(".search__hit"));
      if (!hits.length) return;
      var i = hits.findIndex(function (h) { return h.classList.contains("is-active"); });
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (i >= 0) hits[i].classList.remove("is-active");
        var next = e.key === "ArrowDown" ? (i + 1) % hits.length : (i <= 0 ? hits.length - 1 : i - 1);
        hits[next].classList.add("is-active");
        hits[next].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && i >= 0) {
        e.preventDefault();
        window.location.href = hits[i].getAttribute("href");
      } else if (e.key === "Escape") {
        results.hidden = true;
        input.blur();
      }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".search")) results.hidden = true;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== input &&
          !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
        e.preventDefault();
        input.focus();
      }
    });
  }

  /* ------------------------------------------------- sommaire de la page */

  var tocLinks = document.querySelectorAll(".toc__item a");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    tocLinks.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a.parentElement; });
    var targets = Object.keys(byId)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    var visible = new Set();
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) visible.add(entry.target.id);
        else visible.delete(entry.target.id);
      });
      var first = targets.find(function (t) { return visible.has(t.id); });
      Object.keys(byId).forEach(function (id) {
        byId[id].classList.toggle("is-current", !!first && id === first.id);
      });
    }, { rootMargin: "-72px 0px -70% 0px" });
    targets.forEach(function (t) { observer.observe(t); });
  }
})();
