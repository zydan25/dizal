from decimal import Decimal
from ..extensions import db
from ..models import CapitalContribution,CapitalAllocation,Cashbox
from .cashbox import post_transaction
from .documents import create_document

def central_cashbox():
    box=Cashbox.query.filter_by(box_type="central",is_active=True).first()
    if not box:
        box=Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True)
        db.session.add(box)
        db.session.flush()
    return box

def add_capital(amount,source,created_by_id,notes=None):
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("رأس المال يجب أن يكون أكبر من صفر.")
    box=central_cashbox()
    document=create_document("CAP","إثبات رأس مال",created_by_id,source_type="capital")
    post_transaction(box.id,"IN",amount,"capital_contribution",created_by_id,"إضافة رأس مال",document.id)
    row=CapitalContribution(amount=amount,source=source,cashbox_id=box.id,document_id=document.id,created_by_id=created_by_id,notes=notes,status="approved")
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    return row

def allocate_to_employee(employee,amount,created_by_id,notes=None):
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
    source=central_cashbox()
    destination=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    if not destination: raise ValueError("لا يوجد صندوق فعال لهذا الموظف.")
    document=create_document("TRF","سند تسليم رأس مال للموظف",created_by_id,source_type="capital_allocation")
    post_transaction(source.id,"OUT",amount,"capital_transfer",created_by_id,"تحويل رأس مال للموظف",document.id,"user",employee.id)
    post_transaction(destination.id,"IN",amount,"capital_transfer",created_by_id,"استلام رأس مال تشغيلي",document.id,"central_cashbox",source.id)
    row=CapitalAllocation(amount=amount,employee_id=employee.id,source_cashbox_id=source.id,destination_cashbox_id=destination.id,document_id=document.id,created_by_id=created_by_id,notes=notes)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    return row
