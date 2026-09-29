from decimal import Decimal
from sqlalchemy import func
from ..extensions import db
from ..models import Cashbox,Document,Farmer,FarmerPayment,FarmerPaymentAllocation,FuelDispense,FuelStockMovement,FuelTank,ProjectSettings,User
from .cashbox import post_transaction
from .documents import create_document
from .fuel import consume_fifo,current_stock_liters

def farmer_consumed_drums(farmer_id):
    value=db.session.query(func.coalesce(func.sum(FuelDispense.drums),0)).filter(FuelDispense.farmer_id==farmer_id,FuelDispense.status=="approved").scalar() or 0
    return Decimal(str(value))

def farmer_outstanding_amount(farmer_id):
    dispensed=db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(FuelDispense.farmer_id==farmer_id,FuelDispense.status=="approved").scalar() or 0
    paid=(
        db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(FarmerPayment.farmer_id==farmer_id,Document.status!="reversed")
        .scalar() or 0
    )
    return max(Decimal(str(dispensed))-Decimal(str(paid)),Decimal("0"))

def farmer_outstanding_credit_drums(farmer_id):
    dispenses=(FuelDispense.query.filter_by(farmer_id=farmer_id,status="approved").order_by(FuelDispense.created_at.asc(),FuelDispense.id.asc()).all())
    total=Decimal("0")
    for sale in dispenses:
        allocated=(
            db.session.query(func.coalesce(func.sum(FarmerPaymentAllocation.drums),0))
            .join(FarmerPayment,FarmerPaymentAllocation.payment_id==FarmerPayment.id)
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPaymentAllocation.dispense_id==sale.id,Document.status!="reversed")
            .scalar() or 0
        )
        total += max(Decimal(str(sale.credit_drums))-Decimal(str(allocated)),Decimal("0"))
    return total

def farmer_account(farmer):
    consumed=farmer_consumed_drums(farmer.id)
    outstanding=farmer_outstanding_amount(farmer.id)
    outstanding_drums=farmer_outstanding_credit_drums(farmer.id)
    return {
        "consumed_drums":consumed,
        "remaining_quota_drums":max(Decimal(str(farmer.quota_drums))-consumed,Decimal("0")),
        "outstanding_amount":outstanding,
        "outstanding_drums":outstanding_drums,
        "remaining_credit_drums":max(Decimal(str(farmer.credit_limit_drums))-outstanding_drums,Decimal("0")),
    }

def create_dispense(employee,farmer,tank_id,drums,sale_price_per_liter,paid_amount=0,notes=None):
    if farmer.status!="approved": raise ValueError("لا يمكن صرف الديزل لمزارع غير معتمد.")
    if farmer.assigned_employee_id!=employee.id: raise ValueError("المزارع غير تابع لهذا الموظف.")
    drums=Decimal(str(drums));price=Decimal(str(sale_price_per_liter));paid=Decimal(str(paid_amount or 0));settings=ProjectSettings.get()
    if drums<=0 or price<=0: raise ValueError("عدد الدباب وسعر اللتر يجب أن يكونا أكبر من صفر.")
    account=farmer_account(farmer)
    if drums>account["remaining_quota_drums"]: raise ValueError(f"المتبقي للمزارع من السقف هو {account['remaining_quota_drums']} دبة.")
    if paid<0: raise ValueError("المدفوع لا يمكن أن يكون سالبًا.")
    liters=drums*Decimal(str(settings.drum_liters))
    if liters>current_stock_liters(tank_id): raise ValueError("المخزون في الخزان لا يكفي لهذه العملية.")
    total=liters*price
    if paid>total: raise ValueError("المدفوع لا يمكن أن يتجاوز قيمة الصرف.")
    credit=total-paid
    credit_drums=(credit/(price*Decimal(str(settings.drum_liters)))) if price>0 else Decimal("0")
    if credit_drums>account["remaining_credit_drums"]: raise ValueError(f"المتبقي للمزارع من حد المديونية هو {account['remaining_credit_drums']} دبة.")
    document=create_document("DSP","سند صرف ديزل",employee.id,source_type="fuel_dispense")
    row=FuelDispense(document_id=document.id,farmer_id=farmer.id,employee_id=employee.id,tank_id=tank_id,liters=liters,drums=drums,sale_price_per_liter=price,total_amount=total,paid_amount=paid,credit_amount=credit,credit_drums=credit_drums,payment_mode="cash" if credit==0 else ("mixed" if paid>0 else "credit"),notes=notes,status="approved")
    db.session.add(row);db.session.flush();document.source_id=str(row.id)
    cost_amount=consume_fifo(tank_id,liters,row.id,employee.id);row.cost_amount=cost_amount;row.gross_profit=total-cost_amount
    db.session.add(FuelStockMovement(tank_id=tank_id,direction="OUT",movement_type="dispense",liters=liters,unit_cost=(cost_amount/liters if liters else 0),source_type="fuel_dispense",source_id=str(row.id),document_id=document.id,created_by_id=employee.id))
    from .compensation import apply_employee_compensation_snapshot
    apply_employee_compensation_snapshot(row,employee.employee_profile)
    from .accounting import post_sale
    post_sale(row,employee.id)
    if paid>0:
        cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
        if not cashbox: raise ValueError("لا يوجد صندوق فعال للموظف.")
        post_transaction(cashbox.id,"IN",paid,"farmer_sale_cash",employee.id,f"تحصيل فوري من {farmer.name}",document.id,"fuel_dispense",row.id)
    return row

