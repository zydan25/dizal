from decimal import Decimal
from datetime import datetime,timezone,time
from sqlalchemy import func
from ..extensions import db
from ..models import (
    Document,Farmer,FuelDispense,FuelPurchase,FuelStockMovement,FuelStockLayer,Cashbox,
    CashboxTransaction,EmployeeProfile,EmployeeSettlement,OperatingExpense,User,
    FarmerPayment,CapitalContribution,CapitalAllocation,FuelTank,ProjectSettings
)
from .cashbox import balance
from .fuel import current_stock_liters
from .capital import central_cashbox
from .compensation import compensation_label


ZERO=Decimal("0")


def _decimal(value):
    return Decimal(str(value or 0))


def _date_window(start=None,end=None):
    conditions=[]
    if start:
        conditions.append(FuelDispense.created_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc))
    if end:
        conditions.append(FuelDispense.created_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc))
    return conditions


def calculate_employee_compensation(profile,sales,cogs,liters,drums,currency="ريال"):
    """Calculate the employee's earned compensation from the supplied period totals.

    Variable compensation is earned from approved sales in the period. A fixed
    salary is returned as the configured salary value for the settlement/report
    period; it is not automatically accrued into the all-time project P&L until
    a salary settlement is approved.
    """
    sales=_decimal(sales)
    cogs=_decimal(cogs)
    liters=_decimal(liters)
    drums=_decimal(drums)
    value=_decimal(profile.salary_value if profile else 0)
    salary_type=(profile.salary_type if profile else "fixed") or "fixed"
    gross_profit=sales-cogs

    if salary_type=="per_liter":
        earned=liters*value
        label=f"{value} {currency}/لتر"
    elif salary_type=="per_drum":
        earned=drums*value
        label=f"{value} {currency}/دبة"
    elif salary_type in {"percent_profit","commission"}:
        earned=max(gross_profit,ZERO)*value/Decimal("100")
        label=f"{value}% من الربح"
    else:
        earned=value
        label=f"راتب ثابت {value} {currency}"

    return {
        "salary_type":salary_type,
        "salary_value":value,
        "earned":earned,
        "label":label,
        "gross_profit":gross_profit,
    }


def _employee_dispense_aggregate(employee_id=None,start=None,end=None):
    query=db.session.query(
        func.coalesce(func.sum(FuelDispense.total_amount),0),
        func.coalesce(func.sum(FuelDispense.cost_amount),0),
        func.coalesce(func.sum(FuelDispense.liters),0),
        func.coalesce(func.sum(FuelDispense.drums),0),
        func.coalesce(func.sum(FuelDispense.credit_amount),0),
        func.coalesce(func.sum(FuelDispense.paid_amount),0),
        func.coalesce(func.sum(FuelDispense.employee_commission_amount),0),
    ).filter(FuelDispense.status=="approved")
    if employee_id is not None:
        query=query.filter(FuelDispense.employee_id==employee_id)
    for condition in _date_window(start,end):
        query=query.filter(condition)
    sales,cogs,liters,drums,credit,paid,commission_earned=query.one()
    return {
        "sales":_decimal(sales),
        "cogs":_decimal(cogs),
        "liters":_decimal(liters),
        "drums":_decimal(drums),
        "credit":_decimal(credit),
        "instant_collected":_decimal(paid),
        "commission_earned":_decimal(commission_earned),
    }


def _approved_settlement_total(employee_ids=None,start=None,end=None,compensation_types=None):
    query=db.session.query(func.coalesce(func.sum(EmployeeSettlement.employee_salary),0)).filter(
        EmployeeSettlement.status=="approved"
    )
    if employee_ids is not None:
        ids=list(employee_ids)
        if not ids:
            return ZERO
        query=query.filter(EmployeeSettlement.employee_id.in_(ids))
    if start:
        query=query.filter(EmployeeSettlement.period_end>=start)
    if end:
        query=query.filter(EmployeeSettlement.period_start<=end)
    if compensation_types:
        query=query.filter(EmployeeSettlement.compensation_type_snapshot.in_(list(compensation_types)))
    return _decimal(query.scalar())


def employee_compensation(employee,start=None,end=None):
    totals=_employee_dispense_aggregate(employee.id,start,end)
    profile=employee.employee_profile
    settings=ProjectSettings.get()
    salary_type=(profile.salary_type if profile else "fixed") or "fixed"
    value=_decimal(profile.salary_value if profile else 0)
    if totals["commission_earned"]>ZERO:
        earned=totals["commission_earned"]
        label="عمولة/استحقاق مثبت بقيمة كل عملية"
    elif salary_type=="fixed":
        earned=value
        label=compensation_label(salary_type,value,settings.currency)
    else:
        earned=ZERO
        label=compensation_label(salary_type,value,settings.currency)
    result={
        "salary_type":salary_type,
        "salary_value":value,
        "earned":earned,
        "label":label,
        "gross_profit":totals["sales"]-totals["cogs"],
    }
    result.update(totals)
    return result


