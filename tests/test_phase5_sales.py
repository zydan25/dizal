from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User,Role,ProjectSettings,Cashbox,FuelTank,Farmer,EmployeeProfile,FarmerPaymentAllocation,JournalEntry
from app.services.capital import add_capital,allocate_to_employee
from app.services.fuel import create_purchase,approve_purchase,current_stock_liters
from app.services.sales import create_dispense,create_general_sale,register_payment,farmer_account,farmer_outstanding_amount
from app.services.farmers import project_diesel_capacity
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
        manager.roles.append(manager_role); employee.roles.append(employee_role)
        db.session.add_all([manager,employee]); db.session.flush()
        db.session.add(EmployeeProfile(user_id=employee.id,employee_code="EMP-0001",farmer_limit_override=20,credit_limit_override=Decimal("10")))
        manager_box=Cashbox(name="الرئيسي",box_type="central",is_active=True)
        employee_box=Cashbox(name="الموظف",box_type="employee",owner_user_id=employee.id,is_active=True)
        tank=FuelTank(name="الخزان",code="TANK-01",is_active=True)
        farmer=Farmer(code="F-000001",name="مزارع 1",phone="777000001",quota_drums=Decimal("7"),credit_limit_drums=Decimal("7"),assigned_employee_id=employee.id,created_by_id=employee.id,status="approved")
        db.session.add_all([manager_box,employee_box,tank,farmer]); db.session.commit()
        return manager.id,employee.id,employee_box.id,tank.id,farmer.id

def seed_stock(app,manager_id,employee_id):
    with app.app_context():
        add_capital(Decimal("2000000"),"المستثمر",manager_id)
        allocate_to_employee(User.query.get(employee_id),Decimal("1500000"),manager_id)
        purchase=create_purchase(employee_id,1,date.today(),"محطة",Decimal("2000"),Decimal("1150000"),Decimal("5000"),0,employee_id,"شراء افتتاحي")
        approve_purchase(purchase,manager_id)
        db.session.commit()

def test_dispense_updates_stock_debt_cashbox_and_cost():
    app=make_app()
    manager_id,employee_id,box_id,tank_id,farmer_id=seed(app)
    seed_stock(app,manager_id,employee_id)
    with app.app_context():
        employee=User.query.get(employee_id)
        farmer=Farmer.query.get(farmer_id)
        sale=create_dispense(employee,farmer,tank_id,Decimal("3"),Decimal("650"),Decimal("10000"),"اختبار")
        db.session.commit()
        assert sale.liters==Decimal("60")
        assert sale.total_amount==Decimal("39000")
        assert sale.credit_amount==Decimal("29000")
        assert sale.cost_amount>0
        assert sale.gross_profit==sale.total_amount-sale.cost_amount
        assert current_stock_liters(tank_id)==Decimal("1940")
        account=farmer_account(farmer)
        assert account["consumed_drums"]==Decimal("3")
        assert account["outstanding_amount"]==Decimal("29000")

def test_payment_allocates_to_oldest_debt():
    app=make_app()
    manager_id,employee_id,box_id,tank_id,farmer_id=seed(app)
    seed_stock(app,manager_id,employee_id)
    with app.app_context():
        employee=User.query.get(employee_id);farmer=Farmer.query.get(farmer_id)
        first=create_dispense(employee,farmer,tank_id,Decimal("2"),Decimal("650"),0)
        db.session.flush()
        second=create_dispense(employee,farmer,tank_id,Decimal("2"),Decimal("700"),0)
        db.session.commit()
        payment=register_payment(employee,farmer,Decimal("30000"),"cash")
        db.session.commit()
        allocations=(FarmerPaymentAllocation.query.filter_by(payment_id=payment.id).order_by(FarmerPaymentAllocation.id.asc()).all())
        assert allocations[0].dispense_id==first.id
        assert allocations[0].amount==Decimal("26000")
        assert allocations[1].dispense_id==second.id
        assert allocations[1].amount==Decimal("4000")
        fresh=Farmer.query.get(farmer_id)
        account=farmer_account(fresh)
        assert account["outstanding_amount"]==Decimal("24000")

def test_cannot_dispense_over_quota():
    app=make_app()
    manager_id,employee_id,box_id,tank_id,farmer_id=seed(app)
    seed_stock(app,manager_id,employee_id)
    with app.app_context():
        employee=User.query.get(employee_id);farmer=Farmer.query.get(farmer_id)
        try:
            create_dispense(employee,farmer,tank_id,Decimal("8"),Decimal("650"),0)
        except ValueError as exc:
            assert "الكمية المتفق عليها" in str(exc)
        else:
            raise AssertionError("quota should block dispense")


def test_general_sale_can_use_only_unreserved_project_surplus():
    app=make_app()
    manager_id,employee_id,box_id,tank_id,farmer_id=seed(app)
    seed_stock(app,manager_id,employee_id)
    with app.app_context():
        settings=ProjectSettings.get()
        settings.project_diesel_limit_liters=Decimal("200")
        db.session.commit()

        employee=User.query.get(employee_id)
        try:
            create_general_sale(employee,tank_id,Decimal("4"),Decimal("650"),"عميل اختبار")
        except ValueError as exc:
            assert "فائض المشروع المتاح 60" in str(exc)
        else:
            raise AssertionError("General sale should not consume diesel reserved by farmer quotas")

        sale=create_general_sale(employee,tank_id,Decimal("3"),Decimal("650"),"عميل اختبار")
        db.session.commit()
        assert sale.liters==Decimal("60")
        assert project_diesel_capacity()["remaining_liters"]==Decimal("0")


def test_farmer_balance_combines_journals_with_older_unposted_sales_without_double_counting():
    app=make_app()
    manager_id,employee_id,box_id,tank_id,farmer_id=seed(app)
    seed_stock(app,manager_id,employee_id)
    with app.app_context():
        employee=User.query.get(employee_id)
        farmer=Farmer.query.get(farmer_id)
        posted_sale=create_dispense(employee,farmer,tank_id,Decimal("2"),Decimal("650"),0)
        db.session.flush()
        legacy_sale=create_dispense(employee,farmer,tank_id,Decimal("1"),Decimal("650"),0)
        db.session.flush()

        # Simulate an older sale whose receivable journal was never posted.
        journal=JournalEntry.query.filter_by(
            document_id=legacy_sale.document_id,source_type="fuel_dispense"
        ).first()
        assert journal is not None
        db.session.delete(journal)
        db.session.commit()

        # 2 drums posted to the ledger + 1 drum not posted yet = 39,000.
        assert farmer_outstanding_amount(farmer_id)==Decimal("39000")