def create_general_sale(employee,tank_id,drums,sale_price_per_liter,customer_name=None,notes=None):
    drums=Decimal(str(drums))
    price=Decimal(str(sale_price_per_liter))
    settings=ProjectSettings.get()
    if drums<=0 or price<=0:
        raise ValueError("عدد الدباب وسعر اللتر يجب أن يكونا أكبر من صفر.")
    liters=drums*Decimal(str(settings.drum_liters))
    if liters>current_stock_liters(tank_id):
        raise ValueError("المخزون في الخزان لا يكفي لهذه العملية.")
    total=liters*price
    document=create_document("DSP","سند بيع ديزل مباشر",employee.id,source_type="general_sale",notes=notes)
    row=FuelDispense(
        document_id=document.id,farmer_id=None,employee_id=employee.id,tank_id=tank_id,
        liters=liters,drums=drums,sale_price_per_liter=price,total_amount=total,
        paid_amount=total,credit_amount=Decimal("0"),credit_drums=Decimal("0"),
        payment_mode="cash",sale_type="general",customer_name=(customer_name or "").strip() or None,
        notes=notes,status="approved",
    )
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    cost_amount=consume_fifo(tank_id,liters,row.id,employee.id)
    row.cost_amount=cost_amount
    row.gross_profit=total-cost_amount
    db.session.add(FuelStockMovement(
        tank_id=tank_id,direction="OUT",movement_type="general_sale",liters=liters,
        unit_cost=(cost_amount/liters if liters else 0),source_type="general_sale",
        source_id=str(row.id),document_id=document.id,created_by_id=employee.id,
    ))
    from .compensation import apply_employee_compensation_snapshot
    apply_employee_compensation_snapshot(row,employee.employee_profile)
    from .accounting import post_sale
    post_sale(row,employee.id)
    cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    if not cashbox:
        raise ValueError("لا يوجد صندوق فعال للموظف.")
    post_transaction(cashbox.id,"IN",total,"general_sale_cash",employee.id,
                     f"بيع ديزل مباشر{': '+customer_name if customer_name else ''}",document.id,"general_sale",row.id)
    return row

