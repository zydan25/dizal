from decimal import Decimal
from io import BytesIO
from app import create_app
from app.extensions import db
from app.models import Asset,Cashbox,DocumentAttachment,Permission,ProjectSettings,Role,RolePermission,User,Document,JournalEntry,CapitalContribution,Farmer
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
        settings=ProjectSettings.get()
        settings.admin_theme="water_pos"
        settings.admin_bottom_nav_enabled=False
        settings.employee_bottom_nav_enabled=True
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
    html=response.get_data(as_text=True)
    assert "مزارع الموظف" in html
    assert "employee-controls-water-pos" not in html
    assert "employee-form-theme-water-pos.css" not in html
    assert "admin-theme-water-pos.css" not in html
    assert client.get(f"/sales/farmer/{own_id}").status_code==200

    # Enabling the existing employee Water theme must keep its home/menu,
    # while only form/card controls adopt the optional Water POS refinements.
    with app.app_context():
        settings=ProjectSettings.get()
        settings.employee_dashboard_theme="water"
        db.session.commit()
    water_home=client.get(response.request.path).get_data(as_text=True)
    assert "employee-theme-water.css" in water_home
    assert 'class="water-header"' in water_home
    assert 'class="water-menu-panel"' in water_home
    assert 'class="bottom-nav d-lg-none"' in water_home
    assert "employee-form-theme-water-pos.css" not in water_home
    account_html=client.get("/auth/account").get_data(as_text=True)
    assert "employee-form-theme-water-pos.css" in account_html
    assert "employee-controls-water-pos" in account_html
    assert "admin-theme-water-pos.css" not in account_html
    farmer_html=client.get(f"/sales/farmer/{own_id}").get_data(as_text=True)
    assert "employee-form-theme-water-pos.css" in farmer_html
    assert client.get(f"/reports/my-operations").status_code==200
    assert client.get(f"/sales/farmer/{other_id}").status_code==403


def test_dispense_ledger_and_creation_form_render():
    app=make_app()
    seed(app)
    client=app.test_client()
    login=client.post("/auth/login",data={"identifier":"manager","password":"secret"},follow_redirects=True)
    assert login.status_code==200

    ledger=client.get("/sales/dispense")
    assert ledger.status_code==200
    ledger_html=ledger.get_data(as_text=True)
    assert "سجل صرف الديزل" in ledger_html
    assert "إضافة صرف" in ledger_html
    assert "من تاريخ" in ledger_html
    assert "كل المزارعين" in ledger_html
    assert "إجمالي قيمة الصرف" in ledger_html

    form=client.get("/sales/dispense/new")
    assert form.status_code==200
    form_html=form.get_data(as_text=True)
    assert "إضافة صرف ديزل" in form_html
    assert 'action="/sales/dispense"' in form_html
    assert "آخر عمليات صرف الديزل" not in form_html

    with app.app_context():
        for name in [
            "sales/dispenses.html",
            "sales/dispense.html",
            "documents/print.html",
            "documents/view.html",
        ]:
            app.jinja_env.get_template(name)

