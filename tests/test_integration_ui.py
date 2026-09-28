from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import Cashbox,Permission,ProjectSettings,Role,RolePermission,User,Document,JournalEntry,CapitalContribution,Farmer
from app.permissions import PERMISSIONS
from app.services.capital import add_capital
from app.services.cashbox import balance
from app.services.reversals import reverse_document
from flask_security.utils import hash_password

def make_app():
    return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test-secret","SECURITY_PASSWORD_SALT":"test-salt"})

def seed(app):
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        manager=Role(name="manager",description="manager",label="مدير")
        db.session.add(manager)
        db.session.flush()
        for key,(label,module) in PERMISSIONS.items():
            perm=Permission(key=key,label=label,module=module)
            db.session.add(perm);db.session.flush();db.session.add(RolePermission(role_id=manager.id,permission_id=perm.id))
        user=User(username="manager",email="manager@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="integration-manager")
        user.roles.append(manager)
        db.session.add(user);db.session.add(Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True))
        db.session.commit()
        return user.id

def test_integration_blueprints_and_health():
    app=make_app();seed(app)
    assert {"audit","roles","whatsapp","media","documents"}.issubset(app.blueprints.keys())
    assert app.test_client().get("/health").get_json()["version"]=="integration-2026-09"

def test_capital_reversal_creates_reversal_and_restores_cash():
    app=make_app();manager_id=seed(app)
    with app.app_context():
        row=add_capital(Decimal("1000"),"مستثمر",manager_id,"اختبار")
        db.session.commit()
        original=row.document
        assert balance(row.cashbox_id)==Decimal("1000.000")
        reversal=reverse_document(original,manager_id,"تصحيح الاختبار")
        db.session.commit()
        assert original.status=="reversed"
        assert reversal.document_type=="REV"
        assert reversal.source_type=="document_reversal"
        assert balance(row.cashbox_id)==Decimal("0.000")
        assert JournalEntry.query.filter_by(document_id=original.id).count()==1
        assert JournalEntry.query.filter_by(document_id=reversal.id).count()==1
        assert CapitalContribution.query.filter_by(id=row.id).first().status=="reversed"


def test_employee_sees_own_farmer_account_and_operations_only():
    app=make_app()
    manager_id=seed(app)
    with app.app_context():
        employee_role=Role(name="employee",description="employee",label="موظف")
        db.session.add(employee_role)
        db.session.flush()
        for key in ["dashboard.view","farmers.view","employee.statement.view","documents.view","cashbox.view","notifications.view"]:
            permission=Permission.query.filter_by(key=key).first()
            db.session.add(RolePermission(role_id=employee_role.id,permission_id=permission.id))
        employee=User(
            username="employee",
            email="employee@test.local",
            password=hash_password("secret"),
            display_name="موظف",
            active=True,
            is_employee=True,
            fs_uniquifier="integration-employee",
        )
        employee.roles.append(employee_role)
        db.session.add(employee)
        db.session.flush()
        own=Farmer(code="F-EMP-1",name="مزارع الموظف",phone="700000001",quota_drums=20,credit_limit_drums=10,assigned_employee_id=employee.id,created_by_id=employee.id,status="approved")
        other=Farmer(code="F-OTHER-1",name="مزارع آخر",phone="700000002",quota_drums=20,credit_limit_drums=10,assigned_employee_id=manager_id,created_by_id=employee.id,status="approved")
        db.session.add_all([own,other])
        db.session.commit()
        own_id,other_id=own.id,other.id
    client=app.test_client()
    response=client.post("/auth/login",data={"identifier":"employee","password":"secret"},follow_redirects=True)
    assert response.status_code==200
    assert "مزارع الموظف" in response.get_data(as_text=True)
    assert client.get(f"/sales/farmer/{own_id}").status_code==200
    assert client.get(f"/reports/my-operations").status_code==200
    assert client.get(f"/sales/farmer/{other_id}").status_code==403


def test_unauthenticated_protected_pages_redirect_to_login():
    app=make_app()
    client=app.test_client()
    response=client.get("/farmers/")
    assert response.status_code==302
    assert "/auth/login" in response.headers["Location"]


def test_settings_palette_and_font_scale_persist():
    app=make_app()
    seed(app)
    client=app.test_client()
    login=client.post("/auth/login",data={"identifier":"manager","password":"secret"},follow_redirects=True)
    assert login.status_code==200
    response=client.post("/settings/",data={
        "project_name":"Dizal",
        "manager_name":"مدير",
        "manager_phone":"700000000",
        "currency":"ريال",
        "drum_liters":"20",
        "max_farmers_per_employee":"50",
        "max_credit_drums_per_farmer":"7",
        "max_dispense_liters_per_day":"4000",
        "default_sale_price_per_liter":"650",
        "color_preset":"violet",
        "font_scale":"1.05",
        "font_family":"Tajawal",
        "radius":"14px",
    },follow_redirects=True)
    assert response.status_code==200
    with app.app_context():
        settings=ProjectSettings.get()
        assert settings.primary_color=="#6d28d9"
        assert settings.secondary_color=="#9333ea"
        assert settings.font_scale=="1.05"

def test_template_numeric_output_removes_trailing_decimal_zeroes():
    app=make_app()
    seed(app)
    with app.test_request_context("/"):
        from flask import render_template_string
        rendered=render_template_string("{{ amount }}|{{ count }}", amount=Decimal("1250.00"), count=7.0)
        assert rendered=="1250|7"
