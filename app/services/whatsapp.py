import json
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError
from ..extensions import db
from ..models import WhatsAppConfig,WhatsAppMessage,WhatsAppTemplate

def get_config():
    row=WhatsAppConfig.query.first()
    if row is None:
        row=WhatsAppConfig()
        db.session.add(row)
        db.session.flush()
    return row

def render_template(template_key,context):
    template=WhatsAppTemplate.query.filter_by(key=template_key,enabled=True).first()
    if not template: raise ValueError("قالب واتساب غير موجود أو غير فعال.")
    body=template.body
    for key,value in context.items():
        body=body.replace("{{"+key+"}}",str(value))
    return body

def enqueue_text(recipient,body,created_by_id=None,template_key=None):
    if not recipient: raise ValueError("رقم المستلم مطلوب.")
    row=WhatsAppMessage(recipient=recipient,body=body,created_by_id=created_by_id,template_key=template_key,status="queued")
    db.session.add(row)
    db.session.flush()
    return row

def send_http(message,config):
    payload=json.dumps({"to":message.recipient,"message":message.body,"from":config.sender_number}).encode("utf-8")
    request=Request(config.base_url.rstrip("/") + "/send",data=payload,headers={"Content-Type":"application/json","Authorization":f"Bearer {config.api_token or ''}"},method="POST")
    with urlopen(request,timeout=config.timeout_seconds) as response:
        raw=response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

def send_message(message_id):
    message=WhatsAppMessage.query.get(message_id)
    if not message: raise ValueError("الرسالة غير موجودة.")
    config=get_config()
    if not config.enabled: raise ValueError("ربط واتساب غير مفعل.")
    message.status="sending"
    db.session.flush()
    try:
        if config.provider not in {"http","baileys","cloud"}:
            raise ValueError("مزود واتساب غير مدعوم.")
        result=send_http(message,config)
        message.status="sent"
        message.provider_message_id=str(result.get("id") or result.get("message_id") or "")
        message.sent_at=datetime.now(timezone.utc)
        message.error=None
    except (HTTPError,URLError,TimeoutError,ValueError,Exception) as exc:
        message.retry_count+=1
        message.status="failed" if message.retry_count>=config.retry_limit else "retrying"
        message.error=str(exc)[:1000]
        db.session.flush()
        raise
    return message

def send_pending(limit=20):
    rows=WhatsAppMessage.query.filter(WhatsAppMessage.status.in_(["queued","retrying"])).order_by(WhatsAppMessage.created_at.asc()).limit(limit).all()
    sent=0
    for row in rows:
        try:
            send_message(row.id)
            sent+=1
            db.session.commit()
        except Exception:
            db.session.rollback()
    return sent
