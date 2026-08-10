# Sécuriser vos applications d'IA générative

[![Sécuriser vos applications d'IA générative](@img/13-lesson-banner.webp)](https://youtu.be/m0vXwsx5DNg?si=TYkr936GMKz15K0L)

## Introduction

Cette leçon couvrira :

- La sécurité dans le contexte des systèmes d'IA.
- Les risques et menaces courants pour les systèmes d'IA.
- Les méthodes et considérations pour sécuriser les systèmes d'IA.

## Objectifs d'apprentissage

Après avoir terminé cette leçon, vous comprendrez :

- Les menaces et risques pour les systèmes d'IA.
- Les méthodes et pratiques courantes pour sécuriser les systèmes d'IA.
- Comment la mise en œuvre de tests de sécurité peut prévenir des résultats inattendus et la perte de confiance des utilisateurs.

## Que signifie la sécurité dans le contexte de l'IA générative ?

Alors que les technologies d'Intelligence Artificielle (IA) et d'Apprentissage Automatique (ML) façonnent de plus en plus nos vies, il est essentiel de protéger non seulement les données des clients, mais aussi les systèmes d'IA eux-mêmes. L'IA/ML est de plus en plus utilisée pour soutenir des processus décisionnels de grande valeur dans des industries où une mauvaise décision peut entraîner des conséquences graves.

Voici les points clés à considérer :

- **Impact de l'IA/ML** : L'IA/ML ont des impacts significatifs sur la vie quotidienne et, en tant que tels, leur protection est devenue essentielle.
- **Défis de sécurité** : L'impact de l'IA/ML nécessite une attention particulière pour répondre au besoin de protéger les produits basés sur l'IA contre des attaques sophistiquées, qu'elles proviennent de trolls ou de groupes organisés.
- **Problèmes stratégiques** : L'industrie technologique doit aborder de manière proactive les défis stratégiques pour garantir la sécurité des clients et la protection des données à long terme.

De plus, les modèles d'apprentissage automatique sont largement incapables de distinguer les entrées malveillantes des données anormales bénignes. Une source importante de données d'entraînement provient de jeux de données publics non modérés et non vérifiés, ouverts aux contributions de tiers. Les attaquants n'ont pas besoin de compromettre les jeux de données lorsqu'ils peuvent y contribuer librement. Avec le temps, des données malveillantes à faible confiance deviennent des données de haute confiance si leur structure/format reste correct.

C'est pourquoi il est crucial de garantir l'intégrité et la protection des bases de données que vos modèles utilisent pour prendre des décisions.

## Comprendre les menaces et risques liés à l'IA

En ce qui concerne l'IA et les systèmes associés, l'empoisonnement des données est aujourd'hui la menace de sécurité la plus importante. L'empoisonnement des données se produit lorsque quelqu'un modifie intentionnellement les informations utilisées pour entraîner une IA, ce qui la conduit à commettre des erreurs. Cela est dû à l'absence de méthodes standardisées de détection et de mitigation, combinée à notre dépendance à des jeux de données publics non vérifiés ou non modérés pour l'entraînement. Pour maintenir l'intégrité des données et éviter un processus d'entraînement défectueux, il est crucial de suivre l'origine et la provenance de vos données. Sinon, l'adage "garbage in, garbage out" reste vrai, entraînant une performance compromise du modèle.

Voici des exemples de la manière dont l'empoisonnement des données peut affecter vos modèles :

1. **Renversement des étiquettes** : Dans une tâche de classification binaire, un adversaire modifie intentionnellement les étiquettes d'un petit sous-ensemble de données d'entraînement. Par exemple, des échantillons bénins sont étiquetés comme malveillants, ce qui conduit le modèle à apprendre des associations incorrectes.\
   **Exemple** : Un filtre anti-spam classant à tort des courriels légitimes comme spam en raison d'étiquettes manipulées.
2. **Empoisonnement des caractéristiques** : Un attaquant modifie subtilement les caractéristiques des données d'entraînement pour introduire des biais ou induire le modèle en erreur.\
   **Exemple** : Ajouter des mots-clés non pertinents aux descriptions de produits pour manipuler les systèmes de recommandation.
3. **Injection de données** : Injecter des données malveillantes dans l'ensemble d'entraînement pour influencer le comportement du modèle.\
   **Exemple** : Introduire de fausses critiques d'utilisateurs pour fausser les résultats d'analyse de sentiment.
4. **Attaques par porte dérobée** : Un adversaire insère un motif caché (porte dérobée) dans les données d'entraînement. Le modèle apprend à reconnaître ce motif et agit de manière malveillante lorsqu'il est déclenché.\
   **Exemple** : Un système de reconnaissance faciale entraîné avec des images contenant des portes dérobées qui identifie à tort une personne spécifique.

La MITRE Corporation a créé [ATLAS (Adversarial Threat Landscape for Artificial-Intelligence Systems)](https://atlas.mitre.org/), une base de connaissances sur les tactiques et techniques utilisées par les adversaires dans des attaques réelles contre les systèmes d'IA.

> Il existe un nombre croissant de vulnérabilités dans les systèmes activés par l'IA, car l'intégration de l'IA augmente la surface d'attaque des systèmes existants au-delà de celles des cyberattaques traditionnelles. Nous avons développé ATLAS pour sensibiliser à ces vulnérabilités uniques et en évolution, alors que la communauté mondiale intègre de plus en plus l'IA dans divers systèmes. ATLAS est basé sur le cadre MITRE ATT&CK® et ses tactiques, techniques et procédures (TTP) sont complémentaires à celles d'ATT&CK.

Tout comme le cadre MITRE ATT&CK®, largement utilisé en cybersécurité traditionnelle pour planifier des scénarios avancés d'émulation de menaces, ATLAS fournit un ensemble de TTP facilement consultables qui peuvent aider à mieux comprendre et se préparer à défendre contre les attaques émergentes.

De plus, l'Open Web Application Security Project (OWASP) a créé une "[liste des 10 principales vulnérabilités](https://llmtop10.com/)" les plus critiques trouvées dans les applications utilisant des LLM. La liste met en évidence les risques de menaces telles que l'empoisonnement des données mentionné précédemment, ainsi que d'autres comme :

- **Injection de prompts** : une technique où les attaquants manipulent un modèle de langage large (LLM) via des entrées soigneusement conçues, le faisant agir en dehors de son comportement prévu.
- **Vulnérabilités de la chaîne d'approvisionnement** : Les composants et logiciels qui composent les applications utilisées par un LLM, tels que les modules Python ou les jeux de données externes, peuvent eux-mêmes être compromis, entraînant des résultats inattendus, des biais introduits et même des vulnérabilités dans l'infrastructure sous-jacente.
- **Dépendance excessive** : Les LLM sont faillibles et ont tendance à halluciner, fournissant des résultats inexacts ou dangereux. Dans plusieurs circonstances documentées, les gens ont pris les résultats pour argent comptant, entraînant des conséquences négatives imprévues dans le monde réel.

Rod Trent, Cloud Advocate chez Microsoft, a écrit un ebook gratuit, [Must Learn AI Security](https://github.com/rod-trent/OpenAISecurity/tree/main/Must_Learn/Book_Version), qui explore en profondeur ces menaces émergentes liées à l'IA et fournit des conseils détaillés sur la meilleure façon de gérer ces scénarios.

## Tests de sécurité pour les systèmes d'IA et les LLM

L'intelligence artificielle (IA) transforme divers domaines et industries, offrant de nouvelles possibilités et avantages pour la société. Cependant, l'IA pose également des défis et des risques importants, tels que la confidentialité des données, les biais, le manque d'explicabilité et les utilisations potentielles abusives. Il est donc crucial de s'assurer que les systèmes d'IA sont sécurisés et responsables, c'est-à-dire qu'ils respectent les normes éthiques et légales et qu'ils peuvent être dignes de confiance pour les utilisateurs et les parties prenantes.

Les tests de sécurité sont le processus d'évaluation de la sécurité d'un système d'IA ou d'un LLM, en identifiant et en exploitant leurs vulnérabilités. Cela peut être effectué par des développeurs, des utilisateurs ou des auditeurs tiers, en fonction de l'objectif et de la portée des tests. Certaines des méthodes de test de sécurité les plus courantes pour les systèmes d'IA et les LLM sont :

- **Assainissement des données** : Il s'agit du processus de suppression ou d'anonymisation des informations sensibles ou privées des données d'entraînement ou des entrées d'un système d'IA ou d'un LLM. L'assainissement des données peut aider à prévenir les fuites de données et les manipulations malveillantes en réduisant l'exposition des données confidentielles ou personnelles.
- **Tests adverses** : Il s'agit du processus de génération et d'application d'exemples adverses aux entrées ou sorties d'un système d'IA ou d'un LLM pour évaluer sa robustesse et sa résilience face aux attaques adverses. Les tests adverses peuvent aider à identifier et à atténuer les vulnérabilités et faiblesses d'un système d'IA ou d'un LLM qui pourraient être exploitées par des attaquants.
- **Vérification du modèle** : Il s'agit du processus de vérification de l'exactitude et de l'exhaustivité des paramètres ou de l'architecture du modèle d'un système d'IA ou d'un LLM. La vérification du modèle peut aider à détecter et à prévenir le vol de modèle en s'assurant que le modèle est protégé et authentifié.
- **Validation des sorties** : Il s'agit du processus de validation de la qualité et de la fiabilité des sorties d'un système d'IA ou d'un LLM. La validation des sorties peut aider à détecter et à corriger les manipulations malveillantes en s'assurant que les sorties sont cohérentes et précises.

OpenAI, un leader dans les systèmes d'IA, a mis en place une série d'_évaluations de sécurité_ dans le cadre de leur initiative de réseau de red teaming, visant à tester les sorties des systèmes d'IA dans l'espoir de contribuer à la sécurité de l'IA.

> Les évaluations peuvent aller de simples tests de questions-réponses à des simulations plus complexes. Voici des exemples concrets d'évaluations développées par OpenAI pour évaluer les comportements de l'IA sous différents angles :

#### Persuasion

- [MakeMeSay](https://github.com/openai/evals/tree/main/evals/elsuite/make_me_say/readme.md) : Dans quelle mesure un système d'IA peut-il tromper un autre système d'IA pour qu'il dise un mot secret ?
- [MakeMePay](https://github.com/openai/evals/tree/main/evals/elsuite/make_me_pay/readme.md) : Dans quelle mesure un système d'IA peut-il convaincre un autre système d'IA de faire un don d'argent ?
- [Ballot Proposal](https://github.com/openai/evals/tree/main/evals/elsuite/ballots/readme.md) : Dans quelle mesure un système d'IA peut-il influencer le soutien d'un autre système d'IA à une proposition politique ?

#### Stéganographie (messages cachés)

- [Steganography](https://github.com/openai/evals/tree/main/evals/elsuite/steganography/readme.md) : Dans quelle mesure un système d'IA peut-il transmettre des messages secrets sans être détecté par un autre système d'IA ?
- [Text Compression](https://github.com/openai/evals/tree/main/evals/elsuite/text_compression/readme.md) : Dans quelle mesure un système d'IA peut-il compresser et décompresser des messages pour permettre de cacher des messages secrets ?
- [Schelling Point](https://github.com/openai/evals/blob/main/evals/elsuite/schelling_point/README.md) : Dans quelle mesure un système d'IA peut-il se coordonner avec un autre système d'IA, sans communication directe ?

### Sécurité de l'IA

Il est impératif de protéger les systèmes d'IA contre les attaques malveillantes, les abus ou les conséquences involontaires. Cela inclut de prendre des mesures pour garantir la sécurité, la fiabilité et la confiance des systèmes d'IA, telles que :

- Sécuriser les données et algorithmes utilisés pour entraîner et exécuter les modèles d'IA.
- Prévenir l'accès non autorisé, la manipulation ou le sabotage des systèmes d'IA.
- Détecter et atténuer les biais, discriminations ou problèmes éthiques dans les systèmes d'IA.
- Garantir la responsabilité, la transparence et l'explicabilité des décisions et actions de l'IA.
- Aligner les objectifs et les valeurs des systèmes d'IA avec ceux des humains et de la société.

La sécurité de l'IA est essentielle pour garantir l'intégrité, la disponibilité et la confidentialité des systèmes d'IA et des données. Certains des défis et opportunités liés à la sécurité de l'IA sont :

- Opportunité : Intégrer l'IA dans les stratégies de cybersécurité, car elle peut jouer un rôle crucial dans l'identification des menaces et l'amélioration des temps de réponse. L'IA peut aider à automatiser et à augmenter la détection et la mitigation des cyberattaques, telles que le phishing, les logiciels malveillants ou les ransomwares.
- Défi : L'IA peut également être utilisée par des adversaires pour lancer des attaques sophistiquées, telles que la génération de contenu faux ou trompeur, l'usurpation d'identité ou l'exploitation de vulnérabilités dans les systèmes d'IA. Par conséquent, les développeurs d'IA ont une responsabilité unique de concevoir des systèmes robustes et résilients contre les abus.

### Protection des données

Les LLM peuvent présenter des risques pour la confidentialité et la sécurité des données qu'ils utilisent. Par exemple, les LLM peuvent potentiellement mémoriser et divulguer des informations sensibles provenant de leurs données d'entraînement, telles que des noms personnels, des adresses, des mots de passe ou des numéros de carte de crédit. Ils peuvent également être manipulés ou attaqués par des acteurs malveillants cherchant à exploiter leurs vulnérabilités ou biais. Il est donc important d'être conscient de ces risques et de prendre des mesures appropriées pour protéger les données utilisées avec les LLM. Voici plusieurs étapes que vous pouvez suivre pour protéger les données utilisées avec les LLM :

- **Limiter la quantité et le type de données partagées avec les LLM** : Partagez uniquement les données nécessaires et pertinentes pour les objectifs visés, et évitez de partager des données sensibles, confidentielles ou personnelles. Les utilisateurs devraient également anonymiser ou chiffrer les données qu'ils partagent avec les LLM, par exemple en supprimant ou masquant toute information identifiante, ou en utilisant des canaux de communication sécurisés.
- **Vérifier les données générées par les LLM** : Vérifiez toujours l'exactitude et la qualité des sorties générées par les LLM pour vous assurer qu'elles ne contiennent pas d'informations indésirables ou inappropriées.
- **Signaler et alerter en cas de violation ou d'incident de données** : Soyez vigilant face à toute activité ou comportement suspect ou anormal des LLM, comme la génération de textes qui sont hors sujet, inexacts, offensants ou nuisibles. Cela pourrait indiquer une violation de données ou un incident de sécurité.

La sécurité, la gouvernance et la conformité des données sont essentielles pour toute organisation souhaitant exploiter la puissance des données et de l'IA dans un environnement multi-cloud. Sécuriser et gouverner toutes vos données est une entreprise complexe et multifacette. Vous devez sécuriser et gouverner différents types de données (structurées, non structurées et données générées par l'IA) dans différents emplacements à travers plusieurs clouds, et vous devez tenir compte des réglementations existantes et futures en matière de sécurité des données, de gouvernance et d'IA. Pour protéger vos données, vous devez adopter certaines bonnes pratiques et précautions, telles que :

- Utiliser des services ou plateformes cloud offrant des fonctionnalités de protection et de confidentialité des données.
- Utiliser des outils de qualité et de validation des données pour vérifier vos données afin de détecter les erreurs, incohérences ou anomalies.
- Utiliser des cadres de gouvernance et d'éthique des données pour garantir que vos données sont utilisées de manière responsable et transparente.

### Émulation des menaces réelles - Red teaming pour l'IA
Simuler des menaces réelles est désormais considéré comme une pratique standard pour construire des systèmes d'IA résilients en utilisant des outils, tactiques et procédures similaires afin d'identifier les risques pour les systèmes et tester la réponse des défenseurs.

> La pratique du red teaming en IA a évolué pour prendre une signification plus large : elle ne se limite pas à rechercher des vulnérabilités de sécurité, mais inclut également l'exploration d'autres défaillances du système, telles que la génération de contenu potentiellement nuisible. Les systèmes d'IA présentent de nouveaux risques, et le red teaming est essentiel pour comprendre ces risques inédits, comme l'injection de prompts et la production de contenu non fondé. - [Microsoft AI Red Team building future of safer AI](https://www.microsoft.com/security/blog/2023/08/07/microsoft-ai-red-team-building-future-of-safer-ai/)

[![Conseils et ressources pour le red teaming](@img/13-AI-red-team.webp)]()

Voici les principaux enseignements qui ont façonné le programme de Red Team IA de Microsoft.

1. **Portée étendue du red teaming en IA :**  
   Le red teaming en IA englobe désormais à la fois les résultats en matière de sécurité et ceux liés à l'IA responsable (RAI). Traditionnellement, le red teaming se concentrait sur les aspects de sécurité, en traitant le modèle comme un vecteur (par exemple, le vol du modèle sous-jacent). Cependant, les systèmes d'IA introduisent de nouvelles vulnérabilités de sécurité (par exemple, l'injection de prompts, l'empoisonnement), nécessitant une attention particulière. Au-delà de la sécurité, le red teaming en IA examine également les problèmes d'équité (par exemple, les stéréotypes) et le contenu nuisible (par exemple, la glorification de la violence). L'identification précoce de ces problèmes permet de prioriser les investissements dans la défense.  

2. **Défaillances malveillantes et bénignes :**  
   Le red teaming en IA prend en compte les défaillances à la fois malveillantes et bénignes. Par exemple, lors du red teaming du nouveau Bing, nous explorons non seulement comment des adversaires malveillants peuvent subvertir le système, mais aussi comment des utilisateurs réguliers peuvent rencontrer du contenu problématique ou nuisible. Contrairement au red teaming de sécurité traditionnel, qui se concentre principalement sur les acteurs malveillants, le red teaming en IA prend en compte une gamme plus large de profils et de défaillances potentielles.  

3. **Nature dynamique des systèmes d'IA :**  
   Les applications d'IA évoluent constamment. Dans les applications de modèles de langage de grande taille, les développeurs s'adaptent aux exigences changeantes. Un red teaming continu garantit une vigilance constante et une adaptation aux risques en évolution.  

Le red teaming en IA n'est pas exhaustif et doit être considéré comme un complément à d'autres contrôles tels que [le contrôle d'accès basé sur les rôles (RBAC)](https://learn.microsoft.com/azure/ai-services/openai/how-to/role-based-access-control) et des solutions complètes de gestion des données. Il est conçu pour compléter une stratégie de sécurité qui vise à utiliser des solutions d'IA sûres et responsables, prenant en compte la confidentialité et la sécurité tout en cherchant à minimiser les biais, le contenu nuisible et la désinformation qui peuvent éroder la confiance des utilisateurs.  

Voici une liste de lectures supplémentaires qui peuvent vous aider à mieux comprendre comment le red teaming peut aider à identifier et atténuer les risques dans vos systèmes d'IA :  

- [Planification du red teaming pour les modèles de langage de grande taille (LLMs) et leurs applications](https://learn.microsoft.com/azure/ai-services/openai/concepts/red-teaming)  
- [Qu'est-ce que le réseau de red teaming d'OpenAI ?](https://openai.com/blog/red-teaming-network)  
- [Red Teaming en IA - Une pratique clé pour construire des solutions d'IA plus sûres et responsables](https://rodtrent.substack.com/p/ai-red-teaming)  
- MITRE [ATLAS (Adversarial Threat Landscape for Artificial-Intelligence Systems)](https://atlas.mitre.org/), une base de connaissances sur les tactiques et techniques utilisées par les adversaires dans des attaques réelles contre les systèmes d'IA.  

## Vérification des connaissances  

Quelle pourrait être une bonne approche pour maintenir l'intégrité des données et prévenir les abus ?  

1. Mettre en place des contrôles d'accès basés sur les rôles solides pour la gestion et l'accès aux données  
1. Implémenter et auditer l'étiquetage des données pour éviter la mauvaise représentation ou l'utilisation abusive des données  
1. S'assurer que votre infrastructure d'IA prend en charge le filtrage de contenu  

A:1, Bien que les trois recommandations soient excellentes, s'assurer que vous attribuez les privilèges d'accès aux données appropriés aux utilisateurs contribuera grandement à prévenir la manipulation et la mauvaise représentation des données utilisées par les LLMs.  

## 🚀 Défi  

Renseignez-vous davantage sur la manière de [gérer et protéger les informations sensibles](https://learn.microsoft.com/training/paths/purview-protect-govern-ai/) à l'ère de l'IA.  

## Excellent travail, continuez votre apprentissage  

Après avoir terminé cette leçon, consultez notre [collection d'apprentissage sur l'IA générative](https://aka.ms/genai-collection) pour continuer à approfondir vos connaissances sur l'IA générative !  

Rendez-vous à la leçon 14 où nous examinerons [le cycle de vie des applications d'IA générative](@lesson/14-the-generative-ai-application-lifecycle) !
