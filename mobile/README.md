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

## Résilience du mode Agent (branche de revue)

Les deux flux de sortie OpenClaw sont désormais drainés simultanément,
sans attendre sa fin : cela évite un blocage du processus lorsque ses logs
dépassent le tampon système. La taille totale de chaque flux est bornée à
2 Mio, avec arrêt du groupe de processus Linux en cas de déconnexion,
annulation, dépassement du délai ou du quota. Au plus 2 processus Agent
peuvent tourner en même temps.

Les entrées de conversation sont bornées ; les messages d'erreur HTTP
n'exposent plus stderr/stdout OpenClaw ni les détails du backend de chat.
Le déploiement nécessite une validation des permissions de l'utilisateur
`ubuntu`, du service systemd et de l'accès privé Tailscale.
