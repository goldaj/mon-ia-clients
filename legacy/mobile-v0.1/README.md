# Mobile AI v0.1

Interface web mobile légère destinée à tourner directement sur le VPS.

## Sécurité

Le serveur web écoute UNIQUEMENT sur `127.0.0.1:8090`.
Il ne doit pas être ouvert dans UFW.

L'accès distant prévu passe par **Tailscale Serve**, donc l'interface reste privée
dans ton tailnet et n'est pas publiée sur Internet.

## Installation sur le VPS

Copier ce dossier dans :

`/home/ubuntu/mobile-ai`

Puis :

```bash
cd /home/ubuntu/mobile-ai
./install.sh
curl http://127.0.0.1:8090/api/status
```

## Accès Tailscale

Une fois Tailscale installé et authentifié sur le VPS :

```bash
sudo tailscale serve --bg 8090
tailscale serve status
```

Installe ensuite Tailscale sur Android, connecte-toi au même compte/tailnet,
puis ouvre l'URL HTTPS `.ts.net` indiquée par `tailscale serve status`.

## Modes

- Rapide : llama.cpp directement, avec streaming.
- Agent : OpenClaw local au VPS.
