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


def test_point_of_sale_and_sales_report_routes_exist():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.test_request_context("/"):
        from flask import url_for
        assert url_for("sales.point_of_sale") == "/sales/point-of-sale"
        assert url_for("sales.point_of_sale_short") == "/sales/pos"
        assert url_for("reports.sales_report_view") == "/reports/sales"

def test_root_service_worker_route_has_origin_wide_scope():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    client=app.test_client()
    response=client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers.get("Service-Worker-Allowed") == "/"
