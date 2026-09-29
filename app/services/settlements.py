from decimal import Decimal
from datetime import date,datetime,timezone
from sqlalchemy import func
from ..extensions import db
from ..models import Cashbox,CashboxTransaction,EmployeeSettlement,OperatingExpense,User
from .cashbox import balance,post_transaction
from .documents import create_document
from .accounting import post_salary
from .reports import employee_compensation


def _cash_balance_until(cashbox_id,end_date):
    incoming=db.session.query(func.coalesce(func.sum(CashboxTransaction.amount),0)).filter(
        CashboxTransaction.cashbox_id==cashbox_id,
        CashboxTransaction.direction=="IN",
        CashboxTransaction.created_at < datetime.combine(end_date,__import__("datetime").time.max).replace(tzinfo=timezone.utc)
    ).scalar() or 0
    outgoing=db.session.query(func.coalesce(func.sum(CashboxTransaction.amount),0)).filter(
        CashboxTransaction.cashbox_id==cashbox_id,
        CashboxTransaction.direction=="OUT",
        CashboxTransaction.created_at < datetime.combine(end_date,__import__("datetime").time.max).replace(tzinfo=timezone.utc)
    ).scalar() or 0
    return Decimal(str(incoming))-Decimal(str(outgoing))


def settlement_preview(employee,start_date,end_date):
    cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    if not cashbox:
        raise ValueError("لا يوجد صندوق فعال للموظف.")

    compensation=employee_compensation(employee,start_date,end_date)
    expenses=db.session.query(func.coalesce(func.sum(OperatingExpense.amount),0)).filter(
        OperatingExpense.employee_id==employee.id,
        OperatingExpense.status=="approved",
        OperatingExpense.expense_date>=start_date,
        OperatingExpense.expense_date<=end_date
    ).scalar() or 0
    expenses=Decimal(str(expenses))

    return {
        "cashbox":cashbox,
        "expected_cash":_cash_balance_until(cashbox.id,end_date),
        "sales_amount":compensation["sales"],
        "cost_of_sales":compensation["cogs"],
        "gross_profit":compensation["gross_profit"],
        "operating_expenses":expenses,
        "employee_salary":compensation["earned"],
        "salary_type":compensation["salary_type"],
        "salary_value":compensation["salary_value"],
        "commission_label":compensation["label"],
        "sold_liters":compensation["liters"],
        "sold_drums":compensation["drums"],
        "operating_profit":compensation["gross_profit"]-expenses-compensation["earned"],
    }


def create_settlement(employee,start_date,end_date,created_by_id,actual_cash,owner_transfer=0,retained_operating_capital=0,notes=None):
    actual=Decimal(str(actual_cash))
    if actual<0:
        raise ValueError("النقد الفعلي لا يمكن أن يكون سالبًا.")
    preview=settlement_preview(employee,start_date,end_date)
    expected=preview["expected_cash"]
    shortage=max(expected-actual,Decimal("0"))
    overage=max(actual-expected,Decimal("0"))
    employee_salary=preview["employee_salary"]
    document=create_document("SET","سند تسوية الموظف",created_by_id,source_type="employee_settlement",status="draft")
    settlement=EmployeeSettlement(
        document_id=document.id,employee_id=employee.id,period_start=start_date,period_end=end_date,
        expected_cash=expected,actual_cash=actual,cash_shortage=shortage,cash_overage=overage,
        sales_amount=preview["sales_amount"],cost_of_sales=preview["cost_of_sales"],gross_profit=preview["gross_profit"],
        operating_expenses=preview["operating_expenses"],employee_salary=employee_salary,
        compensation_type_snapshot=preview["salary_type"],
        compensation_value_snapshot=Decimal(str(
            preview.get("salary_value",0) if preview["salary_type"]!="fixed"
            else (employee.employee_profile.salary_value if employee.employee_profile else 0)
        )),
        owner_transfer=Decimal(str(owner_transfer or 0)),retained_operating_capital=Decimal(str(retained_operating_capital or 0)),
        status="draft",created_by_id=created_by_id,notes=notes
    )
    db.session.add(settlement)
    db.session.flush()
    document.source_id=str(settlement.id)
    return settlement


def approve_settlement(settlement,approved_by_id):
    if settlement.status!="draft":
        raise ValueError("التسوية ليست في حالة مسودة.")
    if settlement.owner_transfer<0 or settlement.retained_operating_capital<0:
        raise ValueError("قيم التسوية لا يمكن أن تكون سالبة.")
    employee_cashbox=Cashbox.query.filter_by(owner_user_id=settlement.employee_id,box_type="employee",is_active=True).first()
    if not employee_cashbox:
        raise ValueError("لا يوجد صندوق موظف فعال.")
    total_out=settlement.owner_transfer+settlement.employee_salary
    if balance(employee_cashbox.id)<total_out:
        raise ValueError("رصيد صندوق الموظف لا يكفي للراتب والتحويل المحددين.")

    if settlement.owner_transfer>0:
        central=Cashbox.query.filter_by(box_type="central",is_active=True).first()
        if not central:
            raise ValueError("الصندوق الرئيسي غير موجود.")
        post_transaction(employee_cashbox.id,"OUT",settlement.owner_transfer,"owner_transfer",approved_by_id,"تحويل للمدير",settlement.document_id,"settlement",settlement.id)
        post_transaction(central.id,"IN",settlement.owner_transfer,"owner_transfer",approved_by_id,"استلام تحويل من الموظف",settlement.document_id,"settlement",settlement.id)

    if settlement.employee_salary>0:
        post_transaction(
            employee_cashbox.id,"OUT",settlement.employee_salary,"employee_salary",
            approved_by_id,"راتب/عمولة الموظف",settlement.document_id,"settlement",settlement.id
        )
        if settlement.compensation_type_snapshot in {"per_liter","per_drum","percent_profit","commission"}:
            from .accounting import post_commission_payment
            post_commission_payment(
                settlement.employee_id,
                settlement.employee_salary,
                settlement.document_id,
                approved_by_id,
            )
        else:
            post_salary(settlement.employee_id,settlement.employee_salary,settlement.document_id,approved_by_id)

    settlement.status="approved"
    settlement.document.status="approved"
    settlement.document.approved_by_id=approved_by_id
    db.session.flush()
    return settlement
