from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User,Role,ProjectSettings,Cashbox
from app.services.cashbox import balance
from app.services.capital import add_capital,allocate_to_employee
from app.services.assets import create_asset
from app.services.documents import create_document
from flask_security.utils import hash_password

def make_app():
    return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})

def seed(app):
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        manager=Role(name="manager",description="manager",label="مدير")
        employee_role=Role(name="employee",description="employee",label="موظف")
        db.session.add_all([manager,employee_role])
        user=User(username="manager",email="m@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="m1")
        employee=User(username="employee",email="e@test.local",password=hash_password("secret"),display_name="موظف",active=True,is_employee=True,fs_uniquifier="e1")
        user.roles.append(manager);employee.roles.append(employee_role)
        db.session.add_all([user,employee])
        db.session.flush()
        central=Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True)
        personal=Cashbox(name="صندوق الموظف",box_type="employee",owner_user_id=employee.id,is_active=True)
        db.session.add_all([central,personal])
        db.session.commit()
        return user.id,employee.id

def test_capital_transfer_and_asset_flow():
    app=make_app()
    manager_id,employee_id=seed(app)
    with app.app_context():
        add_capital(Decimal("1230000"),"المستثمر",manager_id,"رأس مال افتتاحي")
        employee=User.query.get(employee_id)
        allocate_to_employee(employee,Decimal("1000000"),manager_id,"رأس مال تشغيل")
        box=Cashbox.query.filter_by(owner_user_id=employee_id).first()
        assert balance(box.id)==Decimal("1000000")
        create_asset("خزان","أصل ثابت",Decimal("75000"),date.today(),box.id,manager_id,employee_id,"المستودع","خزان افتتاحي")
        assert balance(box.id)==Decimal("925000")

def test_document_number_is_generated():
    app=make_app()
    manager_id,_=seed(app)
    with app.app_context():
        doc=create_document("DOC","اختبار سند",manager_id)
        assert doc.number.startswith("DOC-")
        assert len(doc.number.split("-")[-1])==6
