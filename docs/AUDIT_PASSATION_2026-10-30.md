# Audit contradictoire et passation — goldaj/mon-ia-clients (2026-10-30)

Sources GitHub : branches, PR, fichiers racine, README ; aucune application cliente lancée ni tests exécutés.

## Branches
`main` : `204e48636d9911a3469739cebd48ae1ac7c8fb71`.
- `chatgpt/review-20261024` : behind, 0 commit(s) exclusif(s), 13 de retard. Travaux absorbés, vérifier dépendances avant retirer.
- `feat/mobile-conversation-backup-20261029` : behind, 0 commit(s) exclusif(s), 2 de retard. Travaux absorbés, vérifier dépendances avant retirer.

## PR
- [#2](https://github.com/goldaj/mon-ia-clients/pull/2) : closed, fusionnée ; feat: portable local conversation backup and restore for Mon IA mobile PWA
- [#1](https://github.com/goldaj/mon-ia-clients/pull/1) : closed, fusionnée ; [DRAFT] Mon IA Mobile: exécution Agent annulable et sans blocage

## Structure et README
`.github`, `.gitignore`, `AGENTS.md`, `README.md`, `docs`, `legacy`, `mobile`, `tests`, `windows`.

# Mon IA | Clients desktop et mobile

**Prototypes d'interfaces pour une IA personnelle | Python · Windows · PWA · SSH**

Collection de clients développés pour piloter un assistant IA à distance, avec une interface Windows et un client web mobile. Le projet explore la séparation entre interface utilisateur et moteur d'inférence local/distant.

## Composants

- `windows/` : prototype desktop Python, appels au serveur, configuration et packaging.
- `mobile/` : interface web/PWA et service Python.
- `legacy/` : versions de référence conservées pour comprendre l'évolution du prototype.

## Objectifs de conception

- Afficher des échanges avec un modèle distant ou auto-hébergé.
- Fournir une interface adaptée à la souris et au téléphone.
- Découpler connexion SSH/tunnel et logique de présentation.
- Garder les détails de connexion en configuration privée.

## Démarrage

Pour Windows, utiliser `windows/run.bat` après configuration du serveur et de la connexion SSH ; voir [le guide Windows](windows/README.md). Le packaging est décrit dans ce même guide. Pour la cible PWA/service, consulter [le guide mobile](mobile/README.md) et adapter l'installation à son propre serveur. Les dépendances figurent dans les fichiers `requirements.txt` de c

## Défis à vérifier
1. Export/restauration des conversations : compatibilité des versions, doublons, IDs, contenu malformé et limites mémoire sur téléphone.
2. Traitement des données et secrets : aucun historique sensible ne doit partir vers un serveur sans action explicite.
3. Tester les opérations longues avec annulation, reprise et changement d'état réseau, sans blocage de l'UI.
4. Reproduire l'installation PWA sur Android, perte du stockage et cas offline, puis documenter les résultats.
5. Les deux anciennes branches sont absorbées ; pas d'autre PR à ouvrir sauf modification testée. Vérifier workflows avant suppression.
