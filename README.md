# Softscar Learning Content

Contenu pour la formation de Softscar.

## 🧠 IA Générative — cours et ateliers, en français

Ce dépôt héberge un **site statique** qui réunit deux ressources open source majeures,
réorganisées pour être suivies comme un vrai parcours d'apprentissage :

- **le cours** [*Generative AI for Beginners*](https://github.com/microsoft/generative-ai-for-beginners)
  de Microsoft, dans sa traduction française officielle — 22 leçons réparties en
  **7 parcours progressifs** au lieu des dossiers à plat d'origine ;
- **les ateliers** [*awesome-llm-apps*](https://github.com/Shubhamsaboo/awesome-llm-apps) —
  **139 applications d'IA complètes**, code inclus, classées en 17 catégories.

Le cours explique, les ateliers font construire. Des **tags** indiquent où investir son
temps, et chaque page listant un service payant propose ses **alternatives gratuites**.

| | |
|---|---|
| **Leçons** | 22, en 7 parcours |
| **Ateliers** | 139, en 17 catégories (dont 24 sur le RAG) |
| **Pages** | 283 pages HTML |
| **Code** | ~1 300 fichiers d'exemple, lisibles et téléchargeables |
| **Langue** | français (les README techniques des ateliers restent en anglais) |
| **Dépendances à l'exécution** | aucune |

### Consulter le site

**En ligne (GitHub Pages)** : `https://<votre-compte>.github.io/learning-content/`

> Si Pages n'est pas encore actif : **Settings → Pages → Source: Deploy from a branch →
> branche `main`, dossier `/docs`**, puis *Save*.

**En local** — aucune installation : ouvrez `docs/index.html` dans un navigateur. Tout
fonctionne depuis le disque, y compris la recherche et les filtres.

```bash
python3 -m http.server 8000 -d docs   # ou simplement double-cliquer sur docs/index.html
```

### Ce que propose le site

- **7 parcours + 17 catégories d'ateliers**, avec navigation croisée : chaque leçon renvoie
  vers les ateliers qui la mettent en pratique, et réciproquement.
- **Tags filtrables** sur quatre axes — intérêt (⭐ incontournable, 🔥 très demandé…),
  difficulté, coût, nature. Le filtrage est cumulable et l'URL obtenue est partageable.
- **Alternatives gratuites** : chaque leçon ou atelier exigeant un service facturé affiche
  en tête par quoi le remplacer, et une [page de synthèse](docs/annexes/alternatives-gratuites/)
  récapitule tout.
- **Recherche plein texte** sur l'ensemble du site (raccourci : `/`).
- **Suivi de progression** : cochez leçons et ateliers terminés, l'état reste dans votre
  navigateur.
- **Thème clair / sombre**, sommaire par page, navigation précédent/suivant, responsive,
  accessible au clavier, imprimable.

## Organisation du dépôt

```
content/                     sources Markdown et métadonnées — la vérité du site
  _meta.json                 cours : parcours, titres FR, durées, vocabulaire des tags
  _apps_meta.json            ateliers : titres et résumés FR des 17 catégories et 139 projets
  _services.json             services payants, motifs de détection, alternatives gratuites
  _ingest.json, _apps.json   manifestes produits par l'ingestion
  <leçon>/, _annexes/        Markdown français du cours
  ateliers/<cat>/<projet>/   README des ateliers (anglais, liens réécrits)
docs/                        ★ le site généré — c'est ce que GitHub Pages publie
  assets/code/               code des leçons et des ateliers (copie unique, téléchargeable)
  assets/images/             images (copie unique)
tools/
  common.py                  mécaniques d'ingestion partagées
  ingest.py                  importe le cours Microsoft
  ingest_apps.py             importe les ateliers awesome-llm-apps
  build.py                   content/ → docs/
  check_links.py             liens, ancres, couverture, cohérence des tags et services
  assets/                    style.css et app.js du site
```

`docs/` est **commité** : le site se consulte sans rien construire. On ne l'édite jamais à
la main — on modifie `content/` ou `tools/`, puis on régénère. Code et images n'existent
qu'à un seul endroit, sous `docs/assets/` : les dupliquer à la racine coûterait une
vingtaine de mégaoctets pour rien.

## Régénérer le site

```bash
pip install -r tools/requirements.txt

python3 tools/ingest.py        # cours Microsoft (clone partiel, ~800 Mo temporaires)
python3 tools/ingest_apps.py   # ateliers awesome-llm-apps (~160 Mo temporaires)
python3 tools/build.py         # régénère docs/
python3 tools/check_links.py   # contrôle : 0 lien cassé, 22 leçons, 139 ateliers
```

Les trois étapes sont idempotentes : les relancer produit exactement le même résultat.
Pour réutiliser un clone existant plutôt que d'en refaire un :

```bash
python3 tools/ingest.py      --upstream /chemin/vers/generative-ai-for-beginners
python3 tools/ingest_apps.py --upstream /chemin/vers/awesome-llm-apps
```

**Changer uniquement la présentation** — regroupement en parcours, titres français, tags,
alternatives gratuites — se fait dans `content/_meta.json`, `content/_apps_meta.json` ou
`content/_services.json`, puis `python3 tools/build.py` suffit.

### Ajouter un service et ses alternatives

Une entrée dans `content/_services.json` suffit : les motifs de `detect` sont cherchés dans
le Markdown, le code et les `requirements.txt` de chaque page. De là découlent, sans autre
intervention, l'encadré sur les pages concernées, le tag de coût, et la ligne dans la page
de synthèse. Le tag de coût n'est jamais écrit à la main — il ne peut donc pas mentir.

## Ce qui a été retouché par rapport aux sources

Les contenus sont repris **intégralement, sans réécriture ni résumé**. Seule la mise en
forme est adaptée : chemins d'images réécrits, liens internes redirigés vers les pages du
site, paramètre de suivi `?WT.mc_id=…` retiré, et encart de traduction automatique remplacé
par un lien vers l'original. Le détail figure dans [`ATTRIBUTION.md`](ATTRIBUTION.md).

Ne sont pas embarqués : les fichiers de plus de 1 Mo, les images de plus de 2 Mo, les
binaires et les jeux de données volumineux — chaque page concernée les liste et renvoie
vers le dépôt d'origine. Trois éléments manquent parce qu'ils sont absents des dépôts
sources eux-mêmes (un fichier vide et deux images du document sur le perceptron).

## Licences et attribution

Deux sources, deux licences, toutes deux permissives :

- **Le cours** : [microsoft/generative-ai-for-beginners](https://github.com/microsoft/generative-ai-for-beginners),
  licence **MIT** — voir [`LICENSE-UPSTREAM`](LICENSE-UPSTREAM).
- **Les ateliers** : [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps),
  licence **Apache-2.0** — voir [`LICENSE-UPSTREAM-APPS`](LICENSE-UPSTREAM-APPS).

Le détail de ce qui vient d'où, et des modifications apportées, est dans
[`ATTRIBUTION.md`](ATTRIBUTION.md). Chaque page du site renvoie vers sa source exacte.

Ce dépôt n'est affilié ni à Microsoft, ni aux auteurs d'awesome-llm-apps.
