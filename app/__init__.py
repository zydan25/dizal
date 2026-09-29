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
        # Keep the origin root as a cacheable 200 response, like the working
        # Alkas PWA. The dashboard route remains responsible for auth/permissions.
        response=Response("""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="refresh" content="0;url=/dashboard/">
<title>Dizal</title>
</head>
<body>
<script>window.location.replace("/dashboard/");</script>
</body>
</html>""",mimetype="text/html")
        return response

    @app.get("/manifest.webmanifest")
    def web_manifest():
        return Response(
            """{
  "name": "Dizal - إدارة توزيع الديزل",
  "short_name": "Dizal",
  "lang": "ar",
  "dir": "rtl",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#0f172a",
  "icons": [
    {
      "src": "/static/icons/dizal-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/icons/dizal-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}""",
            mimetype="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        js = """const CACHE='dizal-shell-v14';
const SHELL=['/','/static/css/app.css','/static/js/app.js'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('dizal-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.pathname.startsWith('/api')||u.pathname.startsWith('/admin')) return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))));
});"""
        return Response(js, mimetype="application/javascript")

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