def test_asset_multiple_attachments_on_purchase_and_edit(tmp_path):
    app=make_app()
    manager_id=seed(app)
    app.config["UPLOAD_FOLDER"]=str(tmp_path/"uploads")
    with app.app_context():
        add_capital(Decimal("100000"),"رأس مال اختبار",manager_id,"لتمويل شراء الأصل")
        db.session.commit()
        cashbox_id=Cashbox.query.filter_by(box_type="central",is_active=True).first().id

    client=app.test_client()
    login=client.post("/auth/login",data={"identifier":"manager","password":"secret"},follow_redirects=True)
    assert login.status_code==200
    form_html=client.get("/assets/new").get_data(as_text=True)
    assert 'enctype="multipart/form-data"' in form_html
    assert 'name="attachments" multiple' in form_html

    created=client.post("/assets/new",data={
        "name":"معدات اختبار",
        "category":"أصل ثابت",
        "cost":"1000",
        "acquisition_date":"2026-10-15",
        "payer_cashbox_id":str(cashbox_id),
        "custodian_user_id":"",
        "location":"المستودع",
        "notes":"اختبار المرفقات",
        "create_tank":"",
        "attachments":[
            (BytesIO(b"%PDF-1.7\\nreceipt one\\n%%EOF"),"invoice-one.pdf"),
            (BytesIO(b"%PDF-1.7\\nreceipt two\\n%%EOF"),"invoice-two.pdf"),
        ],
    },follow_redirects=True)
    assert created.status_code==200
    assert "تم إرفاق 2 ملف" in created.get_data(as_text=True)

    with app.app_context():
        asset=Asset.query.filter_by(name="معدات اختبار").one()
        asset_id=asset.id
        attached=DocumentAttachment.query.filter_by(document_id=asset.document_id).order_by(DocumentAttachment.id).all()
        assert [item.original_name for item in attached]==["invoice-one.pdf","invoice-two.pdf"]
        first_attachment_id=attached[0].id

    detail_response=client.get(f"/assets/{asset_id}")
    assert detail_response.status_code==200
    assert "invoice-one.pdf" in detail_response.get_data(as_text=True)
    download=client.get(f"/assets/{asset_id}/attachments/{first_attachment_id}")
    assert download.status_code==200
    assert download.data.startswith(b"%PDF")

    edited=client.post(f"/assets/{asset_id}/edit",data={
        "name":"معدات اختبار",
        "category":"أصل ثابت",
        "cost":"1000.000",
        "acquisition_date":"2026-10-15",
        "custodian_user_id":"",
        "location":"المستودع",
        "status":"active",
        "notes":"تم تحديث بيانات الأصل",
        "attachments":[(BytesIO(b"%PDF-1.7\\nreceipt three\\n%%EOF"),"invoice-three.pdf")],
    },follow_redirects=True)
    assert edited.status_code==200
    assert "تمت إضافة 1 مرفق" in edited.get_data(as_text=True)

    with app.app_context():
        asset=Asset.query.get(asset_id)
        attached=DocumentAttachment.query.filter_by(document_id=asset.document_id).order_by(DocumentAttachment.id).all()
        assert len(attached)==3
        assert attached[-1].original_name=="invoice-three.pdf"

    assert client.get(f"/assets/{asset_id}").status_code==200
    with app.app_context():
        for template_name in ("assets/form.html","assets/detail.html"):
            app.jinja_env.get_template(template_name)


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
        "allow_employee_sale_price_override":"1",
        "color_preset":"violet",
        "font_scale":"1.05",
        "admin_theme":"water_pos",
        "admin_bottom_nav_enabled":"0",
        "employee_bottom_nav_enabled":"1",
        "font_family":"Tajawal",
        "radius":"14px",
    },follow_redirects=True)
    assert response.status_code==200
    with app.app_context():
        settings=ProjectSettings.get()
        assert settings.primary_color=="#6d28d9"
        assert settings.secondary_color=="#9333ea"
        assert settings.font_scale=="1.05"
        assert settings.admin_theme=="water_pos"
        assert settings.admin_bottom_nav_enabled is False
        assert settings.employee_bottom_nav_enabled is True
        assert settings.allow_employee_sale_price_override is True
    rendered_html=response.get_data(as_text=True)
    assert "admin-theme-water-pos.css" in rendered_html
    assert "20261015-water-pos-admin-v4" in rendered_html
    assert "20261015-water-pos-controls-v1" in rendered_html
    assert 'class="bottom-nav d-lg-none"' not in response.get_data(as_text=True)

def test_template_numeric_output_removes_trailing_decimal_zeroes():
    app=make_app()
    seed(app)
    with app.test_request_context("/"):
        from flask import render_template_string
        rendered=render_template_string("{{ amount }}|{{ count }}", amount=Decimal("1250.00"), count=7.0)
        assert rendered=="1250|7"