def project_summary():
    sales=_decimal(db.session.query(func.coalesce(func.sum(FuelDispense.total_amount),0)).filter(FuelDispense.status=="approved").scalar())
    cogs=_decimal(db.session.query(func.coalesce(func.sum(FuelDispense.cost_amount),0)).filter(FuelDispense.status=="approved").scalar())
    expenses=_decimal(db.session.query(func.coalesce(func.sum(OperatingExpense.amount),0)).filter(OperatingExpense.status=="approved").scalar())
    gross_profit=sales-cogs

    # Aggregate all variable employee compensation from ALL approved dispenses;
    # this intentionally does not use the 300-row presentation limit.
    aggregate_rows=db.session.query(
        FuelDispense.employee_id,
        func.coalesce(func.sum(FuelDispense.total_amount),0),
        func.coalesce(func.sum(FuelDispense.cost_amount),0),
        func.coalesce(func.sum(FuelDispense.liters),0),
        func.coalesce(func.sum(FuelDispense.drums),0),
        func.coalesce(func.sum(FuelDispense.employee_commission_amount),0),
    ).filter(FuelDispense.status=="approved").group_by(FuelDispense.employee_id).all()
    aggregate_map={
        row[0]:{
            "sales":_decimal(row[1]),
            "cogs":_decimal(row[2]),
            "liters":_decimal(row[3]),
            "drums":_decimal(row[4]),
            "commission_earned":_decimal(row[5]),
        }
        for row in aggregate_rows
    }

    employees=User.query.filter_by(is_employee=True).all()
    fixed_ids=[]
    employee_compensation_rows=[]
    variable_commission_earned=ZERO
    for employee in employees:
        profile=employee.employee_profile
        totals=aggregate_map.get(
            employee.id,
            {"sales":ZERO,"cogs":ZERO,"liters":ZERO,"drums":ZERO,"commission_earned":ZERO},
        )
        salary_type=(profile.salary_type if profile else "fixed") or "fixed"
        value=_decimal(profile.salary_value if profile else 0)
        earned=totals["commission_earned"]
        variable_commission_earned+=earned
        if salary_type=="fixed":
            fixed_ids.append(employee.id)
            label=compensation_label(salary_type,value,ProjectSettings.get().currency)
        else:
            label="عمولة/استحقاق مثبت بقيمة كل عملية"
        employee_compensation_rows.append({
            "employee":employee,
            "sales":totals["sales"],
            "cogs":totals["cogs"],
            "liters":totals["liters"],
            "drums":totals["drums"],
            "gross_profit":totals["sales"]-totals["cogs"],
            "commission_earned":totals["commission_earned"],
            "earned":earned,
            "salary_type":salary_type,
            "label":label,
        })

    # Fixed salaries are recognized from approved settlements. Variable
    # compensation is accrued from approved sales, so paying a commission does
    # not create a second expense in this management report.
    fixed_salary_recognized=_approved_settlement_total(fixed_ids,compensation_types={"fixed"})
    employee_compensation_expense=variable_commission_earned+fixed_salary_recognized
    net_profit=gross_profit-expenses-employee_compensation_expense

    approved_farmers=Farmer.query.filter_by(status="approved").count()
    debt=_decimal(db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(FuelDispense.status=="approved").scalar())
    payments=_decimal(
        db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(Document.status!="reversed").scalar()
    )
    receivables=max(debt-payments,ZERO)

    settings=ProjectSettings.get()
    stock=current_stock_liters()
    stock_cost=_decimal(
        db.session.query(
            func.coalesce(func.sum(FuelStockLayer.remaining_liters*FuelStockLayer.unit_cost),0)
        ).scalar()
    )
    sale_price=_decimal(settings.default_sale_price_per_liter)
    stock_sale_value=stock*sale_price
    stock_unrealized_margin=stock_sale_value-stock_cost
    drum=_decimal(settings.drum_liters)
    stock_drums=stock/drum if drum else ZERO
    avg_stock_cost=stock_cost/stock if stock else ZERO

    capital_contributed=_decimal(
        db.session.query(func.coalesce(func.sum(CapitalContribution.amount),0))
        .filter(CapitalContribution.status=="approved").scalar()
    )
    allocated_capital=_decimal(
        db.session.query(func.coalesce(func.sum(CapitalAllocation.amount),0))
        .join(Document,CapitalAllocation.document_id==Document.id)
        .filter(Document.status!="reversed").scalar()
    )

    central=Cashbox.query.filter_by(box_type="central",is_active=True).first()
    central_cash=balance(central.id) if central else ZERO
    employee_boxes=Cashbox.query.filter_by(box_type="employee",is_active=True).all()
    employee_cash=sum((balance(box.id) for box in employee_boxes),ZERO)
    cash_available=central_cash+employee_cash

    inventory=inventory_commitment()

    tank_rows=[]
    tank_alerts=[]
    for tank in FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).all():
        tank_stock=current_stock_liters(tank.id)
        capacity=_decimal(tank.capacity_liters)
        percent=(tank_stock/capacity*Decimal("100")) if capacity>0 else ZERO
        row={"tank":tank,"stock":tank_stock,"capacity":capacity,"percent":percent}
        tank_rows.append(row)
        if capacity>0 and tank_stock>capacity:
            tank_alerts.append({"type":"danger","title":f"الخزان {tank.name} تجاوز السعة","message":f"المخزون {tank_stock} لتر مقابل سعة {capacity} لتر.","url":None})
        elif capacity>0 and percent>=Decimal("90"):
            tank_alerts.append({"type":"warning","title":f"الخزان {tank.name} قريب من السعة","message":f"امتلاء الخزان {percent.quantize(Decimal('0.1'))}%.","url":None})

    alerts=[]
    minimum=_decimal(settings.minimum_stock_liters)
    if stock<=ZERO:
        alerts.append({"type":"danger","title":"المخزون نفد","message":"لا يوجد ديزل متاح في المخزون الحالي.","url":"/fuel/stock"})
    elif minimum>ZERO and stock<=minimum:
        alerts.append({"type":"warning","title":"المخزون منخفض","message":f"المخزون {stock} لتر، والحد الأدنى {minimum} لتر.","url":"/fuel/stock"})
    if inventory["shortage_liters"]>ZERO:
        alerts.append({"type":"danger","title":"عجز في تغطية التزامات المزارعين","message":f"العجز {inventory['shortage_liters']} لتر.","url":"/fuel/stock"})
    alerts.extend(tank_alerts)

    return {
        "sales":sales,
        "cogs":cogs,
        "gross_profit":gross_profit,
        "expenses":expenses,
        "employee_commission":variable_commission_earned,
        "fixed_salary_recognized":fixed_salary_recognized,
        "employee_compensation_expense":employee_compensation_expense,
        "operating_profit":net_profit,
        "net_profit":net_profit,
        "farmers":approved_farmers,
        "receivables":receivables,
        "stock_liters":stock,
        "stock_drums":stock_drums,
        "stock_cost_value":stock_cost,
        "stock_sale_value":stock_sale_value,
        "stock_unrealized_margin":stock_unrealized_margin,
        "stock_average_cost_per_liter":avg_stock_cost,
        "stock_sale_price_per_liter":sale_price,
        "capital_contributed":capital_contributed,
        "allocated_capital":allocated_capital,
        "unallocated_capital":max(capital_contributed-allocated_capital,ZERO),
        "central_cash":central_cash,
        "employee_cash":employee_cash,
        "cash_available":cash_available,
        "gross_margin_pct":(gross_profit/sales*Decimal("100")) if sales else ZERO,
        "net_margin_pct":(net_profit/sales*Decimal("100")) if sales else ZERO,
        "employee_rows":employee_compensation_rows,
        "tank_rows":tank_rows,
        "alerts":alerts,
    }


