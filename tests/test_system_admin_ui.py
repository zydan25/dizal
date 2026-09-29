import json
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import (
    Cashbox, EmployeeProfile, Permission, ProjectSettings, Role, RolePermission, User
)
from app.permissions import PERMISSIONS
from app.services.system_admin import reset_project_data
from flask_security.utils import hash_password


def make_app():
    return create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        "SECURITY_PASSWORD_SALT": "test-salt",
    })


def seed_roles(app):
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        rows = {}
        for key, (label, module) in PERMISSIONS.items():
            row = Permission(key=key, label=label, module=module)
            db.session.add(row)
            rows[key] = row
        manager = Role(name="manager", description="manager", label="مدير")
        employee = Role(name="employee", description="employee", label="موظف")
        db.session.add_all([manager, employee])
        db.session.flush()
        for row in rows.values():
            db.session.add(RolePermission(role_id=manager.id, permission_id=row.id))
        db.session.commit()


def test_pwa_assets_and_manifest_are_install_ready():
    manifest = json.loads(Path("app/static/manifest.webmanifest").read_text(encoding="utf-8"))
    icons = {icon["src"]: icon["sizes"] for icon in manifest["icons"]}
    assert icons["/static/icons/dizal-192.png"] == "192x192"
    assert icons["/static/icons/dizal-512.png"] == "512x512"
    assert Path("app/static/icons/dizal-192.png").read_bytes().startswith(b"\x89PNG")
    assert Path("app/static/icons/dizal-512.png").read_bytes().startswith(b"\x89PNG")
    sw = Path("app/static/sw.js").read_text(encoding="utf-8")
    assert 'register("/sw.js' in Path("app/static/js/app.js").read_text(encoding="utf-8") or "register('/sw.js" in Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "const VERSION=" in sw


def test_manager_account_page_and_updates():
    app = make_app()
    seed_roles(app)
    with app.app_context():
        manager_role = Role.query.filter_by(name="manager").first()
        manager = User(
            username="manager",
            email="manager@test.local",
            phone="777000111",
            password=hash_password("secret"),
            display_name="المدير",
            active=True,
            fs_uniquifier="manager-test",
        )
        manager.roles.append(manager_role)
        db.session.add(manager)
        db.session.commit()
    client = app.test_client()
    login = client.post("/auth/login", data={"identifier": "manager", "password": "secret"}, follow_redirects=True)
    assert login.status_code == 200
    page = client.get("/employees/account")
    assert page.status_code == 200
    assert "بيانات المدير في السندات" in page.get_data(as_text=True)
    updated = client.post(
        "/employees/account",
        data={
            "username": "manager2",
            "phone": "777000222",
            "email": "manager2@test.local",
            "display_name": "مدير المشروع",
            "manager_name": "اسم المدير في السند",
            "manager_phone": "777000222",
        },
        follow_redirects=True,
    )
    assert updated.status_code == 200
    with app.app_context():
        manager = User.query.filter_by(username="manager2").one()
        settings = ProjectSettings.get()
        assert manager.display_name == "مدير المشروع"
        assert settings.manager_name == "اسم المدير في السند"


def test_reset_keeps_active_manager_and_removes_employee_data():
    app = make_app()
    seed_roles(app)
    with app.app_context():
        manager_role = Role.query.filter_by(name="manager").first()
        employee_role = Role.query.filter_by(name="employee").first()
        manager = User(username="manager", password=hash_password("secret"), display_name="مدير", active=True, fs_uniquifier="m1")
        manager.roles.append(manager_role)
        employee = User(username="employee", password=hash_password("secret"), display_name="موظف", active=True, is_employee=True, fs_uniquifier="e1")
        employee.roles.append(employee_role)
        db.session.add_all([manager, employee])
        db.session.flush()
        db.session.add(EmployeeProfile(user_id=employee.id, employee_code="EMP-0001"))
        db.session.add(Cashbox(name="صندوق الموظف", box_type="employee", owner_user_id=employee.id, is_active=True))
        db.session.add(Cashbox(name="الصندوق الرئيسي", box_type="central", is_active=True))
        db.session.commit()
        reset_project_data(preserve_user_id=manager.id)
        db.session.commit()
        assert User.query.filter_by(username="manager").count() == 1
        assert User.query.filter_by(username="employee").count() == 0
        assert User.query.filter_by(is_employee=True).count() == 0
        assert Cashbox.query.filter_by(box_type="central").count() == 1
        assert ProjectSettings.query.count() == 1


def test_sales_report_backwards_compatible_endpoint():
    app = make_app()
    with app.app_context():
        db.create_all()
        assert "reports.sales_report" in app.view_functions
        assert "reports.sales_report_view" in app.view_functions
