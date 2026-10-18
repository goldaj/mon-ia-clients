#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ubuntu/mobile-ai"
if [ "$PWD" != "$APP_DIR" ]; then
  echo "Lance ce script depuis $APP_DIR"
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

sudo cp mobile-ai.service /etc/systemd/system/mobile-ai.service
sudo systemctl daemon-reload
sudo systemctl enable --now mobile-ai.service

echo
echo "Service installé."
echo "Test local : curl http://127.0.0.1:8090/api/status"
