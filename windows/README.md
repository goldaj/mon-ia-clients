# Mon IA — Windows v1

Client Windows pour ton IA sur VPS.

Fonctions principales :
- modes ⚡ Rapide et 🛠 Agent ;
- historique multi-conversations ;
- renommer / supprimer ;
- bouton Arrêter ;
- Markdown + blocs de code ;
- chronomètre + vitesse approximative en mode Rapide ;
- état serveur (IA, OpenClaw, MobileAI, RAM, swap, charge, uptime) ;
- reconnexion SSH automatique ;
- masquage des blocs `<think>`.

Lancement : `run.bat`

EXE : `build_exe.bat` → `dist\MonIA.exe`

Les réglages et l'historique restent dans AppData sous `LocalAIClient`, donc une mise à jour depuis v0.x ne les efface pas.

Sécurité : aucun port LLM n'est exposé publiquement ; le client passe par SSH.
