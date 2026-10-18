# Local AI Client v0.3

Petit client Windows pour ton IA locale hébergée sur le VPS.

## Architecture

- **Mode Rapide** : l'application ouvre automatiquement un tunnel SSH vers `llama-server`
  puis appelle l'API OpenAI-compatible locale du VPS.
- **Mode Agent** : l'application exécute à distance `openclaw agent ... --json` via SSH.
- Aucun port IA n'a besoin d'être exposé publiquement.

## Prérequis Windows

1. Windows 10/11
2. Python 3.11+
3. OpenSSH Client Windows (`ssh` doit fonctionner dans PowerShell)
4. La même clé SSH que celle utilisée pour te connecter au VPS.

Teste avant de lancer l'app :

```powershell
ssh ubuntu@TON_SERVEUR
```

## Lancement

Double-clique sur `run.bat`.

Au premier lancement, ouvre **Paramètres** et renseigne :
- serveur SSH : IP ou nom DNS du VPS
- utilisateur SSH : `ubuntu` dans notre installation
- clé privée : facultatif si Windows trouve déjà ta clé
- port distant llama.cpp : `8080`
- port local : `18080`
- agent OpenClaw : `main`

Clique ensuite sur **Connecter**.

## Modes

### Rapide
Appelle directement `llama-server`.
C'est le mode à utiliser pour la conversation normale : faible surcharge et streaming.

### Agent
Passe par OpenClaw.
C'est volontairement plus lent et doit être réservé aux tâches où la couche agentique apporte quelque chose.

## Générer un .exe

Double-clique sur `build_exe.bat`.

Le binaire sera créé dans :

`dist\LocalAIClient.exe`

## Sécurité

Le client utilise un tunnel SSH. L'API `llama-server` reste liée à `127.0.0.1` sur le VPS.
Ne change pas le bind de llama.cpp vers `0.0.0.0` juste pour cette application.


## Changements v0.2

- Correction du mode **Agent** : les connexions SSH non interactives ne chargeaient pas
  forcément `~/.profile`, donc `openclaw` n'était pas présent dans le `PATH`.
  Le client appelle maintenant explicitement `$HOME/.npm-global/bin/openclaw`.
- Le mode **Rapide** masque les blocs `<think>...</think>` du modèle LFM Thinking
  afin de n'afficher que sa réponse finale.


## Changements v0.3

- Connexion SSH automatique au démarrage si le serveur est déjà configuré.
- Bouton **Arrêter** pour interrompre une génération, y compris le mode Agent.
- Chronomètre de génération affiché en direct.
- **Entrée** envoie le message ; **Maj+Entrée** insère une nouvelle ligne.
- Le mode Rapide ajoute un mini prompt système en français, volontairement très court.
- Affichage plus clair des modes `⚡ Rapide` et `🛠 Agent`.
- Le texte partiel d'une génération Rapide est conservé si elle est interrompue.
