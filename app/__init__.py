from decimal import Decimal,InvalidOperation
import math
from flask import Flask,render_template,redirect,request,url_for,send_from_directory,Response
from flask_login import current_user
from .config import Config
from .extensions import db,migrate,csrf,security

def create_app(config_object=None):
    app=Flask(__name__)
    app.config.from_object(Config)
    if isinstance(config_object,dict):
        app.config.from_mapping(config_object)
    elif config_object is not None:
        app.config.from_object(config_object)
    def clean_number(value):
        if value is None or value == "":
            return ""
        try:
            number=Decimal(str(value).replace(",",""))
            if not number.is_finite():
                return value
            text=format(number,"f")
            if "." in text:
                text=text.rstrip("0").rstrip(".")
            return text or "0"
        except (InvalidOperation,ValueError,TypeError):
            return value

    def display_finalize(value):
        if isinstance(value,(Decimal,float)) and not isinstance(value,bool):
            if isinstance(value,float) and not math.isfinite(value):
                return value
            return clean_number(value)
        return value

    app.jinja_env.filters["clean_number"]=clean_number
    app.jinja_env.finalize=display_finalize

    db.init_app(app)
    migrate.init_app(app,db)
    csrf.init_app(app)

    from flask_security import SQLAlchemyUserDatastore
    from .models import User,Role
    security.init_app(app,SQLAlchemyUserDatastore(db,User,Role))

    from .context import register_context
    register_context(app)

    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.settings import settings_bp
    from .blueprints.employees import employees_bp
    from .blueprints.cashbox import cashbox_bp
    from .blueprints.capital import capital_bp
    from .blueprints.assets import assets_bp
    from .blueprints.fuel import fuel_bp
    from .blueprints.farmers import farmers_bp
    from .blueprints.sales import sales_bp
    from .blueprints.expenses import expenses_bp
    from .blueprints.settlements import settlements_bp
    from .blueprints.reports import reports_bp
    from .blueprints.documents import documents_bp
    from .blueprints.notifications import notifications_bp
    from .blueprints.audit import audit_bp
    from .blueprints.roles import roles_bp
    from .blueprints.whatsapp import whatsapp_bp
    from .blueprints.media import media_bp

    for blueprint in (
        auth_bp,dashboard_bp,settings_bp,employees_bp,cashbox_bp,capital_bp,
        assets_bp,fuel_bp,farmers_bp,sales_bp,expenses_bp,settlements_bp,
        reports_bp,documents_bp,notifications_bp,audit_bp,roles_bp,whatsapp_bp,media_bp
    ):
        app.register_blueprint(blueprint)

    @app.get("/")
    def root():
        return redirect(url_for("dashboard.index" if current_user.is_authenticated else "auth.login"))

    @app.get("/pwa/launch")
    def pwa_launch():
        # Session-independent so it can be safely precached as the PWA start URL.
        # /dashboard/ handles authentication/redirects after launch.
        html="""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1877F2">
<link rel="manifest" href="/manifest.webmanifest">
<title>Dizal</title>
<style>html,body{height:100%;margin:0}body{display:grid;place-items:center;background:#f6f8fc;color:#172033;font-family:Arial,sans-serif}.box{text-align:center;padding:32px}.logo{width:76px;height:76px;border-radius:22px;background:#1877F2;color:#fff;display:grid;place-items:center;margin:0 auto 18px;font-size:34px;font-weight:800}.spinner{width:24px;height:24px;border:3px solid #d9e0ec;border-top-color:#1877F2;border-radius:50%;animation:spin .8s linear infinite;margin:18px auto}@keyframes spin{to{transform:rotate(360deg)}}p{margin:0;color:#68758b;font-size:14px}</style>
</head>
<body><main class="box" aria-live="polite"><div class="logo">D</div><h1>Dizal</h1><div class="spinner" aria-hidden="true"></div><p>جاري فتح النظام…</p></main>
<script>window.setTimeout(function(){window.location.replace("/dashboard/");},150);</script>
</body></html>"""
        response=Response(html,mimetype="text/html")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/pwa/debug")
    def pwa_debug():
        html="""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1877F2">
<link rel="manifest" href="/manifest.webmanifest?v=20260930-6">
<title>Dizal · تشخيص PWA</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;color:#172033;background:#f4f7fb}*{box-sizing:border-box}body{margin:0;padding:16px}main{max-width:760px;margin:0 auto}.card{background:#fff;border:1px solid #e0e7f0;border-radius:18px;padding:16px;margin-bottom:12px;box-shadow:0 5px 18px rgba(20,35,65,.05)}h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:0 0 12px}p{color:#67748a;margin:0 0 12px;line-height:1.7}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.item{border:1px solid #e5ebf3;border-radius:12px;padding:10px;background:#fbfcfe;min-width:0}.item b{display:block;font-size:12px;color:#657287;margin-bottom:5px}.item span{display:block;font-size:14px;word-break:break-word}.ok{color:#187a45;font-weight:800}.bad{color:#b42318;font-weight:800}.warn{color:#9a6700;font-weight:800}button{border:0;border-radius:12px;background:#1877F2;color:#fff;font:inherit;font-weight:800;padding:11px 14px;margin:4px;cursor:pointer}button.secondary{background:#eef3fb;color:#24334d}pre{white-space:pre-wrap;word-break:break-word;background:#111827;color:#e5eefc;border-radius:12px;padding:12px;font-size:12px;direction:ltr;text-align:left;overflow:auto}small{color:#77849a}.icon-test{display:flex;align-items:center;gap:12px;padding:10px;border:1px solid #e5ebf3;border-radius:12px;margin:7px 0}.icon-test img{width:56px;height:56px;object-fit:contain;border-radius:12px;background:#f2f5fa}@media(max-width:560px){.grid{grid-template-columns:1fr}body{padding:10px}}</style>
</head>
<body><main>
<section class="card"><h1>تشخيص Dizal PWA</h1><p>الفحص يعمل من هذا الجهاز نفسه. لا يحتاج كمبيوتر أو F12.</p><button id="refresh">إعادة الفحص</button><button class="secondary" id="install">تجربة التثبيت</button></section>
<section class="card"><h2>الحالة الأساسية</h2><div class="grid" id="state"></div></section>
<section class="card"><h2>فحص الملفات</h2><div class="grid" id="resources"></div></section>
<section class="card"><h2>Service Worker</h2><div id="sw"></div></section>
<section class="card"><h2>الأيقونات</h2><div id="icons"></div></section>
<section class="card"><h2>التفاصيل</h2><pre id="details">جاري الفحص…</pre></section>
</main>
<script src="/static/js/pwa-debug.js?v=20260930-6" defer></script>
</body></html>"""
        response=Response(html,mimetype="text/html")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/manifest.webmanifest")
    def web_manifest():
        response=send_from_directory(app.static_folder,"manifest.webmanifest",mimetype="application/manifest+json")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/sw.js")
    def service_worker():
        response=send_from_directory(app.static_folder,"sw.js",mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"]="/"
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.errorhandler(401)
    def unauthorized(_error):
        return redirect(url_for("auth.login", next=request.full_path))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"),403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"),404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"),500

    @app.get("/health")
    def health():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            status="ok"
        except Exception:
            status="error"
        return {"status":status,"database":status,"version":"integration-2026-09"}

    return app
