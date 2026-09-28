from decimal import Decimal
from sqlalchemy import func
from ..extensions import db
from ..models import Cashbox,CashboxTransaction

def balance(cashbox_id):
    incoming=db.session.query(func.coalesce(func.sum(CashboxTransaction.amount),0)).filter(CashboxTransaction.cashbox_id==cashbox_id,CashboxTransaction.direction=="IN").scalar() or 0
    outgoing=db.session.query(func.coalesce(func.sum(CashboxTransaction.amount),0)).filter(CashboxTransaction.cashbox_id==cashbox_id,CashboxTransaction.direction=="OUT").scalar() or 0
    return Decimal(str(incoming))-Decimal(str(outgoing))

def post_transaction(cashbox_id,direction,amount,transaction_type,posted_by_id,description=None,document_id=None,reference_type=None,reference_id=None,allow_negative=False):
    amount=Decimal(str(amount))
    if amount<=0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
    box=Cashbox.query.get(cashbox_id)
    if not box:
        raise ValueError("الصندوق غير موجود.")
    if direction not in {"IN","OUT"}:
        raise ValueError("اتجاه الحركة غير صالح.")
    if direction=="OUT" and not allow_negative and balance(cashbox_id)<amount:
        raise ValueError("رصيد الصندوق لا يكفي لتنفيذ العملية.")
    row=CashboxTransaction(cashbox_id=cashbox_id,direction=direction,amount=amount,transaction_type=transaction_type,posted_by_id=posted_by_id,description=description,document_id=document_id,reference_type=reference_type,reference_id=str(reference_id) if reference_id else None)
    db.session.add(row)
    db.session.flush()
    return row
