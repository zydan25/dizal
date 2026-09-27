from app import create_app
from app.extensions import db
from app.models import ProjectSettings
from app.services.reports import project_summary,inventory_commitment

def test_reports_empty_database_are_safe():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        summary=project_summary()
        inventory=inventory_commitment()
        assert summary["sales"]==0
        assert summary["gross_profit"]==0
        assert inventory["stock_liters"]==0
