from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User,Role,Cashbox,FuelTank,ProjectSettings
from app.services.cashbox import balance
from app.services.capital import add_capital,allocate_to_employee
from app.services.fuel import create_purchase,approve_purchase,current_stock_liters
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
        manager.roles.append(manager_role)
        employee.roles.append(employee_role)
        db.session.add_all([manager,employee])
        db.session.flush()
        central=Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True)
        employee_box=Cashbox(name="صندوق الموظف",box_type="employee",owner_user_id=employee.id,is_active=True)
        tank=FuelTank(name="الخزان الرئيسي",code="TANK-01",is_active=True)
        db.session.add_all([central,employee_box,tank])
        db.session.commit()
        return manager.id,employee.id,employee_box.id,tank.id

def test_supply_is_pending_then_approved():
    app=make_app()
    manager_id,employee_id,employee_box_id,tank_id=seed(app)
    with app.app_context():
        add_capital(Decimal("1230000"),"المستثمر",manager_id)
        allocate_to_employee(User.query.get(employee_id),Decimal("1200000"),manager_id)
        purchase=create_purchase(employee_id,tank_id,date.today(),"محطة",Decimal("2000"),Decimal("1150000"),Decimal("5000"),0,employee_id,"توريد افتتاحي")
        assert purchase.status=="submitted"
        assert current_stock_liters()==Decimal("0")
        assert balance(employee_box_id)==Decimal("1200000")
        approve_purchase(purchase,manager_id)
        db.session.commit()
        assert current_stock_liters()==Decimal("2000")
        assert balance(employee_box_id)==Decimal("45000")
        assert purchase.unit_cost==Decimal("577.5")

def test_no_negative_employee_cashbox_on_supply():
    app=make_app()
    manager_id,employee_id,employee_box_id,tank_id=seed(app)
    with app.app_context():
        add_capital(Decimal("50000"),"المستثمر",manager_id)
        allocate_to_employee(User.query.get(employee_id),Decimal("50000"),manager_id)
        purchase=create_purchase(employee_id,tank_id,date.today(),"محطة",Decimal("1000"),Decimal("60000"),0,0,employee_id)
        try:
            approve_purchase(purchase,manager_id)
        except ValueError as exc:
            assert "رصيد" in str(exc)
        else:
            raise AssertionError("Expected insufficient cashbox error")
