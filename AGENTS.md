# Agent instructions — mon-ia-clients

Clients Windows et web mobile pour assistant IA. Les dossiers windows et mobile ont leurs propres guides. Préserver legacy et tester séparément chaque interface.

## Priorities
- Read README.md and docs/CHATGPT_PROJECT_HISTORY.md before changes.
- Keep edits minimal and test before claiming a result.
- Do not overwrite existing work.
- Update docs/CHATGPT_PROJECT_HISTORY.md with relevant user and assistant messages when exact text and dates are supplied; label any summaries as non-verbatim.
- Never invent missing conversation logs or timestamps. Keep the repository's publication constraints in mind.

## Import/Export des conversations PWA (2026-10-29)

Branche `feat/mobile-conversation-backup-20261029`, empilée sur `chatgpt/review-20261024` (PR #1, API Agent résiliente). Pas de fusion avant le parent.

- Lire `docs/MOBILE_HISTORY_BACKUP.md`. `mobile/conversation_backup.js` expose un schéma JSON versionné, un export qui supprime les ID et sessions OpenClaw, un import strict et un merge préservant les conversations actuelles.
- `mobile/app.py` ajoute Exporter/Importer dans le tiroir PWA, sans nouvel endpoint d'upload ; téléchargement local par Blob, cache offline du script via service worker.
- Tests `tests/test_mobile_backup.cjs`, `tests/test_mobile_frontend.py` et `tests/check_mobile_js_syntax.py`, workflow `mobile-tests.yml` (Python + Node). Tests UI et comportement mobile encore à effectuer manuellement.
- **Ne jamais committer un fichier exporté**, il contient des conversations privées en clair. Ne pas réutiliser silencieusement une ancienne session agent de serveur ni introduire d'upload ou synchronisation sans autorisation.
- Avant toute évolution, vérifier les PR/branches en cours et les CI ; conserver les versions `legacy/`, les clients Windows existants et les chemins de secrets privés.
