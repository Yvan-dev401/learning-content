# Attribution

## Origine du contenu

L'ensemble du contenu pédagogique publié dans `content/`, `code/` et `docs/` provient du
dépôt :

> **Generative AI for Beginners**
> https://github.com/microsoft/generative-ai-for-beginners
> © Microsoft Corporation — licence MIT

Plus précisément :

| Élément | Source dans le dépôt d'origine |
|---|---|
| Texte des 22 leçons et pages annexes | `translations/fr/**/*.md` (traduction française officielle, produite par [Co-op Translator](https://github.com/Azure/co-op-translator)) |
| Illustrations | `translated_images/fr/` et, en repli, les dossiers `images/` / `img/` de chaque leçon |
| Exemples de code et notebooks | dossiers `python/`, `typescript/`, `javascript/`, `js-githubmodels/`, `dotnet/`, `scripts/` de chaque leçon |
| Documents annexes | `translations/fr/docs/`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` |

La licence MIT d'origine est reproduite intégralement dans
[`LICENSE-UPSTREAM`](LICENSE-UPSTREAM), conformément à sa clause de conservation de la
notice de copyright.

## Ce qui a été ajouté ici

Ce dépôt n'apporte pas de contenu de cours : il apporte une **réorganisation et une mise en
forme**.

- Le regroupement des 22 leçons en 7 parcours progressifs (`content/_meta.json`), avec des
  titres et résumés français rédigés pour ce site, ainsi que des durées indicatives.
- Les scripts d'import, de génération et de vérification (`tools/`).
- Le design du site : `tools/assets/style.css`, `tools/assets/app.js`, et les gabarits HTML
  produits par `tools/build.py`.

Le texte des leçons n'a été ni réécrit, ni résumé, ni complété. Les seules modifications
appliquées au Markdown sont mécaniques et décrites dans le README : réécriture des chemins
d'images et des liens internes, retrait du paramètre de suivi `?WT.mc_id=`, et remplacement
de l'encart de traduction automatique par un lien vers la version d'origine — ce lien figure
au bas de chaque page du site.

## Traduction automatique

La version française du cours est générée automatiquement en amont par Co-op Translator.
Comme le rappelait l'avertissement d'origine : la traduction peut contenir des erreurs ou
des imprécisions, et **la version anglaise fait foi**. Chaque page du site renvoie vers le
fichier français d'origine et vers la leçon anglaise correspondante.

## Absence d'affiliation

Ce dépôt n'est ni affilié à Microsoft Corporation, ni approuvé ou soutenu par elle. Les
marques citées (Microsoft, Azure, OpenAI, Hugging Face, Mistral, Meta…) appartiennent à
leurs détenteurs respectifs.
