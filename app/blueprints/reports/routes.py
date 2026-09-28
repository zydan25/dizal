from datetime import date,time,datetime,timezone
from flask import abort,render_template,request
from flask_login import current_user
from sqlalchemy import func
from ...decorators import permission_required
from ...models import Cashbox,CashboxTransaction,EmployeeSettlement,User
from ...services.reports import employee_performance,farmer_debts,inventory_commitment,project_summary
from . import reports_bp

@reports_bp.get("/")
@permission_required("reports.view")
def index():
    return render_template("reports/index.html",summary=project_summary(),inventory=inventory_commitment())

@reports_bp.get("/farmers-debts")
@permission_required("reports.view")
def farmers_debts():
    return render_template("reports/farmer_debts.html",rows=farmer_debts())

@reports_bp.get("/employees")
@permission_required("reports.view")
def employees():
    return render_template("reports/employees.html",rows=employee_performance())

@reports_bp.get("/employee/<int:employee_id>")
@permission_required("reports.view")
def employee_statement(employee_id):
    employee=User.query.filter_by(id=employee_id,is_employee=True).first_or_404()
    if not current_user.has_role("manager") and employee.id!=current_user.id:
        abort(403)
    start=date.fromisoformat(request.args.get("start") or date.today().replace(day=1).isoformat())
    end=date.fromisoformat(request.args.get("end") or date.today().isoformat())
    if end<start: abort(400,description="نهاية الفترة لا يمكن أن تسبق بدايتها.")
    start_dt=datetime.combine(start,time.min).replace(tzinfo=timezone.utc)
    end_dt=datetime.combine(end,time.max).replace(tzinfo=timezone.utc)
    box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    transactions=[]
    total_in=0
    total_out=0
    if box:
        transactions=CashboxTransaction.query.filter(CashboxTransaction.cashbox_id==box.id,CashboxTransaction.created_at>=start_dt,CashboxTransaction.created_at<=end_dt).order_by(CashboxTransaction.created_at.asc(),CashboxTransaction.id.asc()).all()
        total_in=sum((row.amount for row in transactions if row.direction=="IN"),0)
        total_out=sum((row.amount for row in transactions if row.direction=="OUT"),0)
    settlements=EmployeeSettlement.query.filter(EmployeeSettlement.employee_id==employee.id,EmployeeSettlement.period_end>=start,EmployeeSettlement.period_start<=end).order_by(EmployeeSettlement.id.desc()).all()
    return render_template("reports/employee_statement.html",employee=employee,box=box,transactions=transactions,total_in=total_in,total_out=total_out,start=start,end=end,settlements=settlements)
