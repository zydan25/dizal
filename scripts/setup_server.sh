#!/usr/bin/env bash
set -euo pipefail
apt-get update
apt-get install -y python3 python3-venv python3-dev build-essential libpq-dev nginx postgresql postgresql-contrib
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='dizal'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER dizal WITH PASSWORD 'dizal';"
sudo -u postgres psql -c "ALTER USER dizal WITH PASSWORD 'dizal';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='dizal'" | grep -q 1 || sudo -u postgres createdb -O dizal dizal
mkdir -p /home/root/projects
cd /home/root/projects
if [ ! -d dizal/.git ]; then git clone https://github.com/zydan25/dizal.git dizal; fi
cd dizal
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
mkdir -p instance/uploads
cp -n .env.example .env || true
export FLASK_APP=wsgi.py
flask db init || true
flask db migrate -m "phase1 foundation" || true
flask db upgrade
python seed.py
cp deploy/nginx.conf /etc/nginx/sites-available/dizal
ln -sf /etc/nginx/sites-available/dizal /etc/nginx/sites-enabled/dizal
nginx -t
systemctl reload nginx
command -v pm2 >/dev/null 2>&1 || npm install -g pm2
pm2 startOrRestart deploy/ecosystem.config.cjs
pm2 save
