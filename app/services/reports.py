from decimal import Decimal
from datetime import datetime,timezone,time
from sqlalchemy import func
from ..extensions import db
from ..models import Document,Farmer,FuelDispense,FuelStockMovement,Cashbox,EmployeeProfile,OperatingExpense,User,FarmerPayment
from .cashbox import balance
from .fuel import current_stock_liters

def project_summary():
    sales=db.session.query(func.coalesce(func.sum(FuelDispense.total_amount),0)).filter(FuelDispense.status=="approved").scalar() or 0
    cogs=db.session.query(func.coalesce(func.sum(FuelDispense.cost_amount),0)).filter(FuelDispense.status=="approved").scalar() or 0
    expenses=db.session.query(func.coalesce(func.sum(OperatingExpense.amount),0)).filter(OperatingExpense.status=="approved").scalar() or 0
    approved_farmers=Farmer.query.filter_by(status="approved").count()
    debt=db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(FuelDispense.status=="approved").scalar() or 0
    payments=(
        db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(Document.status!="reversed")
        .scalar() or 0
    )
    return {"sales":Decimal(str(sales)),"cogs":Decimal(str(cogs)),"gross_profit":Decimal(str(sales))-Decimal(str(cogs)),"expenses":Decimal(str(expenses)),"operating_profit":Decimal(str(sales))-Decimal(str(cogs))-Decimal(str(expenses)),"farmers":approved_farmers,"receivables":max(Decimal(str(debt))-Decimal(str(payments)),Decimal("0")),"stock_liters":current_stock_liters()}

def farmer_debts():
    rows=[]
    for farmer in Farmer.query.filter(Farmer.status.in_(["approved","suspended"])).order_by(Farmer.name):
        sold=db.session.query(func.coalesce(func.sum(FuelDispense.total_amount),0)).filter(FuelDispense.farmer_id==farmer.id,FuelDispense.status=="approved").scalar() or 0
        credit=db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(FuelDispense.farmer_id==farmer.id,FuelDispense.status=="approved").scalar() or 0
        paid=(
            db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed")
            .scalar() or 0
        )
        outstanding=max(Decimal(str(credit))-Decimal(str(paid)),Decimal("0"))
        if outstanding>0: rows.append({"farmer":farmer,"sales":Decimal(str(sold)),"outstanding":outstanding})
    return rows

def employee_performance():
    rows=[]
    for employee in User.query.filter_by(is_employee=True,active=True).order_by(User.display_name):
        sales=db.session.query(func.coalesce(func.sum(FuelDispense.total_amount),0)).filter(FuelDispense.employee_id==employee.id,FuelDispense.status=="approved").scalar() or 0
        cogs=db.session.query(func.coalesce(func.sum(FuelDispense.cost_amount),0)).filter(FuelDispense.employee_id==employee.id,FuelDispense.status=="approved").scalar() or 0
        box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
        farmer_count=Farmer.query.filter_by(assigned_employee_id=employee.id,status="approved").count()
        rows.append({"employee":employee,"sales":Decimal(str(sales)),"cogs":Decimal(str(cogs)),"profit":Decimal(str(sales))-Decimal(str(cogs)),"cashbox_balance":balance(box.id) if box else Decimal("0"),"farmer_count":farmer_count})
    return rows

def inventory_commitment():
    committed=db.session.query(func.coalesce(func.sum(Farmer.quota_drums),0)).filter(Farmer.status=="approved").scalar() or 0
    consumed=db.session.query(func.coalesce(func.sum(FuelDispense.drums),0)).filter(FuelDispense.status=="approved").scalar() or 0
    drum=Decimal(str(__import__("app.models",fromlist=["ProjectSettings"]).ProjectSettings.get().drum_liters))
    remaining_drums=max(Decimal(str(committed))-Decimal(str(consumed)),Decimal("0"))
    stock=current_stock_liters();committed_liters=remaining_drums*drum
    return {"stock_liters":stock,"committed_liters":committed_liters,"free_liters":max(stock-committed_liters,Decimal("0")),"shortage_liters":max(committed_liters-stock,Decimal("0"))}


def employee_operations(employee_id,start=None,end=None):
    from datetime import datetime,timezone,time
    from ..models import FuelPurchase
    result={"dispenses":[],"payments":[],"supplies":[],"sales":Decimal("0"),"liters":Decimal("0"),"drums":Decimal("0"),"collected":Decimal("0"),"payment_collected":Decimal("0"),"instant_collected":Decimal("0"),"credit":Decimal("0"),"supplied_liters":Decimal("0")}
    dq=FuelDispense.query.filter_by(employee_id=employee_id).order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc())
    pq=FarmerPayment.query.join(Document,FarmerPayment.document_id==Document.id).filter(FarmerPayment.employee_id==employee_id).order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc())
    sq=FuelPurchase.query.filter_by(employee_id=employee_id).order_by(FuelPurchase.submitted_at.desc(),FuelPurchase.id.desc())
    if start:
        dt=datetime.combine(start,time.min).replace(tzinfo=timezone.utc)
        dq=dq.filter(FuelDispense.created_at>=dt);pq=pq.filter(FarmerPayment.created_at>=dt);sq=sq.filter(FuelPurchase.submitted_at>=dt)
    if end:
        dt=datetime.combine(end,time.max).replace(tzinfo=timezone.utc)
        dq=dq.filter(FuelDispense.created_at<=dt);pq=pq.filter(FarmerPayment.created_at<=dt);sq=sq.filter(FuelPurchase.submitted_at<=dt)
    result["dispenses"]=dq.limit(300).all()
    result["payments"]=pq.limit(300).all()
    result["supplies"]=sq.limit(300).all()
    approved=[row for row in result["dispenses"] if row.status=="approved"]
    approved_supplies=[row for row in result["supplies"] if row.status=="approved"]
    result["sales"]=sum((Decimal(str(row.total_amount)) for row in approved),Decimal("0"))
    result["liters"]=sum((Decimal(str(row.liters)) for row in approved),Decimal("0"))
    result["drums"]=sum((Decimal(str(row.drums)) for row in approved),Decimal("0"))
    result["credit"]=sum((Decimal(str(row.credit_amount)) for row in approved),Decimal("0"))
    result["instant_collected"]=sum((Decimal(str(row.paid_amount)) for row in approved),Decimal("0"))
    result["payment_collected"]=sum((Decimal(str(row.amount)) for row in result["payments"] if row.document.status!="reversed"),Decimal("0"))
    result["collected"]=result["instant_collected"]+result["payment_collected"]
    result["supplied_liters"]=sum((Decimal(str(row.liters)) for row in approved_supplies),Decimal("0"))
    return result
