from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import Cashbox,Permission,ProjectSettings,Role,RolePermission,User,Document,JournalEntry,CapitalContribution
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
