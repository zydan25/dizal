#!/usr/bin/env bash
set -euo pipefail
cd /home/root/projects/dizal
source .venv/bin/activate
export FLASK_APP=wsgi.py
mkdir -p instance/uploads
if [ ! -d migrations ]; then flask db init; fi
flask db migrate -m "phase1 foundation"
flask db upgrade
python seed.py
