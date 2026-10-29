# Sauvegarde et restauration portable du client PWA — 29 octobre 2026

## Fonctionnalité utilisateur

Dans le volet **Conversations**, les boutons **Exporter JSON** et **Importer JSON** sont disponibles. Ils manipulent l'historique conservé dans le `localStorage` **du navigateur actuel** :

- Export : télécharge un fichier `mon-ia-conversations-AAAA-MM-JJ.json` contenant les titres, modes et messages des conversations. Le fichier est généré dans le navigateur par `Blob` / `URL.createObjectURL`. **Aucun upload au serveur ni nouvelle API d'export**.
- Import : sélection d'un fichier JSON local, validation stricte du schéma et des limites, confirmation avant ajout. Les conversations présentes sont **préservées** ; les importées reçoivent de nouveaux identifiants, ce qui évite les collisions.
- L'interface bloque import et export pendant la génération d'un message. En cas d'échec (fichier incorrect ou quota de stockage), elle conserve l'ancien état.
- Après import, les conversations Agent sont visibles, **mais leurs sessions côté OpenClaw ne sont pas réimportées**. De nouvelles clés de session sont générées pour éviter de reconnecter silencieusement une ancienne session d'un autre appareil. La conversation Agent suivante repart donc sans sa mémoire serveur précédente. Le mode Rapide peut réutiliser ses messages comme contexte, selon les limites du backend.

## Confidentialité et limites

Le fichier contient **l'intégralité du texte sauvegardé**, qui peut comprendre des informations privées. Le stocker dans un emplacement personnel et ne pas le publier, l'envoyer dans un ticket ou le committer sur GitHub. L'export n'est **ni chiffré, ni automatiquement synchronisé**. L'import utilise uniquement le navigateur, le serveur FastAPI fournit le script statique `conversation_backup.js`.

Format versionné : `kind = mon-ia-conversations`, `version = 1`, `created_at` et `conversations` (titre, mode, messages). Aucun identifiant de session OpenClaw, token ou adresse SSH n'est copié. Limites : **200 conversations**, **1 000 messages par conversation**, **100 000 caractères par message**, **2 millions de caractères cumulés**, fichier **5 Mo maximum**. Le fichier JSON est contrôlé avant injection dans l'UI existante, qui échappe déjà les textes Markdown/HTML.

La sauvegarde locale est sans mot de passe, sans compte et sans stockage cloud. Les API conversationnelles existantes continuent leur comportement actuel. Aucune promesse de résilience absolue : si l'application est effacée de l'appareil, il faut restaurer depuis un export précédemment téléchargé.

## Déploiement et tests

Cette PR est **empilée sur la PR #1**, qui corrige l'exécution des agents. La branche de référence est `chatgpt/review-20261024`, pas `main`. Ne pas fusionner la présente PR sans sa base et sa validation.

```bash
python -m pip install -r mobile/requirements.txt
python -m unittest discover -s tests -v
node --check mobile/conversation_backup.js
node tests/test_mobile_backup.cjs
python tests/check_mobile_js_syntax.py
```

Le workflow GitHub Actions mobile installe Python 3.11 et Node.js 22 puis exécute les tests existants et nouveaux. Les tests Node vérifient import/export, conservation des conversations en cours, re-cléage des sessions, champs omis et refus de formats malveillants. Le test Python contrôle le DOM, l'existence des boutons et l'absence d'appel upload, puis le script `check_mobile_js_syntax` valide la syntaxe du JS embarqué et du service worker.

**À vérifier sur un vrai téléphone** : sélection du fichier, téléchargement par navigateur/PWA, ouverture sous Tailscale et récupération après fermeture de la PWA. La CI seule n'est pas un test mobile.

## Reprise Codex

1. Lire `AGENTS.md`, `README.md`, `docs/CHATGPT_PROJECT_HISTORY.md`, `mobile/README.md` et les PR #1 puis la nouvelle PR empilée.
2. Vérifier la CI complète, puis effectuer une validation manuelle mobile (Android/Chrome) et Windows/Edge avec des **conversations factices**, pas des secrets réels.
3. Vérifier quotas réels de `localStorage`, export PWA installé, import hors ligne (le script est ajouté au cache du service worker) et scénario d'erreur de stockage.
4. Étudier ensuite l'export chiffré optionnel et le transfert Windows ↔ mobile par un format interopérable. Ne pas créer de synchronisation automatique de secrets sans consentement.
5. Aucune migration de serveur, aucun déploiement VPS ou port réseau public ne sont réalisés ici.
