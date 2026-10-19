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
