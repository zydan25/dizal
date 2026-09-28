from datetime import datetime,timezone,time
from sqlalchemy import func
from flask import render_template
from flask_login import current_user
from ...decorators import permission_required
from ...models import AuditLog,Cashbox,Farmer,FuelDispense,FuelPurchase,Notification,User
from ...permissions import user_has_permission
from ...services.cashbox import balance
from ...services.reports import farmer_debts,inventory_commitment,project_summary
from . import dashboard_bp

@dashboard_bp.get("/")
@permission_required("dashboard.view")
def index():
    manager=user_has_permission(current_user,"users.manage")
    employee_count=User.query.filter_by(is_employee=True).count()
    recent_audits=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    pending_supplies=FuelPurchase.query.filter_by(status="submitted").count()
    pending_farmers=Farmer.query.filter(Farmer.status.in_(["submitted","changes_requested"])).count()
    unread_all=Notification.query.filter_by(read_at=None).count()
    employee_cashbox=None
    employee_stats=None
    summary=None
    inventory=None
    if manager:
        summary=project_summary()
        inventory=inventory_commitment()
    elif current_user.is_employee:
        box=Cashbox.query.filter_by(owner_user_id=current_user.id,box_type="employee",is_active=True).first()
        if box:
            employee_cashbox={"name":box.name,"balance":balance(box.id)}
        debt_rows=[row for row in farmer_debts() if row["farmer"].assigned_employee_id==current_user.id]
        today=datetime.now(timezone.utc).date()
        start=datetime.combine(today,time.min).replace(tzinfo=timezone.utc)
        employee_stats={
            "farmers":Farmer.query.filter_by(assigned_employee_id=current_user.id,status="approved").count(),
            "debts_count":len(debt_rows),
            "debt_amount":sum((row["outstanding"] for row in debt_rows),0),
            "today_sales":db_sum(FuelDispense.total_amount,FuelDispense.employee_id,current_user.id,FuelDispense.status,"approved",FuelDispense.created_at>=start),
            "pending_supplies":FuelPurchase.query.filter_by(employee_id=current_user.id,status="submitted").count(),
            "available_liters":inventory_commitment()["stock_liters"],
        }
    return render_template("dashboard/index.html",manager=manager,employee_count=employee_count,recent_audits=recent_audits,employee_cashbox=employee_cashbox,employee_stats=employee_stats,summary=summary,inventory=inventory,pending_supplies=pending_supplies,pending_farmers=pending_farmers,unread_all=unread_all)

def db_sum(column,*conditions):
    return float(__import__("app.extensions",fromlist=["db"]).db.session.query(func.coalesce(func.sum(column),0)).filter(*conditions).scalar() or 0)
