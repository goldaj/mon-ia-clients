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

Les dépendances et instructions propres à chaque cible figurent dans les sous-dossiers après import des sources. Les composants ne sont pas destinés à la production en l'état et nécessitent une instance de backend accessible.

## Sécurité

Aucune clé SSH, adresse privée de machine ni secret ne doit être versionné. Les valeurs de configuration sont des exemples ou doivent être fournies localement.

## Compétences mises en œuvre

Prototypage multi-support, intégration d'API, interface conversationnelle, architecture client/serveur et gestion d'environnements.
