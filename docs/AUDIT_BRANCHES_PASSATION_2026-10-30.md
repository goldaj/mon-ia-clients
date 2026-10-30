# Passation GitHub : branches, PR, audit critique — 30/10/2026

**Objet :** Clients Windows et PWA mobile pour assistant IA. Méthode : inspection du README, de AGENTS.md, des refs et PR GitHub. Aucun test métier exécuté dans cette passe.

## Inventaire exhaustif des branches (référence `main`)
- `chatgpt/review-20261024` — `031d24dee5d8d0e271697c398038b5cb9e6a0fa6` (branche historique : vérifier l'ascendance à nouveau avant nettoyage)
- `feat/mobile-conversation-backup-20261029` — `56e03e43b48a071dd772ab0fe12864a549a112fc` (comparée en direct : behind, ahead 0, behind 4)
- `main` — `ff03ba121d90465e37d597a3f1075d6d28a93513` (conserver, branche par défaut)

## PR (2)
- [#2](https://github.com/goldaj/mon-ia-clients/pull/2) : fusionnée, `feat/mobile-conversation-backup-20261029` vers `main`.
- [#1](https://github.com/goldaj/mon-ia-clients/pull/1) : fusionnée, `chatgpt/review-20261024` vers `main`.

## Analyse critique
L'import/export portable de conversations PWA ne doit pas exfiltrer identifiants ni sessions agents. Vérifier robustesse des schémas JSON, capacité de fusion et résistance aux données malformées/volumineuses, puis compatibilité service worker hors ligne. Les clients Windows et mobile sont distincts.

## Plan de reprise
Relire docs/MOBILE_HISTORY_BACKUP.md et contextes, exécuter tests JS/Python et tester export/import dans un vrai navigateur sur jeux fictifs ; ne jamais committer des conversations exportées.

## Règles
Lire README (# Mon IA | Clients desktop et mobile), AGENTS.md et docs/CHATGPT_PROJECT_HISTORY.md. Ne pas inférer d'une PR fusionnée que les tests manuels ont été exécutés. Aucun merge/suppression de branches ni changement de programme réalisé ici. Les branches encore visibles ne sont pas des PR ouvertes.
