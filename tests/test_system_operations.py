from app import create_app
from app.extensions import db
from flask_security.utils import hash_password
from app.models import Asset,FuelDispense,Cashbox,EmployeeProfile,Farmer,ProjectSettings,Role,User
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
        assert "allow_employee_sale_price_override" in ProjectSettings.__table__.c
        assert ProjectSettings.get().allow_employee_sale_price_override is False

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

def test_root_and_manifest_pwa_endpoints_are_install_ready():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    client=app.test_client()
    root=client.get("/")
    manifest=client.get("/manifest.webmanifest")
    sw=client.get("/sw.js")
    assert root.status_code==302
    assert "/auth/login" in root.headers["Location"]
    assert manifest.status_code==200
    assert "manifest+json" in (manifest.headers.get("Content-Type") or "")
    assert manifest.get_json()["start_url"]=="/"
    assert manifest.get_json()["scope"]=="/"
    assert sw.status_code==200
    assert sw.headers.get("Service-Worker-Allowed")=="/"
    assert "/static/offline.html" in sw.get_data(as_text=True)

def test_reset_clears_operational_data_but_preserves_manager():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        settings=ProjectSettings.get()
        manager_role=Role(name="manager",description="manager",label="مدير")
        employee_role=Role(name="employee",description="employee",label="موظف")
        db.session.add_all([manager_role,employee_role]);db.session.flush()
        manager=User(username="manager",email="manager@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="reset-manager")
        employee=User(username="employee",email="employee@test.local",password=hash_password("secret"),display_name="موظف",active=True,is_employee=True,fs_uniquifier="reset-employee")
        manager.roles.append(manager_role);employee.roles.append(employee_role)
        db.session.add_all([manager,employee]);db.session.flush()
        db.session.add(EmployeeProfile(user_id=employee.id,employee_code="EMP-0001"))
        db.session.add(Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True))
        db.session.add(Cashbox(name="صندوق الموظف",box_type="employee",owner_user_id=employee.id,is_active=True))
        farmer=Farmer(code="F-000001",name="مزارع اختبار",phone="700000001",quota_drums=5,credit_limit_drums=5,assigned_employee_id=employee.id,created_by_id=employee.id,status="approved")
        db.session.add(farmer);db.session.commit()
        from app.services.system_admin import reset_project_data
        reset_project_data()
        db.session.commit()
        db.session.expire_all()
        assert User.query.filter_by(username="manager").one().id==manager.id
        assert User.query.filter_by(username="employee").first() is None
        assert Farmer.query.count()==0
        assert EmployeeProfile.query.filter_by(user_id=employee.id).first() is None
        assert Cashbox.query.filter_by(box_type="employee",owner_user_id=employee.id).first() is None
        assert Cashbox.query.filter_by(box_type="central",is_active=True).first() is not None
        assert ProjectSettings.query.count()==1
        assert settings.id==ProjectSettings.get().id

def test_manager_account_page_updates_identity_and_password():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        role=Role(name="manager",description="manager",label="مدير")
        db.session.add(role);db.session.flush()
        user=User(username="manager",email="manager@test.local",password=hash_password("secret"),display_name="مدير",phone="700000000",active=True,fs_uniquifier="account-manager")
        user.roles.append(role);db.session.add(user);db.session.commit()
    client=app.test_client()
    login=client.post("/auth/login",data={"identifier":"manager","password":"secret"},follow_redirects=True)
    assert login.status_code==200
    response=client.post("/auth/account",data={
        "display_name":"مدير النظام",
        "username":"system-admin",
        "phone":"700000009",
        "email":"admin@dizal.local",
        "document_manager_name":"المهندس زيدان",
        "document_manager_phone":"700000009",
        "current_password":"secret",
        "new_password":"new-secret",
        "confirm_password":"new-secret",
    },follow_redirects=True)
    assert response.status_code==200
    with app.app_context():
        user=User.query.filter_by(email="admin@dizal.local").first()
        assert user.username=="system-admin"
        assert user.display_name=="مدير النظام"
        assert ProjectSettings.get().manager_name=="المهندس زيدان"
        assert ProjectSettings.get().manager_phone=="700000009"
        assert user.password!= "new-secret"

def test_employee_creation_can_assign_manager_role():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})
    with app.app_context():
        db.create_all()
        manager_role=Role(name="manager",description="manager",label="مدير")
        employee_role=Role(name="employee",description="employee",label="موظف")
        db.session.add_all([manager_role,employee_role]);db.session.flush()
        manager=User(username="manager",email="manager@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="create-manager")
        manager.roles.append(manager_role);db.session.add(manager);db.session.commit()
    client=app.test_client()
    assert client.post("/auth/login",data={"identifier":"manager","password":"secret"},follow_redirects=True).status_code==200
    response=client.post("/employees/new",data={
        "display_name":"مدير تشغيل",
        "username":"ops-manager",
        "phone":"700000010",
        "email":"ops-manager@dizal.local",
        "password":"secret123",
        "role":"manager",
        "salary_type":"fixed",
        "salary_value":"0",
        "notes":"مدير فرعي",
    },follow_redirects=True)
    assert response.status_code==200
    with app.app_context():
        created=User.query.filter_by(username="ops-manager").one()
        assert created.is_employee is True
        assert created.has_role("manager")
        assert EmployeeProfile.query.filter_by(user_id=created.id).first() is not None
        assert Cashbox.query.filter_by(owner_user_id=created.id,box_type="employee").first() is not None
