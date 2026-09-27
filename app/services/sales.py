from decimal import Decimal
from sqlalchemy import func
from ..extensions import db
from ..models import Farmer,FarmerPayment,FuelDispense,FuelStockMovement,FuelTank,ProjectSettings
from ..models import Cashbox
from .cashbox import post_transaction
from .documents import create_document
from .fuel import current_stock_liters

def farmer_consumed_drums(farmer_id):
    value=db.session.query(func.coalesce(func.sum(FuelDispense.drums),0)).filter(FuelDispense.farmer_id==farmer_id,FuelDispense.status=="approved").scalar() or 0
    return Decimal(str(value))

def farmer_outstanding_amount(farmer_id):
    dispensed=db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(FuelDispense.farmer_id==farmer_id,FuelDispense.status=="approved").scalar() or 0
    paid=db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0)).filter(FarmerPayment.farmer_id==farmer_id).scalar() or 0
    return max(Decimal(str(dispensed))-Decimal(str(paid)),Decimal("0"))

def farmer_outstanding_credit_drums(farmer):
    total=Decimal("0")
    for sale in FuelDispense.query.filter_by(farmer_id=farmer.id,status="approved").all():
        if sale.credit_amount and sale.total_amount:
            total += Decimal(str(sale.credit_drums)) * (Decimal(str(max(sale.credit_amount-farmer_payment_allocated(sale.id),0))) / Decimal(str(sale.credit_amount)))
    # Phase 5 uses value-based debt conversion for the simple account; allocations become explicit in a later phase.
    settings=ProjectSettings.get()
    per_drum=Decimal(str(settings.default_sale_price_per_liter))*Decimal(str(settings.drum_liters))
    if per_drum<=0:return Decimal("0")
    outstanding=farmer_outstanding_amount(farmer.id)
    return outstanding/per_drum

def farmer_payment_allocated(_dispense_id):
    return Decimal("0")

def farmer_account(farmer):
    settings=ProjectSettings.get()
    consumed=farmer_consumed_drums(farmer.id)
    outstanding=farmer_outstanding_amount(farmer.id)
    per_drum=Decimal(str(settings.default_sale_price_per_liter))*Decimal(str(settings.drum_liters))
    outstanding_drums=(outstanding/per_drum) if per_drum>0 else Decimal("0")
    return {
        "consumed_drums":consumed,
        "remaining_quota_drums":max(Decimal(str(farmer.quota_drums))-consumed,Decimal("0")),
        "outstanding_amount":outstanding,
        "outstanding_drums":outstanding_drums,
        "remaining_credit_drums":max(Decimal(str(farmer.credit_limit_drums))-outstanding_drums,Decimal("0")),
    }

def create_dispense(employee,farmer,tank_id,drums,sale_price_per_liter,paid_amount=0,notes=None):
    if farmer.status!="approved":
        raise ValueError("لا يمكن صرف الديزل لمزارع غير معتمد.")
    drums=Decimal(str(drums))
    price=Decimal(str(sale_price_per_liter))
    paid=Decimal(str(paid_amount or 0))
    settings=ProjectSettings.get()
    if drums<=0 or price<=0: raise ValueError("عدد الدباب وسعر اللتر يجب أن يكونا أكبر من صفر.")
    account=farmer_account(farmer)
    if drums>account["remaining_quota_drums"]:
        raise ValueError(f"المتبقي للمزارع من السقف هو {account['remaining_quota_drums']} دبة.")
    if paid<0: raise ValueError("المدفوع لا يمكن أن يكون سالبًا.")
    liters=drums*Decimal(str(settings.drum_liters))
    if liters>current_stock_liters(tank_id):
        raise ValueError("المخزون في الخزان لا يكفي لهذه العملية.")
    total=liters*price
    if paid>total: raise ValueError("المدفوع لا يمكن أن يتجاوز قيمة الصرف.")
    credit=total-paid
    credit_drums=(credit/(price*Decimal(str(settings.drum_liters)))) if price>0 else Decimal("0")
    if credit_drums>account["remaining_credit_drums"]:
        raise ValueError(f"المتبقي للمزارع من حد المديونية هو {account['remaining_credit_drums']} دبة.")
    document=create_document("DSP","سند صرف ديزل",employee.id,source_type="fuel_dispense")
    row=FuelDispense(document_id=document.id,farmer_id=farmer.id,employee_id=employee.id,tank_id=tank_id,liters=liters,drums=drums,sale_price_per_liter=price,total_amount=total,paid_amount=paid,credit_amount=credit,credit_drums=credit_drums,payment_mode="cash" if credit==0 else ("mixed" if paid>0 else "credit"),notes=notes,status="approved")
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    db.session.add(FuelStockMovement(tank_id=tank_id,direction="OUT",movement_type="dispense",liters=liters,unit_cost=None,source_type="fuel_dispense",source_id=str(row.id),document_id=document.id,created_by_id=employee.id))
    if paid>0:
        cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
        if not cashbox: raise ValueError("لا يوجد صندوق فعال للموظف.")
        post_transaction(cashbox.id,"IN",paid,"farmer_sale_cash",employee.id,f"تحصيل فوري من {farmer.name}",document.id,"fuel_dispense",row.id)
    return row

def register_payment(employee,farmer,amount,payment_method="cash",reference=None,notes=None):
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("مبلغ السداد يجب أن يكون أكبر من صفر.")
    outstanding=farmer_outstanding_amount(farmer.id)
    if amount>outstanding: raise ValueError("مبلغ السداد أكبر من مديونية المزارع.")
    document=create_document("RCV","سند قبض من مزارع",employee.id,source_type="farmer_payment")
    row=FarmerPayment(document_id=document.id,farmer_id=farmer.id,employee_id=employee.id,amount=amount,payment_method=payment_method,reference=reference,notes=notes)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    if not cashbox: raise ValueError("لا يوجد صندوق فعال للموظف.")
    post_transaction(cashbox.id,"IN",amount,"farmer_payment",employee.id,f"سداد من {farmer.name}",document.id,"farmer",farmer.id)
    return row
