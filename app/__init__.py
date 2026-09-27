from flask import Flask
from .config import Config
from .extensions import db,migrate,csrf,security
def create_app(config_object=None):
    app=Flask(__name__);app.config.from_object(Config)
    if isinstance(config_object,dict):app.config.from_mapping(config_object)
    elif config_object is not None:app.config.from_object(config_object)
    db.init_app(app);migrate.init_app(app,db);csrf.init_app(app)
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
    app.register_blueprint(auth_bp);app.register_blueprint(dashboard_bp);app.register_blueprint(settings_bp);app.register_blueprint(employees_bp);app.register_blueprint(cashbox_bp);app.register_blueprint(capital_bp);app.register_blueprint(assets_bp);app.register_blueprint(fuel_bp);app.register_blueprint(farmers_bp)
    from flask import render_template
    @app.errorhandler(403)
    def forbidden(_error):return render_template("errors/403.html"),403
    @app.errorhandler(404)
    def not_found(_error):return render_template("errors/404.html"),404
    @app.errorhandler(500)
    def server_error(_error):return render_template("errors/500.html"),500
    @app.get("/health")
    def health():
        from sqlalchemy import text
        try:db.session.execute(text("SELECT 1"));status="ok"
        except Exception:status="error"
        return {"status":status,"database":status,"version":"phase4"}
    return app
