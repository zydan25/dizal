#!/usr/bin/env bash
set -euo pipefail
cd /home/root/projects/dizal
source .venv/bin/activate
git pull --ff-only origin main
pip install -r requirements.txt
export FLASK_APP=wsgi.py
flask db upgrade
python seed.py
python -m pytest
pm2 reload dizal --update-env
sudo nginx -t
sudo systemctl reload nginx
curl -fsS http://127.0.0.1:4012/health
