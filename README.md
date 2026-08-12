# Softscar Learning Content

Contenu pour la formation de Softscar.

## 🧠 IA Générative — cours, ateliers et prompts, en français

Ce dépôt héberge un **site statique** qui réunit trois ressources open source, réorganisées
pour être suivies comme un vrai parcours d'apprentissage :

| | Source | Ce que c'est |
|---|---|---|
| 📘 **Apprendre** | [Generative AI for Beginners](https://github.com/microsoft/generative-ai-for-beginners) (Microsoft) | 22 leçons en français, réparties en **7 parcours progressifs** |
| 🧪 **Construire** | [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | **139 applications** complètes, code inclus, en 17 catégories |
| 🔍 **Décortiquer** | [system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | Les prompts système de **40 outils** commerciaux, découpés et expliqués |

Le cours explique, les ateliers font construire, les prompts montrent ce que fait
l'industrie. **16 sujets transversaux** relient les trois : sur la page « RAG », on trouve au
même endroit les 2 leçons, les 31 ateliers et les 3 prompts qui en parlent.

| | |
|---|---|
| **Contenus** | 201 (22 leçons + 139 ateliers + 40 prompts système) |
| **Pages** | 343 pages HTML |
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

### Les prompts système ne sont pas déversés bruts

Un prompt système de 10 000 mots affiché d'un bloc n'apprend rien à personne. Chaque fiche
est donc construite ainsi :

- **À quoi sert ce prompt** — son rôle, quand il est envoyé, ce qu'il produit ;
- **Ce que ce prompt apprend** — analyse rédigée, pour les outils les plus instructifs ;
- **Le réutiliser chez vous** — ce qui se transpose dans ses propres prompts, et ce qui ne se
  transpose pas parce que cela n'existe que dans ce produit ;
- **Constats mesurés** — longueur, mode de structuration, nombre d'outils et d'interdictions,
  calculés sur les fichiers eux-mêmes ;
- **Quel fichier, et où** — pour les 29 outils qui en publient plusieurs : un tableau
  fichier / surface du produit / modèle / taille, avec le fichier par lequel commencer ;
- **Le déroulé, étape par étape** — les sections rangées dans l'ordre où elles entrent en jeu
  (1 il apprend qui il est, 2 l'éditeur décrit votre machine, … 10 il rédige sa réponse), les
  sections liées regroupées, les étapes absentes sautées, et à part celles qui ne s'enchaînent
  avec rien. Un fichier qui contient les étapes 2 à 5 n'est pas un prompt mais **une requête
  entière enregistrée** — le site le signale, parce que ces parties-là ne se copient pas ;
- **L'ordre réel du fichier** — les sections telles qu'elles se suivent dans le texte, chacune
  expliquée en français quand son nom est répertorié, avec son numéro d'étape ;
- **Le texte, section par section** — intégral et intact, mais en blocs repliables et ancrés,
  avec un onglet par fichier et sa fiche de situation (surface, modèle, moment d'envoi) ;
- les **définitions d'outils** rendues lisibles, précédées de ce qu'il faut savoir pour les lire.

Une [page guide](docs/prompts-systeme/guide/) explique en amont ce qu'est un prompt système,
quand il est envoyé, ce qu'il change, ce qu'il coûte en jetons, les dix moments d'un échange,
ce que le produit remplit tout seul (`<attached_files>` est le trombone du champ de saisie),
comment se lit un `Tools.json`, et pourquoi un même outil publie plusieurs fichiers (versions successives, surfaces distinctes,
variantes par modèle, prompt + outils, ou simple découpage à l'import). Le glossaire
(`content/_prompt_sections.json`) décrit **54 types de section** et en reconnaît 68 variantes de
nommage ; `content/_prompt_files.json` situe les **103 fichiers** un par un. Une section qu'il
ne connaît pas garde son nom brut, sans commentaire inventé.

## Organisation du dépôt

```
content/                     sources et métadonnées — la vérité du site
  _meta.json                 parcours, titres FR, durées, vocabulaire des tags, sujets par leçon
  _topics.json               les 16 sujets transversaux et leurs mots-clés de détection
  _apps_meta.json            habillage FR des 17 catégories et 139 ateliers
  _prompts_meta.json         habillage FR des 40 outils : rôle, moment, résultat, analyse, réemploi
  _prompt_sections.json      glossaire des types de section et leur place dans le déroulé
  _prompt_files.json         les 103 fichiers situés : surface, modèle, moment, statut
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
