# Contexte ChatGPT pour Mon IA Clients

**Initialisé le 2026-10-24. Couverture : partielle, sauf les sources originales référencées explicitement.** Codex doit lire ce fichier après `AGENTS.md` et avant toute reprise du projet. Une mémoire reconstruite n'est pas la totalité du chat.

## Projet confirmé par le dépôt
- Dépôt : `goldaj/mon-ia-clients`.
- Objet : Clients desktop Windows/Python et mobile PWA/web pour piloter une IA distante ou locale en séparant l'interface utilisateur du moteur d'inférence.
- Contraintes : Garder les anciennes versions dans `legacy/`, les interfaces dans `windows/` et `mobile/`. Ne jamais inclure clés SSH, adresses personnelles de serveurs, tokens ni secrets d'authentification.
- Validation : Lire `windows/README.md` et `mobile/README.md` ; Windows via `windows/run.bat` seulement après configuration privée. Ne pas affirmer une connexion réelle sans la vérifier.

## Échanges attestés ou sources à lire

2026-09-21 — Assistant, résumé reconstruit, non verbatim : architecture Jade/IA locale avec moteur d'inférence séparé des clients.

2026-10-18 — Assistant, résumé reconstruit, non verbatim : inventaire et séparation des prototypes de clients PC/téléphone. Aucun verbatim intégral des anciennes conversations n'est accessible ici.

2026-10-24 — Utilisateur (verbatim, heure non vérifiable) : « je te demande de lire mes repo git où tu es le dernier utilisateur, de rajouter un AGENTS.md pertinent s'il n'y en a pas. Mais en plus, tu rajoutera un document repérable par codex (peut être le référencer dans le AGENTS.md justement ?) où tu mets l'intégralité de nos échanges liés à ce projet. Mes questions, tes réponses (de sorte à les différencier) et les horodatages si tu les as. »

## Limites de couverture, fidélité et mise à jour
- Les passages marqués `verbatim` sont des extraits exacts disponibles dans le contexte ; les résumés ne doivent **jamais** être cités comme du dialogue mot pour mot. Aucune réponse complète de l'assistant n'a été inventée.
- Pour obtenir l'intégralité des questions, réponses et horodatages : intégrer un export authentique des conversations pertinentes ; conserver l'ordre et le rôle des messages, et expurger avant publication les éléments sensibles et hors projet.
- En intervention future, ajouter en bas les nouveaux dialogues sourcés et les décisions vérifiées, sans effacer les entrées précédentes. Ce journal et `AGENTS.md` sont versionnés dans Git.
