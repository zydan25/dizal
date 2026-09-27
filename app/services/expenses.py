from decimal import Decimal
from datetime import date
from ..extensions import db
from ..models import OperatingExpense
from .cashbox import post_transaction
from .documents import create_document
from .accounting import post_expense

def create_expense(cashbox_id,employee_id,category,amount,expense_date,created_by_id,description=None):
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("المصروف يجب أن يكون أكبر من صفر.")
    document=create_document("EXP","سند مصروف تشغيلي",created_by_id,source_type="operating_expense")
    post_transaction(cashbox_id,"OUT",amount,"operating_expense",created_by_id,description or category,document.id,"expense",category)
    row=OperatingExpense(document_id=document.id,cashbox_id=cashbox_id,employee_id=employee_id,expense_date=expense_date or date.today(),category=category,amount=amount,description=description,status="approved",created_by_id=created_by_id)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    post_expense(row,created_by_id)
    return row
