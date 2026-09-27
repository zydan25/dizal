# Phase 1

انظر docs/PHASE1_IMPLEMENTATION.md.

للتشغيل المحلي:

1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. export FLASK_APP=wsgi.py
5. flask db init
6. flask db migrate -m "phase1 foundation"
7. flask db upgrade
8. python seed.py
9. flask run --port 4012

حساب المدير الأولي يعتمد على DIZAL_ADMIN_USERNAME و DIZAL_ADMIN_PASSWORD.
