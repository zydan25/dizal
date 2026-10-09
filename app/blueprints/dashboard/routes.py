from datetime import datetime,timezone,time,timedelta
from sqlalchemy import func
from flask import render_template
from flask_login import current_user
from ...decorators import permission_required
from ...models import AuditLog,Cashbox,Document,Farmer,FarmerPayment,FuelDispense,FuelPurchase,FuelTank,Notification,ProjectSettings,User
from ...permissions import user_has_permission
from ...services.cashbox import balance
from ...services.farmers import project_diesel_capacity
from ...services.sales import farmer_account
from ...services.reports import farmer_debts,inventory_commitment,project_summary
from . import dashboard_bp

@dashboard_bp.get("/")
@permission_required("dashboard.view")
def index():
    manager=user_has_permission(current_user,"users.manage")
    employee_count=User.query.filter_by(is_employee=True).count()
    recent_audits=AuditLog.query.filter(AuditLog.actor_user_id==current_user.id).order_by(AuditLog.created_at.desc()).limit(8).all()
    pending_supplies=FuelPurchase.query.filter_by(status="submitted").count()
    pending_farmers=Farmer.query.filter(Farmer.status.in_(["submitted","changes_requested"])).count()
    unread_all=Notification.query.filter_by(read_at=None).count()
    employee_cashbox=None
    employee_stats=None
    employee_debtors=[]
    employee_farmers=[]
    employee_followups=[]
    employee_farmers_total=0
    employee_notifications=[]
    summary=None
    inventory=None
    trend_rows=[]
    tank_overview=[]
    if manager:
        recent_audits=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
        summary=project_summary()
        inventory=inventory_commitment()
    if manager or current_user.is_employee:
        trend_rows=operational_trend(None if manager else current_user.id)
        active_tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).limit(8).all()
        from ...services.fuel import current_stock_liters
        tank_overview=[{"tank":tank,"stock":current_stock_liters(tank.id)} for tank in active_tanks]
    if current_user.is_employee and not manager:
        box=Cashbox.query.filter_by(owner_user_id=current_user.id,box_type="employee",is_active=True).first()
        if box:
            employee_cashbox={"name":box.name,"balance":balance(box.id)}
        debt_rows=[row for row in farmer_debts() if row["farmer"].assigned_employee_id==current_user.id]
        employee_debtors=sorted(debt_rows,key=lambda row:float(row.get("outstanding") or 0),reverse=True)[:5]
        employee_farmers=[
            {"farmer":farmer,"account":farmer_account(farmer)}
            for farmer in Farmer.query.filter_by(assigned_employee_id=current_user.id).filter(
                Farmer.status.in_(["approved","suspended"])
            ).order_by(Farmer.name).limit(40).all()
        ]
        employee_farmers_total=Farmer.query.filter_by(assigned_employee_id=current_user.id).filter(
            Farmer.status.in_(["approved","suspended"])
        ).count()
        employee_followups=Farmer.query.filter_by(
            assigned_employee_id=current_user.id,status="changes_requested"
        ).order_by(Farmer.updated_at.desc(),Farmer.id.desc()).limit(10).all()
        employee_notifications=Notification.query.filter_by(user_id=current_user.id).order_by(
            Notification.created_at.desc()
        ).limit(5).all()
        today=datetime.now(timezone.utc).date()
        start=datetime.combine(today,time.min).replace(tzinfo=timezone.utc)
        employee_stats={
            "farmers":Farmer.query.filter_by(assigned_employee_id=current_user.id,status="approved").count(),
            "debts_count":len(debt_rows),
            "debt_amount":sum((row["outstanding"] for row in debt_rows),0),
            "today_sales":db_sum(FuelDispense.total_amount,FuelDispense.employee_id==current_user.id,FuelDispense.status=="approved",FuelDispense.created_at>=start),
            "today_liters":db_sum(FuelDispense.liters,FuelDispense.employee_id==current_user.id,FuelDispense.status=="approved",FuelDispense.created_at>=start),
            "today_drums":db_sum(FuelDispense.drums,FuelDispense.employee_id==current_user.id,FuelDispense.status=="approved",FuelDispense.created_at>=start),
            "today_collected":float(__import__("app.extensions",fromlist=["db"]).db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0)).join(Document,FarmerPayment.document_id==Document.id).filter(FarmerPayment.employee_id==current_user.id,FarmerPayment.created_at>=start,Document.status!="reversed").scalar() or 0),
            "pending_supplies":FuelPurchase.query.filter_by(employee_id=current_user.id,status="submitted").count(),
            "available_liters":inventory_commitment()["stock_liters"],
        }
    settings=ProjectSettings.get()
    dashboard_template="dashboard/employee_theme2.html" if (not manager and current_user.is_employee and settings.employee_dashboard_theme=="water") else "dashboard/index.html"
    project_capacity=project_diesel_capacity() if dashboard_template=="dashboard/employee_theme2.html" else None
    return render_template(dashboard_template,manager=manager,employee_count=employee_count,recent_audits=recent_audits,employee_cashbox=employee_cashbox,employee_stats=employee_stats,employee_debtors=employee_debtors,employee_farmers=employee_farmers,employee_farmers_total=employee_farmers_total,employee_followups=employee_followups,employee_notifications=employee_notifications,summary=summary,inventory=inventory,pending_supplies=pending_supplies,pending_farmers=pending_farmers,unread_all=unread_all,trend_rows=trend_rows,tank_overview=tank_overview,project_capacity=project_capacity)

def db_sum(column,*conditions):
    return float(__import__("app.extensions",fromlist=["db"]).db.session.query(func.coalesce(func.sum(column),0)).filter(*conditions).scalar() or 0)

 
def operational_trend(employee_id=None):
    today=datetime.now(timezone.utc).date()
    start_day=today-timedelta(days=6)
    start_dt=datetime.combine(start_day,time.min).replace(tzinfo=timezone.utc)
    end_dt=datetime.combine(today,time.max).replace(tzinfo=timezone.utc)
    dq=FuelDispense.query.filter(
        FuelDispense.status=="approved",
        FuelDispense.created_at>=start_dt,
        FuelDispense.created_at<=end_dt,
    )
    pq=(FarmerPayment.query.join(Document,FarmerPayment.document_id==Document.id)
        .filter(FarmerPayment.created_at>=start_dt,FarmerPayment.created_at<=end_dt,Document.status!="reversed"))
    if employee_id is not None:
        dq=dq.filter(FuelDispense.employee_id==employee_id)
        pq=pq.filter(FarmerPayment.employee_id==employee_id)
    dispenses=dq.all()
    payments=pq.all()
    rows=[]
    for offset in range(6,-1,-1):
        day=today-timedelta(days=offset)
        d_liters=sum((float(row.liters or 0) for row in dispenses if row.created_at.date()==day),0.0)
        d_collected=sum((float(row.paid_amount or 0) for row in dispenses if row.created_at.astimezone(timezone.utc).date()==day),0.0)
        d_collected+=sum((float(row.amount or 0) for row in payments if row.created_at.astimezone(timezone.utc).date()==day),0.0)
        rows.append({"label":day.strftime("%d/%m"),"liters":d_liters,"collected":d_collected})
    max_liters=max((row["liters"] for row in rows),default=0)
    max_collected=max((row["collected"] for row in rows),default=0)
    for row in rows:
        row["liters_pct"]=round((row["liters"]/max_liters)*100,1) if max_liters else 0
        row["collected_pct"]=round((row["collected"]/max_collected)*100,1) if max_collected else 0
    return rows