def register_payment(employee,farmer,amount,payment_method="cash",reference=None,notes=None):
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("مبلغ السداد يجب أن يكون أكبر من صفر.")
    if farmer.status not in {"approved","suspended"}: raise ValueError("حساب المزارع غير متاح للتحصيل.")
    if farmer.assigned_employee_id!=employee.id: raise ValueError("المزارع غير تابع لهذا الموظف.")
    outstanding=farmer_outstanding_amount(farmer.id)
    if amount>outstanding: raise ValueError("مبلغ السداد أكبر من مديونية المزارع.")
    document=create_document("RCV","سند قبض من مزارع",employee.id,source_type="farmer_payment")
    row=FarmerPayment(document_id=document.id,farmer_id=farmer.id,employee_id=employee.id,amount=amount,payment_method=payment_method,reference=reference,notes=notes)
    db.session.add(row);db.session.flush();document.source_id=str(row.id)
    remaining=amount
    dispenses=(FuelDispense.query.filter_by(farmer_id=farmer.id,status="approved").order_by(FuelDispense.created_at.asc(),FuelDispense.id.asc()).with_for_update().all())
    settings=ProjectSettings.get()
    for sale in dispenses:
        if remaining<=0: break
        allocated=(
            db.session.query(func.coalesce(func.sum(FarmerPaymentAllocation.amount),0))
            .join(FarmerPayment,FarmerPaymentAllocation.payment_id==FarmerPayment.id)
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPaymentAllocation.dispense_id==sale.id,Document.status!="reversed")
            .scalar() or 0
        )
        remaining_credit=max(Decimal(str(sale.credit_amount))-Decimal(str(allocated)),Decimal("0"))
        if remaining_credit<=0: continue
        allocation=min(remaining,remaining_credit)
        drums=(allocation/(Decimal(str(sale.sale_price_per_liter))*Decimal(str(settings.drum_liters)))) if sale.sale_price_per_liter else Decimal("0")
        db.session.add(FarmerPaymentAllocation(payment_id=row.id,dispense_id=sale.id,amount=allocation,drums=drums))
        remaining-=allocation
    if remaining>Decimal("0.0005"): raise ValueError("تعذر توزيع كامل مبلغ السداد على المديونية.")
    cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    if not cashbox: raise ValueError("لا يوجد صندوق فعال للموظف.")
    post_transaction(cashbox.id,"IN",amount,"farmer_payment",employee.id,f"سداد من {farmer.name}",document.id,"farmer",farmer.id)
    from .accounting import post_payment
    post_payment(row,employee.id)
    return row


def farmer_unpaid_oldest_date(farmer_id):
    from datetime import datetime,timezone
    sales=FuelDispense.query.filter_by(
        farmer_id=farmer_id,status="approved"
    ).order_by(FuelDispense.created_at.asc(),FuelDispense.id.asc()).all()
    for sale in sales:
        allocated=(
            db.session.query(func.coalesce(func.sum(FarmerPaymentAllocation.amount),0))
            .join(FarmerPayment,FarmerPaymentAllocation.payment_id==FarmerPayment.id)
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPaymentAllocation.dispense_id==sale.id,Document.status!="reversed")
            .scalar() or 0
        )
        remaining=max(
            Decimal(str(sale.credit_amount))-Decimal(str(allocated)),
            Decimal("0")
        )
        if remaining>Decimal("0.0005"):
            return sale.created_at
    return None

def farmer_account_metrics(farmer,start=None):
    from datetime import datetime,timezone,time
    account=farmer_account(farmer)
    prior_balance=Decimal("0")
    if start:
        start_dt=datetime.combine(start,time.min).replace(tzinfo=timezone.utc)
        prior_credit=(
            db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0))
            .filter(FuelDispense.farmer_id==farmer.id,
                    FuelDispense.status=="approved",
                    FuelDispense.created_at<start_dt)
            .scalar() or 0
        )
        prior_paid=(
            db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPayment.farmer_id==farmer.id,
                    FarmerPayment.created_at<start_dt,
                    Document.status!="reversed")
            .scalar() or 0
        )
        prior_balance=max(
            Decimal(str(prior_credit))-Decimal(str(prior_paid)),
            Decimal("0")
        )

    oldest=farmer_unpaid_oldest_date(farmer.id)
    today=datetime.now(timezone.utc).date()
    debt_age_days=(today-oldest.date()).days if oldest else 0
    last_payment=(
        FarmerPayment.query
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed")
        .order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc())
        .first()
    )
    return {
        **account,
        "prior_balance":prior_balance,
        "last_payment":last_payment,
        "debt_age_days":max(debt_age_days,0),
    }
