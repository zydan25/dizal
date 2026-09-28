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
