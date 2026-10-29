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

Pour Windows, utiliser `windows/run.bat` après configuration du serveur et de la connexion SSH ; voir [le guide Windows](windows/README.md). Le packaging est décrit dans ce même guide. Pour la cible PWA/service, consulter [le guide mobile](mobile/README.md) et adapter l'installation à son propre serveur. Les dépendances figurent dans les fichiers `requirements.txt` de chaque cible.

Les composants sont des prototypes et nécessitent un backend accessible et des paramètres privés locaux ; cette revue documentaire ne valide ni une connexion réelle ni un déploiement de production.

## Sécurité

Aucune clé SSH, adresse privée de machine ni secret ne doit être versionné. Les valeurs de configuration sont des exemples ou doivent être fournies localement.

## Compétences mises en œuvre

Prototypage multi-support, intégration d'API, interface conversationnelle, architecture client/serveur et gestion d'environnements.

## Archives complémentaires

Les itérations Windows v0.1/v0.2 et Mobile v0.1 sont conservées dans `legacy/` à titre de provenance et d’exploration. Elles ne remplacent pas les versions `windows/` et `mobile/`. Les paramètres SSH personnels et les clés restent dans la configuration locale ; les valeurs de connexion par défaut des archives sont vides ou génériques. La compilation et les connexions de ces anciennes versions restent à vérifier.

## Fiabilisation du client mobile (branche de travail)

La route `POST /api/chat/agent` utilise un exécuteur de processus
asynchrone autonome (`mobile/agent_process.py`) :
- lecture **concurrente** de stdout et stderr pour éviter les blocages
  des tampons lorsque l'agent écrit beaucoup ;
- sorties plafonnées à **2 Mio**, délai maximal **930 s** ;
- arrêt du processus et de ses descendants Linux si le client se déconnecte,
  si la requête est annulée ou si le délai/volume est dépassé ;
- **2 agents concurrents maximum** et attente bornée de 10 s ;
- messages d'erreur génériques côté navigateur, sans fuite de journaux,
  transcriptions, commandes ou identifiants privés.

La clé de session est validée (1–80 caractères, lettres ASCII, chiffres,
tiret ou souligné), et la taille du message agent est bornée à 8192 caractères.
Les réponses non JSON sont refusées plutôt que de récupérer un fragment
arbitraire d'une sortie potentiellement corrompue.

Tests hors ligne (processus Python factices, jamais OpenClaw réel) :
`python -m pip install -r mobile/requirements.txt` puis
`python -m unittest discover -s tests -v`.
**Aucun changement déployé sur le VPS** ; vérifier le flux réel OpenClaw et
la politique Tailscale avant de fusionner.

## Sauvegarde portable de l'historique mobile (branche empilée, 29 octobre 2026)

Dans la PWA, menu **Conversations** → **Exporter JSON** ou **Importer JSON**. L'export récupère les conversations locales sous forme de fichier JSON ; l'import valide strictement le fichier, confirme et **ajoute** les conversations sans effacer celles déjà présentes. Les clés de session OpenClaw ne sont pas transportées, les sessions Agent restaurées repartiront de zéro côté serveur. La sauvegarde contient les textes personnels **en clair** : ne pas partager le fichier.

Cette tranche est empilée sur la PR #1 de fiabilisation mobile et ne change pas le client Windows. Lire [docs/MOBILE_HISTORY_BACKUP.md](docs/MOBILE_HISTORY_BACKUP.md) pour les limites, la confidentialité et les tests. Aucun serveur ou appareil n'a été déployé pendant cette intervention.
