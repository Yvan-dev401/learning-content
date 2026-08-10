# Attribution

Ce dépôt réunit le contenu de deux projets open source distincts, sous deux licences
différentes. Aucun des deux n'est affilié à ce dépôt.

| Section du site | Dépôt d'origine | Licence |
|---|---|---|
| Le cours (22 leçons, parcours 0 à 6) | [microsoft/generative-ai-for-beginners](https://github.com/microsoft/generative-ai-for-beginners) | MIT — [`LICENSE-UPSTREAM`](LICENSE-UPSTREAM) |
| Les ateliers pratiques (139 projets) | [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | Apache-2.0 — [`LICENSE-UPSTREAM-APPS`](LICENSE-UPSTREAM-APPS) |

---

# Le cours — Generative AI for Beginners

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

---

# Les ateliers — awesome-llm-apps

## Origine du contenu

Les 139 ateliers pratiques publiés dans `content/ateliers/`, `docs/ateliers/` et
`docs/assets/code/ateliers/` proviennent du dépôt :

> **Awesome LLM Apps**
> https://github.com/Shubhamsaboo/awesome-llm-apps
> © les contributeurs du projet — licence **Apache License 2.0**

La licence complète est reproduite dans
[`LICENSE-UPSTREAM-APPS`](LICENSE-UPSTREAM-APPS).

| Élément | Source dans le dépôt d'origine |
|---|---|
| README de chaque projet, en anglais | `<catégorie>/<projet>/README.md` et sous-dossiers |
| Code, dépendances, exemples de configuration | fichiers `.py`, `.ts`, `.js`, `requirements.txt`, `.env.example`… de chaque projet |
| Illustrations | images référencées par les README |

## Modifications apportées (clause 4b de la licence Apache-2.0)

La licence Apache-2.0 demande d'indiquer de façon visible les fichiers modifiés. Les
fichiers repris ici l'ont été **sans changement de fond** ; les seules retouches sont
mécaniques, et appliquées par `tools/ingest_apps.py` :

- **README** : les chemins d'images et les liens relatifs sont réécrits pour pointer vers
  les pages de ce site quand la cible y existe, et vers le dépôt d'origine sinon. Aucune
  phrase n'est ajoutée, supprimée ni traduite.
- **Code** : copié tel quel, à l'octet près. Les fichiers binaires, les images et les
  fichiers de plus de 1 Mo ne sont pas embarqués — chaque page d'atelier les liste et
  renvoie vers l'original.
- Chaque page d'atelier indique sa source exacte et rappelle ces retouches en pied de page.

## Le README d'origine n'est pas traduit

Les instructions techniques des ateliers restent en anglais, volontairement : traduire des
commandes, des noms de paquets et des noms de variables introduirait des erreurs
d'exécution. Ce qui est en français, c'est l'habillage rédigé pour ce site — titre, résumé,
tags, prérequis et alternatives gratuites.

## Ce qui a été ajouté ici

- L'habillage français des 17 catégories et des 139 projets (`content/_apps_meta.json`).
- Le système de tags (`content/_meta.json`, clé `tags`) et son filtrage.
- La table des services et de leurs alternatives gratuites (`content/_services.json`),
  ainsi que la détection automatique qui en découle.
- Les scripts `tools/ingest_apps.py`, `tools/common.py`, et les pages générées.

Les tags d'intérêt, de difficulté et de nature sont **un avis pédagogique**, propre à ce
dépôt : ils n'engagent ni Microsoft, ni les auteurs d'awesome-llm-apps. Le tag de coût,
lui, est calculé à partir des services que chaque page exige réellement.

## Absence d'affiliation

Ce dépôt n'est ni affilié aux auteurs d'awesome-llm-apps, ni approuvé par eux. Les marques
et services cités (OpenAI, Anthropic, Google, Qdrant, Tavily, Firecrawl, ElevenLabs…)
appartiennent à leurs détenteurs respectifs. Les indications de tarification et de paliers
gratuits reflètent la situation constatée à la rédaction et peuvent changer : vérifiez
toujours sur le site du service avant de vous engager.
