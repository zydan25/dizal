from decimal import Decimal
from datetime import datetime,timezone
from sqlalchemy import func
from ..extensions import db
from ..models import Cashbox,FuelPurchase,FuelStockMovement,FuelTank
from .cashbox import post_transaction
from .documents import create_document

def current_stock_liters(tank_id=None):
    query_in=db.session.query(func.coalesce(func.sum(FuelStockMovement.liters),0)).filter(FuelStockMovement.direction=="IN")
    query_out=db.session.query(func.coalesce(func.sum(FuelStockMovement.liters),0)).filter(FuelStockMovement.direction=="OUT")
    if tank_id:
        query_in=query_in.filter(FuelStockMovement.tank_id==tank_id)
        query_out=query_out.filter(FuelStockMovement.tank_id==tank_id)
    inbound=query_in.scalar() or 0
    outbound=query_out.scalar() or 0
    return Decimal(str(inbound))-Decimal(str(outbound))

def create_purchase(employee_id,tank_id,purchase_date,supplier_name,liters,diesel_amount,delivery_fee=0,other_fee=0,created_by_id=None,notes=None,status="submitted"):
    liters=Decimal(str(liters))
    diesel_amount=Decimal(str(diesel_amount))
    delivery_fee=Decimal(str(delivery_fee or 0))
    other_fee=Decimal(str(other_fee or 0))
    if liters<=0: raise ValueError("كمية الديزل يجب أن تكون أكبر من صفر.")
    if diesel_amount<0 or delivery_fee<0 or other_fee<0: raise ValueError("القيم المالية لا يمكن أن تكون سالبة.")
    tank=FuelTank.query.get(tank_id)
    if not tank or not tank.is_active: raise ValueError("الخزان غير موجود أو غير فعال.")
    landed=diesel_amount+delivery_fee+other_fee
    unit=landed/liters
    document=create_document("SUP","سند توريد ديزل",created_by_id,source_type="fuel_purchase",notes=notes,status=status)
    row=FuelPurchase(employee_id=employee_id,tank_id=tank_id,purchase_date=purchase_date,supplier_name=supplier_name,liters=liters,diesel_amount=diesel_amount,delivery_fee=delivery_fee,other_fee=other_fee,landed_cost=landed,unit_cost=unit,status=status,document_id=document.id,notes=notes)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    return row

def attach_proof(purchase,attachment):
    from ..models import DocumentAttachment
    row=DocumentAttachment(document_id=purchase.document_id,**attachment)
    db.session.add(row)
    return row

def approve_purchase(purchase,approved_by_id):
    if purchase.status!="submitted":
        raise ValueError("التوريد ليس في حالة انتظار اعتماد.")
    tank=FuelTank.query.get(purchase.tank_id)
    if not tank or not tank.is_active:
        raise ValueError("الخزان غير فعال.")
    cashbox=Cashbox.query.filter_by(owner_user_id=purchase.employee_id,box_type="employee",is_active=True).first()
    if not cashbox:
        raise ValueError("لا يوجد صندوق فعال للموظف.")
    post_transaction(cashbox.id,"OUT",purchase.landed_cost,"fuel_purchase",approved_by_id,f"شراء {purchase.liters} لتر ديزل",purchase.document_id,"fuel_purchase",purchase.id)
    db.session.add(FuelStockMovement(tank_id=purchase.tank_id,direction="IN",movement_type="purchase",liters=purchase.liters,unit_cost=purchase.unit_cost,source_type="fuel_purchase",source_id=str(purchase.id),document_id=purchase.document_id,created_by_id=approved_by_id))
    purchase.status="approved"
    purchase.approved_at=datetime.now(timezone.utc)
    purchase.approved_by_id=approved_by_id
    purchase.document.status="approved"
    purchase.document.approved_by_id=approved_by_id
    db.session.flush()
