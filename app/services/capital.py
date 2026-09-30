from decimal import Decimal
from ..extensions import db
from ..models import Asset,CapitalContribution,CapitalAllocation,Cashbox
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
    from .accounting import post_capital
    post_capital(row,created_by_id)
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
    from .accounting import post_employee_transfer
    post_employee_transfer(row,created_by_id)
    return row


def add_capital_asset(name,category,cost,contribution_date,source,created_by_id,custodian_user_id=None,location=None,notes=None):
    from datetime import date

    amount=Decimal(str(cost))
    if amount<=0:
        raise ValueError("قيمة الأصل المساهم به يجب أن تكون أكبر من صفر.")
    document=create_document(
        "CAP",
        "إثبات أصل كرأس مال",
        created_by_id,
        source_type="capital_asset",
    )
    code=f"AST-{Asset.query.count()+1:06d}"
    while Asset.query.filter_by(asset_code=code).first():
        code=f"AST-{Asset.query.count()+1:06d}"
    asset=Asset(
        asset_code=code,
        name=name,
        category=category,
        acquisition_cost=amount,
        acquisition_date=contribution_date or date.today(),
        payer_cashbox_id=None,
        custodian_user_id=custodian_user_id,
        location=location,
        notes=notes,
        document_id=document.id,
    )
    db.session.add(asset)
    db.session.flush()
    row=CapitalContribution(
        contribution_date=contribution_date,
        amount=amount,
        source=source,
        cashbox_id=None,
        document_id=document.id,
        created_by_id=created_by_id,
        notes=notes,
        status="approved",
        contribution_type="asset",
        asset_id=asset.id,
    )
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    from .accounting import post_capital
    post_capital(row,created_by_id)
    return row


def update_capital_asset_contribution(row,new_cost,actor_id):
    from decimal import Decimal
    from ..models import JournalEntry

    if row.contribution_type != "asset" or not row.asset:
        raise ValueError("هذه ليست مساهمة أصل في رأس المال.")
    if row.status == "reversed" or not row.document or row.document.status != "approved":
        raise ValueError("لا يمكن تعديل مساهمة أصل غير معتمدة أو معكوسة.")
    amount=Decimal(str(new_cost or 0))
    if amount<=0:
        raise ValueError("قيمة الأصل يجب أن تكون أكبر من صفر.")
    entries=JournalEntry.query.filter_by(
        document_id=row.document_id,
        source_type="capital",
        source_id=str(row.id),
    ).order_by(JournalEntry.id).with_for_update().all()
    if len(entries)!=1:
        raise ValueError("القيد الأصلي لمساهمة الأصل غير موجود أو غير فريد؛ لم يتم التعديل.")
    entry=entries[0]
    if len(entry.lines)!=2:
        raise ValueError("القيد الأصلي لمساهمة الأصل غير قياسي؛ لم يتم التعديل.")
    asset_line=next((line for line in entry.lines if line.account and line.account.code=="1300"),None)
    capital_line=next((line for line in entry.lines if line.account and line.account.code=="3000"),None)
    if not asset_line or not capital_line:
        raise ValueError("لم يتم العثور على سطري الأصل ورأس المال في القيد الأصلي.")
    old=Decimal(str(row.amount))
    row.amount=amount
    row.asset.acquisition_cost=amount
    asset_line.debit=amount
    capital_line.credit=amount
    entry.description=f"إضافة أصل كرأس مال: {row.asset.name}"
    return old,amount
