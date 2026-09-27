from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import WhatsAppConfig,WhatsAppMessage,WhatsAppTemplate
from ...services.audit import audit
from ...services.whatsapp import enqueue_text,render_template as render_whatsapp_template,send_message
from . import whatsapp_bp

@whatsapp_bp.route("/",methods=["GET","POST"])
@permission_required("whatsapp.manage")
def index():
    config=WhatsAppConfig.query.first()
    if config is None:
        config=WhatsAppConfig()
        db.session.add(config)
        db.session.commit()
    if request.method=="POST":
        config.provider=request.form.get("provider") or "http"
        config.enabled=request.form.get("enabled")=="1"
        config.base_url=request.form.get("base_url")
        token=request.form.get("api_token")
        if token and token!="********":
            config.api_token=token
        config.sender_number=request.form.get("sender_number")
        config.webhook_secret=request.form.get("webhook_secret")
        config.timeout_seconds=int(request.form.get("timeout_seconds") or 15)
        config.retry_limit=int(request.form.get("retry_limit") or 3)
        db.session.commit()
        audit("whatsapp.config.updated","whatsapp_config",config.id,after={"provider":config.provider,"enabled":config.enabled})
        db.session.commit()
        flash("تم حفظ إعدادات واتساب.","success")
        return redirect(url_for("whatsapp.index"))
    templates=WhatsAppTemplate.query.order_by(WhatsAppTemplate.id).all()
    messages=WhatsAppMessage.query.order_by(WhatsAppMessage.created_at.desc()).limit(50).all()
    return render_template("whatsapp/index.html",config=config,templates=templates,messages=messages)

@whatsapp_bp.post("/send")
@permission_required("whatsapp.send")
def send():
    recipient=request.form.get("recipient")
    body=request.form.get("body")
    template_key=request.form.get("template_key") or None
    if template_key and not body:
        body=render_whatsapp_template(template_key,{"name":request.form.get("name",""),"project":request.form.get("project","")})
    try:
        message=enqueue_text(recipient,body,current_user.id,template_key)
        db.session.commit()
        try:
            send_message(message.id)
            db.session.commit()
            flash("تم إرسال الرسالة.","success")
        except Exception:
            db.session.commit()
            flash("تم وضع الرسالة في قائمة الانتظار لكن فشل الإرسال الفوري.","warning")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc),"danger")
    return redirect(url_for("whatsapp.index"))
