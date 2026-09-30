from decimal import Decimal,InvalidOperation
from sqlalchemy import func
from ..extensions import db
from ..models import CapitalContribution,CapitalAllocation,Cashbox,CashboxTransaction,Document,JournalEntry,JournalLine,Account
from .cashbox import post_transaction,balance
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
    from .accounting import post_capital
    post_capital(row,created_by_id)
    return row

def update_capital_amount(contribution,new_amount,actor_id):
    try:
        new_amount=Decimal(str(new_amount))
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError("مبلغ رأس المال غير صالح.")
    if new_amount<=0:
        raise ValueError("رأس المال يجب أن يكون أكبر من صفر.")

    if contribution.status=="reversed" or (contribution.document and contribution.document.status=="reversed"):
        raise ValueError("لا يمكن تعديل رأس مال معكوس.")
    if contribution.document is None or contribution.document.status!="approved":
        raise ValueError("لا يمكن تعديل إلا رأس المال المرتبط بسند معتمد.")
    if contribution.cashbox_id is None:
        raise ValueError("عملية رأس المال لا ترتبط بصندوق صالح.")

    box=Cashbox.query.get(contribution.cashbox_id)
    if not box or box.box_type!="central":
        raise ValueError("رأس المال يجب أن يكون مثبتًا في الصندوق الرئيسي.")

    old_amount=Decimal(str(contribution.amount))
    if new_amount==old_amount:
        return contribution

    cash_rows=(
        CashboxTransaction.query
        .filter_by(document_id=contribution.document_id,transaction_type="capital_contribution")
        .all()
    )
    if len(cash_rows)!=1:
        raise ValueError("تعذر تعديل رأس المال لأن حركة الصندوق المرتبطة بالسند غير سليمة.")
    cash_row=cash_rows[0]
    if cash_row.cashbox_id!=box.id or cash_row.direction!="IN":
        raise ValueError("حركة رأس المال لا تطابق الصندوق الرئيسي أو اتجاهها غير صحيح.")
    if Decimal(str(cash_row.amount))!=old_amount:
        raise ValueError("مبلغ حركة الصندوق لا يطابق مبلغ رأس المال الحالي.")

    entries=(
        JournalEntry.query
        .filter_by(document_id=contribution.document_id,source_type="capital",source_id=str(contribution.id))
        .all()
    )
    if len(entries)!=1:
        raise ValueError("تعذر تعديل رأس المال لأن القيد المحاسبي المرتبط بالسند غير سليم.")
    entry=entries[0]
    lines=JournalLine.query.filter_by(journal_entry_id=entry.id).all()
    if len(lines)!=2:
        raise ValueError("القيد المحاسبي لرأس المال يجب أن يتكون من طرفين فقط.")

    account_1100=Account.query.filter_by(code="1100").first()
    account_3000=Account.query.filter_by(code="3000").first()
    if not account_1100 or not account_3000:
        raise ValueError("الحسابات المحاسبية الأساسية لرأس المال غير مكتملة.")

    debit_line=next((line for line in lines if line.account_id==account_1100.id and Decimal(str(line.debit))==old_amount and Decimal(str(line.credit or 0))==0),None)
    credit_line=next((line for line in lines if line.account_id==account_3000.id and Decimal(str(line.credit))==old_amount and Decimal(str(line.debit or 0))==0),None)
    if not debit_line or not credit_line:
        raise ValueError("القيد المحاسبي لا يطابق مبلغ رأس المال الحالي.")

    allocated=(
        db.session.query(func.coalesce(func.sum(CapitalAllocation.amount),0))
        .join(Document,CapitalAllocation.document_id==Document.id)
        .filter(Document.status!="reversed")
        .scalar() or 0
    )
    allocated=Decimal(str(allocated))
    total_contributed=(
        db.session.query(func.coalesce(func.sum(CapitalContribution.amount),0))
        .filter(CapitalContribution.status=="approved")
        .scalar() or 0
    )
    total_contributed=Decimal(str(total_contributed))
    projected_total=total_contributed-old_amount+new_amount
    if projected_total < allocated:
        raise ValueError("لا يمكن خفض رأس المال عن إجمالي المبالغ التي تم تسليمها للموظفين.")

    current_balance=Decimal(str(balance(box.id)))
    projected_balance=current_balance-old_amount+new_amount
    if projected_balance<0:
        raise ValueError("لا يمكن خفض رأس المال لأن الصندوق الرئيسي لا يملك رصيدًا كافيًا بعد التعديل.")

    cash_row.amount=new_amount
    debit_line.debit=new_amount
    credit_line.credit=new_amount
    contribution.amount=new_amount
    db.session.flush()
    return contribution

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
    from .accounting import post_employee_transfer
    post_employee_transfer(row,created_by_id)
    return row
