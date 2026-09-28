from app import create_app
from app.extensions import db
from app.models import Permission, ProjectSettings, Role, RolePermission, User
from app.permissions import PERMISSIONS, user_has_permission
from flask_security.utils import hash_password

def make_app():
    return create_app({
        "TESTING":True,
        "SQLALCHEMY_DATABASE_URI":"sqlite://",
        "WTF_CSRF_ENABLED":False,
        "SECRET_KEY":"test-secret",
        "SECURITY_PASSWORD_SALT":"test-salt",
    })

def seed_test(app):
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        perms={}
        for key,(label,module) in PERMISSIONS.items():
            row=Permission(key=key,label=label,module=module)
            db.session.add(row)
            perms[key]=row
        manager=Role(name="manager",description="manager",label="مدير")
        employee=Role(name="employee",description="employee",label="موظف")
        db.session.add_all([manager,employee])
        db.session.flush()
        for row in perms.values():
            db.session.add(RolePermission(role_id=manager.id,permission_id=row.id))
        user=User(username="admin",email="admin@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="admin-test")
        user.roles.append(manager)
        db.session.add(user)
        db.session.commit()

def test_health_and_login():
    app=make_app()
    seed_test(app)
    client=app.test_client()
    assert client.get("/health").status_code==200
    response=client.post("/auth/login",data={"identifier":"admin","password":"secret"},follow_redirects=True)
    assert response.status_code==200
    assert "نظرة كاملة" in response.get_data(as_text=True)

def test_permission_service():
    app=make_app()
    seed_test(app)
    with app.app_context():
        user=User.query.filter_by(username="admin").first()
        assert user_has_permission(user,"settings.manage") is True
        assert user_has_permission(user,"unknown.permission") is True
