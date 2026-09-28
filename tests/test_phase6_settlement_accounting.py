from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User,Role,Cashbox,FuelTank,ProjectSettings,EmployeeProfile,Account,JournalEntry
from app.services.capital import add_capital,allocate_to_employee
from app.services.fuel import create_purchase,approve_purchase
from app.services.settlements import settlement_preview,create_settlement
from app.services.expenses import create_expense
from flask_security.utils import hash_password

def make_app():
    return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","SECURITY_PASSWORD_SALT":"test"})

def seed(app):
    with app.app_context():
        db.create_all()
        ProjectSettings.get()
        manager_role=Role(name="manager",description="manager",label="مدير")
        employee_role=Role(name="employee",description="employee",label="موظف")
        db.session.add_all([manager_role,employee_role])
        manager=User(username="manager",email="m@test.local",password=hash_password("secret"),display_name="مدير",active=True,fs_uniquifier="m1")
        employee=User(username="employee",email="e@test.local",password=hash_password("secret"),display_name="موظف",active=True,is_employee=True,fs_uniquifier="e1")
        manager.roles.append(manager_role);employee.roles.append(employee_role)
        db.session.add_all([manager,employee]);db.session.flush()
        db.session.add(EmployeeProfile(user_id=employee.id,employee_code="EMP-0001",salary_type="fixed",salary_value=Decimal("50000")))
        db.session.add(Cashbox(name="الرئيسي",box_type="central",is_active=True))
        db.session.add(Cashbox(name="الموظف",box_type="employee",owner_user_id=employee.id,is_active=True))
        db.session.add(FuelTank(name="الخزان",code="TANK-01",is_active=True))
        db.session.commit()
        return manager.id,employee.id

def test_journal_accounts_and_settlement_preview():
    app=make_app()
    manager_id,employee_id=seed(app)
    with app.app_context():
        add_capital(Decimal("1230000"),"المستثمر",manager_id)
        allocate_to_employee(User.query.get(employee_id),Decimal("1000000"),manager_id)
        employee_box=Cashbox.query.filter_by(owner_user_id=employee_id,box_type="employee").first()
        create_expense(employee_box.id,employee_id,"نقل",Decimal("5000"),date.today(),manager_id,"نقل افتتاحي")
        db.session.commit()
        preview=settlement_preview(User.query.get(employee_id),date.today(),date.today())
        assert preview["operating_expenses"]==Decimal("5000")
        assert preview["employee_salary"]==Decimal("50000")
        assert Account.query.filter_by(code="3000").first() is not None
        assert JournalEntry.query.count()>=3

def test_unbalanced_journal_rejected():
    app=make_app()
    manager_id,_=seed(app)
    with app.app_context():
        from app.services.accounting import post_journal
        try:
            post_journal("test","1","غير متوازن",manager_id,[{"account_code":"1100","debit":100}])
        except ValueError as exc:
            assert "غير متوازن" in str(exc)
        else:
            raise AssertionError("journal must be balanced")