def farmer_debts():
    rows=[]
    for farmer in Farmer.query.filter(Farmer.status.in_(["approved","suspended"])).order_by(Farmer.name):
        sold=_decimal(db.session.query(func.coalesce(func.sum(FuelDispense.total_amount),0)).filter(
            FuelDispense.farmer_id==farmer.id,FuelDispense.status=="approved"
        ).scalar())
        credit=_decimal(db.session.query(func.coalesce(func.sum(FuelDispense.credit_amount),0)).filter(
            FuelDispense.farmer_id==farmer.id,FuelDispense.status=="approved"
        ).scalar())
        paid=_decimal(
            db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed")
            .scalar()
        )
        outstanding=max(credit-paid,ZERO)
        if outstanding>ZERO:
            rows.append({"farmer":farmer,"sales":sold,"outstanding":outstanding})
    return rows


def employee_performance():
    rows=[]
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name)
    for employee in employees:
        totals=_employee_dispense_aggregate(employee.id)
        profile=employee.employee_profile
        salary_type=(profile.salary_type if profile else "fixed") or "fixed"
        value=_decimal(profile.salary_value if profile else 0)
        variable_types={"per_liter","per_drum","percent_profit","commission"}
        earned=totals["commission_earned"] if salary_type!="fixed" else value
        label=compensation_label(salary_type,value,ProjectSettings.get().currency)
        box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
        paid=_approved_settlement_total(
            [employee.id],
            compensation_types=variable_types if salary_type!="fixed" else {"fixed"},
        )
        farmer_count=Farmer.query.filter_by(assigned_employee_id=employee.id,status="approved").count()
        outstanding=max(totals["commission_earned"]-paid,ZERO) if salary_type!="fixed" else ZERO
        rows.append({
            "employee":employee,
            "sales":totals["sales"],
            "cogs":totals["cogs"],
            "profit":totals["sales"]-totals["cogs"],
            "gross_profit":totals["sales"]-totals["cogs"],
            "liters":totals["liters"],
            "drums":totals["drums"],
            "employee_commission":totals["commission_earned"],
            "salary":paid if salary_type=="fixed" else ZERO,
            "compensation_earned":totals["commission_earned"],

            "compensation_paid":paid,
            "compensation_outstanding":outstanding,
            "net_contribution":totals["sales"]-totals["cogs"]-totals["commission_earned"],
            "commission_label":label,
            "salary_type":salary_type,
            "cashbox_balance":balance(box.id) if box else ZERO,
            "farmer_count":farmer_count,
        })
    return rows


