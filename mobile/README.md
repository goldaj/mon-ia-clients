# Mon IA — Mobile/PWA v1

Nouveautés :
- PWA installable sur Android ;
- historique multi-conversations ;
- renommage / suppression ;
- bouton Arrêter ;
- état serveur (IA, OpenClaw, RAM, swap, CPU, uptime) ;
- Markdown léger ;
- migration de l'historique v0.x ;
- accès toujours privé via Tailscale Serve.

## Mise à jour

```bash
cd /home/ubuntu
rm -rf /home/ubuntu/mobile-ai
mkdir /home/ubuntu/mobile-ai
unzip MonIA_Mobile_v1.zip -d /home/ubuntu/mobile-ai
cd /home/ubuntu/mobile-ai
chmod +x install.sh
./install.sh
curl http://127.0.0.1:8090/api/status
```

Le drop-in de limite mémoire dans `/etc/systemd/system/mobile-ai.service.d/` reste en place.

Android : avec Tailscale actif, ouvre :

`https://YOUR-TAILSCALE-HOST.ts.net/`

Puis Chrome → menu ⋮ → Installer l'application / Ajouter à l'écran d'accueil.

Ne pas ouvrir le port 8090 dans UFW.
