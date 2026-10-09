from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import Account,User,Role,ProjectSettings,EmployeeProfile
from app.services.farmers import create_farmer,review_farmer,change_quota
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
        db.session.add(EmployeeProfile(user_id=employee.id,employee_code="EMP-0001",farmer_limit_override=2,credit_limit_override=Decimal("7")))
        db.session.commit()
        return manager.id,employee.id

def test_farmer_workflow_and_limits():
    app=make_app()
    manager_id,employee_id=seed(app)
    with app.app_context():
        farmer=create_farmer("مزارع 1","777000001","العنوان","",Decimal("5"),Decimal("6"),employee_id,employee_id)
        assert farmer.status=="submitted"
        control=Account.query.filter_by(code="1400").first()
        farmer_account_row=Account.query.filter_by(code=f"1400-F{farmer.id:06d}").first()
        assert control is not None
        assert farmer_account_row is not None
        assert farmer_account_row.parent_id==control.id
        assert farmer_account_row.name==f"ذمم المزارع - {farmer.name}"
        review_farmer(farmer,"approve",manager_id,"تم الاعتماد")
        db.session.commit()
        assert farmer.status=="approved"
        change_quota(farmer,Decimal("7"),Decimal("7"),manager_id,"زيادة معتمدة")
        db.session.commit()
        assert farmer.credit_limit_drums==Decimal("7")

def test_employee_farmer_limit_is_enforced():
    app=make_app()
    manager_id,employee_id=seed(app)
    with app.app_context():
        create_farmer("مزارع 1","777000001",None,None,2,2,employee_id,employee_id)
        db.session.commit()
        create_farmer("مزارع 2","777000002",None,None,2,2,employee_id,employee_id)
        db.session.commit()
        try:
            create_farmer("مزارع 3","777000003",None,None,1,1,employee_id,employee_id)
        except ValueError as exc:
            assert "الحد المسموح" in str(exc)
        else:
            raise AssertionError("Expected farmer limit error")


def test_project_diesel_limit_reserves_agreed_farmer_quantities():
    app=make_app()
    manager_id,employee_id=seed(app)
    with app.app_context():
        settings=ProjectSettings.get()
        settings.project_diesel_limit_liters=Decimal("60")
        db.session.commit()

        create_farmer("مزارع 1","777000101",None,None,Decimal("2"),Decimal("2"),employee_id,employee_id)
        db.session.commit()

        try:
            create_farmer("مزارع 2","777000102",None,None,Decimal("2"),Decimal("2"),employee_id,employee_id)
        except ValueError as exc:
            assert "الفائض المتاح" in str(exc)
            assert "20" in str(exc)
        else:
            raise AssertionError("Project diesel cap should reserve the first farmer's 40 liters")
