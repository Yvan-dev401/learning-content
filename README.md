# Softscar Learning Content

Contenu pour la formation de Softscar.

## 🧠 IA Générative — cours, ateliers et prompts, en français

Ce dépôt héberge un **site statique** qui réunit trois ressources open source, réorganisées
pour être suivies comme un vrai parcours d'apprentissage :

| | Source | Ce que c'est |
|---|---|---|
| 📘 **Apprendre** | [Generative AI for Beginners](https://github.com/microsoft/generative-ai-for-beginners) (Microsoft) | 22 leçons en français, réparties en **7 parcours progressifs** |
| 🧪 **Construire** | [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | **139 applications** complètes, code inclus, en 17 catégories |
| 🔍 **Décortiquer** | [system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | Les prompts système de **40 outils** commerciaux, analysés |

Le cours explique, les ateliers font construire, les prompts montrent ce que fait
l'industrie. **16 sujets transversaux** relient les trois : sur la page « RAG », on trouve au
même endroit les 2 leçons, les 31 ateliers et les 3 prompts qui en parlent.

| | |
|---|---|
| **Contenus** | 201 (22 leçons + 139 ateliers + 40 prompts système) |
| **Pages** | 342 pages HTML |
| **Code** | ~1 300 fichiers d'exemple, lisibles et téléchargeables |
| **Prompts** | 103 fichiers, 2,3 M caractères, 185 définitions d'outils |
| **Langue** | français (les textes techniques restent en langue d'origine) |
| **Dépendances à l'exécution** | aucune |

### Consulter le site

**En ligne (GitHub Pages)** : `https://<votre-compte>.github.io/learning-content/`

**En local** — aucune installation : ouvrez `docs/index.html`. Tout fonctionne depuis le
disque, y compris la recherche et les filtres.

```bash
python3 -m http.server 8000 -d docs
```

### Comment le site est organisé

Trois portes d'entrée sur l'accueil, et **quatre façons de naviguer** selon ce que vous
cherchez :

- **Par parcours** — le chemin pédagogique du cours, dans l'ordre.
- **Par sujet** (`/sujets/`) — les 16 thèmes, chacun croisant les trois familles.
- **Par catalogue** (`/catalogue/`) — les 201 contenus, filtrables en combinant
  **type × sujet × tags**. L'URL obtenue est partageable.
- **Par recherche** — plein texte sur tout le site (raccourci `/`).

Plus, sur chaque page : les **tags** (⭐ incontournable, 🟢 débutant, 💳 compte payant…), un
bloc **« Sur le même sujet »** qui renvoie vers les autres familles, les **alternatives
gratuites** aux services facturés, et le suivi de progression.

## Organisation du dépôt

```
content/                     sources et métadonnées — la vérité du site
  _meta.json                 parcours, titres FR, durées, vocabulaire des tags, sujets par leçon
  _topics.json               les 16 sujets transversaux et leurs mots-clés de détection
  _apps_meta.json            habillage FR des 17 catégories et 139 ateliers
  _prompts_meta.json         habillage FR des 40 outils : « ce qu'on en retient »
  _services.json             services payants, détection, alternatives gratuites
  _ingest.json, _apps.json, _prompts.json    manifestes produits par l'ingestion
  <leçon>/, _annexes/        Markdown français du cours
  ateliers/<cat>/<projet>/   README des ateliers (anglais, liens réécrits)
docs/                        ★ le site généré — c'est ce que GitHub Pages publie
  assets/code/               code des leçons et ateliers (copie unique, téléchargeable)
  assets/prompts-systeme/    prompts bruts, reproduits à l'octet près
  assets/images/             images (copie unique)
tools/
  common.py                  mécaniques d'ingestion partagées
  ingest.py / ingest_apps.py / ingest_prompts.py     une par source
  build.py                   content/ → docs/
  check_links.py             liens, ancres, couverture, cohérence tags/sujets/services
  assets/                    style.css et app.js du site
```

`docs/` est **commité** : le site se consulte sans rien construire. On ne l'édite jamais à la
main — on modifie `content/` ou `tools/`, puis on régénère.

### Ajouter une quatrième source

C'est ce que la structure interne prépare. Tout ce qui donne une page est un **élément**
(`Site.register_items` dans `tools/build.py`) : identifiant, famille, titre, résumé, tags,
sujets, URL. Les cartes, le catalogue, les pages de sujet, les liens transversaux et la
recherche ne connaissent que cette forme. Une nouvelle source demande donc :

1. un `tools/ingest_<source>.py` qui produise un manifeste dans `content/` ;
2. un adaptateur d'une vingtaine de lignes dans `register_items()` ;
3. une entrée dans `COLLECTIONS` (`tools/build.py`) ;
4. un fichier de métadonnées françaises.

Rien à toucher dans les pages transversales : elles suivent.

## Régénérer le site

```bash
pip install -r tools/requirements.txt

python3 tools/ingest.py          # cours Microsoft      (~800 Mo temporaires)
python3 tools/ingest_apps.py     # ateliers             (~160 Mo temporaires)
python3 tools/ingest_prompts.py  # prompts système      (~4 Mo temporaires)
python3 tools/build.py           # régénère docs/
python3 tools/check_links.py     # 0 lien cassé, couverture des trois familles
```

Les quatre étapes sont **idempotentes** : les relancer produit exactement le même résultat.
Chaque script d'ingestion n'efface que ce qu'il produit, et `build.py` n'efface d'`assets/`
que ce qu'il génère lui-même — une source n'écrase jamais le travail d'une autre.

Pour réutiliser un clone existant : `--upstream /chemin/vers/le/depot`.

**Changer la présentation** — parcours, sujets, titres, tags, alternatives — se fait dans les
fichiers `content/_*.json`, puis `python3 tools/build.py` suffit.

## Ce qui a été retouché par rapport aux sources

Les contenus sont repris **intégralement, sans réécriture ni résumé**. Seule la mise en forme
est adaptée : chemins d'images réécrits, liens internes redirigés, paramètres de suivi
retirés. **Les prompts système sont reproduits à l'octet près**, sans aucune modification.
Le détail figure dans [`ATTRIBUTION.md`](ATTRIBUTION.md).

Ne sont pas embarqués : les fichiers de plus de 1 Mo, les images de plus de 2 Mo et les
binaires — chaque page concernée les liste et renvoie vers l'original.

## Licences et attribution

**Ce dépôt est une compilation à licences mixtes** — MIT, Apache-2.0 et GPL-3.0 selon la
partie. Le tableau des chemins et des licences correspondantes est dans
[`ATTRIBUTION.md`](ATTRIBUTION.md), avec les fichiers de licence
[`LICENSE-UPSTREAM`](LICENSE-UPSTREAM),
[`LICENSE-UPSTREAM-APPS`](LICENSE-UPSTREAM-APPS) et
[`LICENSE-UPSTREAM-PROMPTS`](LICENSE-UPSTREAM-PROMPTS).

> ⚠️ **Au sujet des prompts système.** Ce sont des textes propriétaires extraits de produits
> commerciaux par des tiers : ni officiels, ni vérifiables, et souvent périmés. Ils sont repris
> à des fins d'étude ; toute demande de retrait d'un éditeur serait honorée. L'avertissement
> figure sur chaque page concernée.

Ce dépôt n'est affilié à aucune des sources ni à aucun des éditeurs cités.
