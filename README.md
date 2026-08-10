# Softscar Learning Content

Contenu pour la formation de Softscar.

## 🧠 IA Générative — le cours (22 leçons, en français)

Ce dépôt héberge un **site statique** qui reprend l'intégralité du cours
[*Generative AI for Beginners*](https://github.com/microsoft/generative-ai-for-beginners)
de Microsoft, dans sa **traduction française officielle**, réorganisé en **7 parcours
progressifs** au lieu des 22 dossiers à plat du dépôt d'origine.

Chaque leçon contient le cours complet, ses illustrations, et **tous les exemples de code**
(Python, TypeScript, JavaScript, .NET) affichés avec coloration syntaxique et téléchargeables.
Les notebooks Jupyter sont rendus cellule par cellule.

| | |
|---|---|
| **Leçons** | 22, réparties en 7 parcours |
| **Pages** | 45 pages HTML (leçons, pages annexes, parcours, annexes) |
| **Code** | 104 fichiers d'exemple |
| **Langue** | français |
| **Dépendances à l'exécution** | aucune |

### Consulter le site

**En ligne (GitHub Pages)** — une fois Pages activé sur ce dépôt :
`https://<votre-compte>.github.io/Softscar-learning-content/`

> Pour l'activer : **Settings → Pages → Source: Deploy from a branch →
> branche `main`, dossier `/docs`**, puis *Save*.

**En local** — aucune installation nécessaire : ouvrez `docs/index.html` dans un navigateur.
Le site fonctionne intégralement depuis le disque, recherche comprise.

Pour le servir sur `localhost` :

```bash
python3 -m http.server 8000 -d docs
# puis http://localhost:8000
```

### Ce que propose le site

- **7 parcours progressifs**, de la mise en place de l'environnement aux familles de modèles.
- **Recherche plein texte** sur l'ensemble du cours (raccourci : `/`).
- **Suivi de progression** : cochez les leçons terminées, l'état reste dans votre navigateur.
- **Thème clair / sombre**, suit le réglage du système et se bascule manuellement.
- **Sommaire par page**, navigation précédent/suivant, liens vers la version d'origine.
- Responsive, accessible au clavier, et imprimable.

## Organisation du dépôt

```
content/           Markdown français nettoyé — la source de vérité
  _meta.json       titres, parcours, durées, ordre des leçons
  _ingest.json     manifeste produit par l'import
code/              exemples de code copiés depuis le dépôt d'origine
docs/              ★ le site généré (c'est ce que GitHub Pages publie)
tools/
  ingest.py        importe et nettoie le contenu depuis le dépôt Microsoft
  build.py         content/ + code/ → docs/
  check_links.py   vérifie liens, ancres, images et complétude
  assets/          style.css et app.js du site
  requirements.txt dépendances de génération
```

`docs/` est **commité** : le site est consultable sans rien construire. On ne le modifie
jamais à la main — on édite `content/` ou `tools/`, puis on régénère.

## Régénérer le site

```bash
pip install -r tools/requirements.txt

python3 tools/ingest.py       # importe depuis GitHub (clone partiel, ~800 Mo temporaires)
python3 tools/build.py        # régénère docs/
python3 tools/check_links.py  # contrôle : 0 lien cassé, 22 leçons publiées
```

`ingest.py` clone le dépôt source en *sparse checkout* (seules la traduction française et
ses images sont récupérées, pas les 50+ autres langues). Pour réutiliser un clone existant :

```bash
python3 tools/ingest.py --upstream /chemin/vers/generative-ai-for-beginners
```

Modifier uniquement la présentation (titres français, regroupement en parcours, durées) se
fait dans `content/_meta.json`, puis `python3 tools/build.py` suffit.

## Ce qui a été retouché par rapport à la source

Le texte des leçons est repris **intégralement, sans réécriture ni résumé**. Seule la mise
en forme a été adaptée :

- chemins d'images réécrits (`../../../translated_images/fr/nom.<hash>.webp` → `assets/images/nom.webp`),
  avec repli sur l'image anglaise quand la variante traduite n'existe pas ;
- liens entre leçons, pages annexes et fichiers de code redirigés vers les pages du site ;
- paramètre de suivi `?WT.mc_id=…` retiré des liens ;
- encart automatique de Co-op Translator remplacé par un lien vers la version d'origine.

Trois éléments restent absents, faute d'exister dans le dépôt source :
`10-building-low-code-ai-applications/assignment.md` (fichier vide en amont) et deux images
du document sur le perceptron. Les fichiers de plus de 1 Mo (index d'embeddings de 48 Mo,
images générées) ne sont pas embarqués ; chaque leçon concernée renvoie vers le dépôt d'origine.

## Licence et attribution

Le contenu pédagogique et les exemples de code proviennent de
[microsoft/generative-ai-for-beginners](https://github.com/microsoft/generative-ai-for-beginners),
publié sous **licence MIT** par Microsoft Corporation. La licence d'origine est reproduite
dans [`LICENSE-UPSTREAM`](LICENSE-UPSTREAM) et les détails d'attribution dans
[`ATTRIBUTION.md`](ATTRIBUTION.md).

Ce dépôt n'est ni affilié à Microsoft ni approuvé par Microsoft.
