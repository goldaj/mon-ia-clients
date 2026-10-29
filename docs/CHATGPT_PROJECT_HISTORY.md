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

## 2026-10-24 : fiabilisation des agents du client mobile
- **Utilisateur (verbatim, heure indisponible)** : « vas-y avance sur toutes tes propositions », à la suite des propositions sur Jade, Twitch Pokémon et Mon IA Clients et de l'interdiction temporaire de toucher à Hyperliquid.
- **Assistant (résumé non verbatim)** : résolution du blocage possible par remplissage des pipes stderr/stdout de la commande OpenClaw ; arrêt avec signal de groupe de processus Linux sur déconnexion, annulation ou dépassement ; validation et plafonds de sorties ; tests de sous-processus factices.
- Aucun OpenClaw réel lancé, aucun VPS ni compte atteint, aucune modification Hyperliquid. Branche isolée `chatgpt/review-20261024`, PR brouillon ; essais sur VPS restant à effectuer.

## Intervention 2026-10-29 — sauvegarde locale PWA (résumé non verbatim)

- Demande utilisateur : développer réellement plusieurs dépôts GitHub au fil de la conversation, inspecter les travaux et PR existants, documenter les changements pour Codex. Certains dépôts ont été exclus explicitement pour cette session ; Mon IA Clients n'en fait pas partie.
- Inspection : branche `main` et PR brouillon #1 sur `chatgpt/review-20261024`, CI parent réussie ; la nouvelle branche `feat/mobile-conversation-backup-20261029` repart de cette branche pour préserver les corrections de sous-processus Agent.
- Nouvelle fonctionnalité : exporter/importer les historiques PWA en JSON directement dans le navigateur, contrôle strict de schéma et de taille, conservation des conversations existantes, nouveaux IDs et sessions Agent (mémoire serveur **non restaurée**), aucune route de transfert des historiques.
- Tests JavaScript sous Node et contrôles de structure/syntaxe du frontend embarqué ajoutés au workflow `mobile-tests.yml`. CI et test mobile réel à vérifier avant de déclarer fonctionnel sur téléphone.
- Confidentialité : le fichier exporté contient le texte en clair ; ne pas le publier ni le mettre en Git. Aucun appareil ni VPS n'a été contacté, pas de nouvelle ouverture réseau.
- Détail et passation : `docs/MOBILE_HISTORY_BACKUP.md`. Faire une revue de la PR parent avant fusion, tester sous Tailscale avec un historique factice.