def employee_finance_summary(employee,operations=None):
    if operations is None:
        operations=employee_operations(employee.id)
    settings=ProjectSettings.get()
    profile=employee.employee_profile
    salary_type=(profile.salary_type if profile else "fixed") or "fixed"
    value=_decimal(profile.salary_value if profile else 0)
    if salary_type=="fixed":
        earned=value
        label=compensation_label(salary_type,value,settings.currency)
    else:
        earned=_decimal(operations.get("commission_earned"))
        label=f"استحقاق مثبت على العمليات · {compensation_label(salary_type,value,settings.currency)}"
    from ..models import CapitalAllocation
    capital=_decimal(
        db.session.query(func.coalesce(func.sum(CapitalAllocation.amount),0))
        .join(Document,CapitalAllocation.document_id==Document.id)
        .filter(CapitalAllocation.employee_id==employee.id,Document.status!="reversed").scalar()
    )
    box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    employee_box_balance=balance(box.id) if box else ZERO

    stock=current_stock_liters()
    drum=_decimal(settings.drum_liters)
    sale_price=_decimal(settings.default_sale_price_per_liter)
    remaining_cost=_decimal(
        db.session.query(func.coalesce(func.sum(FuelStockLayer.remaining_liters*FuelStockLayer.unit_cost),0)).scalar()
    )
    average_stock_cost=remaining_cost/stock if stock else ZERO
    forecast_sales=stock*sale_price
    forecast_gross_profit=stock*(sale_price-average_stock_cost)
    purchased_cost=_decimal(
        db.session.query(func.coalesce(func.sum(FuelPurchase.landed_cost),0))
        .filter(FuelPurchase.employee_id==employee.id,FuelPurchase.status=="approved").scalar()
    )

    return {
        "capital_delivered":capital,
        "cashbox_balance":employee_box_balance,
        "gross_profit":operations["sales"]-operations["cogs"],
        "employee_commission":earned if salary_type!="fixed" else ZERO,
        "salary":earned if salary_type=="fixed" else ZERO,
        "compensation_earned":earned,
        "project_profit_estimate":operations["sales"]-operations["cogs"]-earned,
        "commission_label":label,
        "salary_type":salary_type,
        "salary_value":value,
        "purchased_cost":purchased_cost,
        "stock_liters":stock,
        "stock_drums":stock/drum if drum else ZERO,
        "sold_liters":operations["liters"],
        "sold_drums":operations["drums"],
        "forecast_sales_value":forecast_sales,
        "forecast_gross_profit":forecast_gross_profit,
        "forecast_stock_cost":remaining_cost,
        "note":"الراتب/العمولة محسوب حسب إعداد الموظف. رأس المال المُسلَّم ليس بالضرورة نقدًا متبقيًا؛ قد يتحول إلى مخزون أو مشتريات.",
    }


