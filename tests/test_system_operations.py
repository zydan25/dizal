from app import create_app
from app.extensions import db
from app.models import Asset,FuelDispense
from app.services.reports import project_summary,inventory_commitment

def test_new_operational_schema_fields_exist():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        assert "tank_id" in Asset.__table__.c
        assert Asset.__table__.c.tank_id.nullable is True
        assert "sale_type" in FuelDispense.__table__.c
        assert "customer_name" in FuelDispense.__table__.c
        assert FuelDispense.__table__.c.farmer_id.nullable is True

def test_new_reports_remain_safe_on_empty_db():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        assert project_summary()["sales"]==0
        assert inventory_commitment()["stock_liters"]==0
