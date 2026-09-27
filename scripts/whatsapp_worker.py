import os
import time
from app import create_app
from app.services.whatsapp import send_pending

app=create_app()
with app.app_context():
    interval=int(os.getenv("WHATSAPP_WORKER_INTERVAL","5"))
    while True:
        send_pending(limit=20)
        time.sleep(interval)