def inventory_commitment():
    settings=ProjectSettings.get()
    committed=_decimal(
        db.session.query(func.coalesce(func.sum(Farmer.quota_drums),0))
        .filter(Farmer.status=="approved").scalar()
    )
    consumed=_decimal(
        db.session.query(func.coalesce(func.sum(FuelDispense.drums),0))
        .filter(FuelDispense.status=="approved").scalar()
    )
    drum=_decimal(settings.drum_liters)
    remaining_drums=max(committed-consumed,ZERO)
    stock=current_stock_liters()
    committed_liters=remaining_drums*drum
    return {
        "stock_liters":stock,
        "committed_drums":remaining_drums,
        "committed_liters":committed_liters,
        "free_liters":max(stock-committed_liters,ZERO),
        "shortage_liters":max(committed_liters-stock,ZERO),
        "minimum_stock_liters":_decimal(settings.minimum_stock_liters),
    }


def employee_operations(employee_id,start=None,end=None):
    from ..models import FuelPurchase
    result={
        "dispenses":[],"payments":[],"supplies":[],
        "sales":ZERO,"cogs":ZERO,"liters":ZERO,"drums":ZERO,
        "collected":ZERO,"payment_collected":ZERO,"instant_collected":ZERO,
        "credit":ZERO,"supplied_liters":ZERO,
    }
    conditions=_date_window(start,end)
    dq=FuelDispense.query.filter(FuelDispense.employee_id==employee_id).order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc())
    pq=(FarmerPayment.query.join(Document,FarmerPayment.document_id==Document.id)
        .filter(FarmerPayment.employee_id==employee_id)
        .order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc()))
    sq=FuelPurchase.query.filter(FuelPurchase.employee_id==employee_id).order_by(FuelPurchase.submitted_at.desc(),FuelPurchase.id.desc())
    if start:
        dt=datetime.combine(start,time.min).replace(tzinfo=timezone.utc)
        dq=dq.filter(FuelDispense.created_at>=dt);pq=pq.filter(FarmerPayment.created_at>=dt);sq=sq.filter(FuelPurchase.submitted_at>=dt)
    if end:
        dt=datetime.combine(end,time.max).replace(tzinfo=timezone.utc)
        dq=dq.filter(FuelDispense.created_at<=dt);pq=pq.filter(FarmerPayment.created_at<=dt);sq=sq.filter(FuelPurchase.submitted_at<=dt)

    result["dispenses"]=dq.limit(300).all()
    result["payments"]=pq.limit(300).all()
    result["supplies"]=sq.limit(300).all()

    totals=_employee_dispense_aggregate(employee_id,start,end)
    result.update(totals)

    approved_payment_query=(db.session.query(func.coalesce(func.sum(FarmerPayment.amount),0))
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(FarmerPayment.employee_id==employee_id,Document.status!="reversed"))
    if start:
        approved_payment_query=approved_payment_query.filter(FarmerPayment.created_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc))
    if end:
        approved_payment_query=approved_payment_query.filter(FarmerPayment.created_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc))
    result["payment_collected"]=_decimal(approved_payment_query.scalar())
    result["collected"]=result["instant_collected"]+result["payment_collected"]

    supply_query=db.session.query(func.coalesce(func.sum(FuelPurchase.liters),0)).filter(
        FuelPurchase.employee_id==employee_id,FuelPurchase.status=="approved"
    )
    if start:
        supply_query=supply_query.filter(FuelPurchase.submitted_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc))
    if end:
        supply_query=supply_query.filter(FuelPurchase.submitted_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc))
    result["supplied_liters"]=_decimal(supply_query.scalar())
    return result


def sales_report(start=None,end=None):
    query=FuelDispense.query.filter_by(status="approved").order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc())
    if start:
        query=query.filter(FuelDispense.created_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc))
    if end:
        query=query.filter(FuelDispense.created_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc))
    rows=query.limit(500).all()  # presentation limit only

    q=db.session.query(
        func.coalesce(func.sum(FuelDispense.total_amount),0),
        func.coalesce(func.sum(FuelDispense.cost_amount),0),
        func.coalesce(func.sum(FuelDispense.liters),0),
        func.coalesce(func.sum(FuelDispense.drums),0),
        func.coalesce(func.sum(FuelDispense.paid_amount),0),
    ).filter(FuelDispense.status=="approved")
    if start:
        q=q.filter(FuelDispense.created_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc))
    if end:
        q=q.filter(FuelDispense.created_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc))
    sales,cogs,liters,drums,collected=q.one()

    return {
        "rows":rows,
        "sales":_decimal(sales),
        "cogs":_decimal(cogs),
        "gross_profit":_decimal(sales)-_decimal(cogs),
        "liters":_decimal(liters),
        "drums":_decimal(drums),
        "collected":_decimal(collected),
        "row_count":query.count(),
    }


def dispense_report(start=None,end=None):
    return sales_report(start,end)
