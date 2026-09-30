from ..extensions import db
from ..models import Asset,FuelTank
from .cashbox import post_transaction
from .documents import create_document

def create_asset(name,category,cost,acquisition_date,payer_cashbox_id,created_by_id,custodian_user_id=None,location=None,notes=None,create_tank=False,tank_capacity_liters=None):
    if float(cost)<=0: raise ValueError("قيمة الأصل يجب أن تكون أكبر من صفر.")
    code=f"AST-{Asset.query.count()+1:06d}"
    document=create_document("AST","سند شراء أصل",created_by_id,source_type="asset")
    post_transaction(payer_cashbox_id,"OUT",cost,"asset_purchase",created_by_id,f"شراء أصل: {name}",document.id,"asset",code)
    row=Asset(asset_code=code,name=name,category=category,acquisition_cost=cost,acquisition_date=acquisition_date,payer_cashbox_id=payer_cashbox_id,custodian_user_id=custodian_user_id,location=location,notes=notes,document_id=document.id)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    if create_tank:
        number=FuelTank.query.count()+1
        while FuelTank.query.filter_by(code=f"TANK-{number:04d}").first(): number+=1
        tank=FuelTank(name=name,code=f"TANK-{number:04d}",capacity_liters=tank_capacity_liters or None,location=location,is_active=True,notes=notes)
        db.session.add(tank)
        db.session.flush()
        row.tank_id=tank.id
    from .accounting import post_asset
    post_asset(row,created_by_id)
    return row


def update_asset_cost(asset, new_cost, actor_id):
    """Update the paid acquisition cost while keeping cashbox and GL entries synchronized."""
    from decimal import Decimal
    from ..models import CashboxTransaction, JournalEntry
    from .cashbox import balance

    new_cost = Decimal(str(new_cost or 0))
    if new_cost <= 0:
        raise ValueError("قيمة الأصل يجب أن تكون أكبر من صفر.")
    if not asset.document or asset.document.status != "approved":
        raise ValueError("لا يمكن تعديل قيمة أصل إلا وسند شرائه معتمد.")

    transactions = CashboxTransaction.query.filter_by(
        document_id=asset.document_id,
        transaction_type="asset_purchase",
    ).order_by(CashboxTransaction.id).with_for_update().all()
    if len(transactions) != 1:
        raise ValueError("لا يمكن تعديل القيمة المالية لهذا الأصل لأن حركة الصرف الأصلية غير موجودة أو غير فريدة.")
    transaction = transactions[0]
    if transaction.direction != "OUT" or transaction.cashbox_id != asset.payer_cashbox_id:
        raise ValueError("حركة صرف الأصل المرتبطة بالصندوق غير متوافقة مع بيانات الأصل.")

    old_cost = Decimal(str(asset.acquisition_cost))
    old_transaction_amount = Decimal(str(transaction.amount))
    if old_transaction_amount != old_cost:
        raise ValueError("قيمة الأصل وحركة الصرف الأصلية غير متطابقتين؛ يلزم تصحيح السجل ماليًا قبل تعديل الأصل.")

    # The current balance already includes the original OUT transaction. Add it back
    # to calculate the cash available before replacing that transaction's amount.
    available_for_replacement = Decimal(str(balance(transaction.cashbox_id))) + old_transaction_amount
    if new_cost > available_for_replacement:
        raise ValueError("الرصيد الحالي للصندوق لا يكفي للقيمة الجديدة للأصل بعد احتساب الصرف الأصلي.")

    entries = JournalEntry.query.filter_by(
        document_id=asset.document_id,
        source_type="asset",
        source_id=str(asset.id),
    ).order_by(JournalEntry.id).with_for_update().all()
    if len(entries) != 1:
        raise ValueError("القيد المحاسبي المرتبط بالأصل غير موجود أو غير فريد؛ لم يتم تعديل أي مبلغ.")
    entry = entries[0]
    if len(entry.lines) != 2:
        raise ValueError("القيد المحاسبي للأصل ليس بالصيغة المتوقعة (أصل مقابل صندوق)؛ لم يتم تعديل أي مبلغ.")

    debit_line = next((line for line in entry.lines if line.account and line.account.code == "1300"), None)
    credit_line = next((line for line in entry.lines if line.credit and line.credit > 0 and line.account and line.account.code in {"1100", "1110"}), None)
    if debit_line is None or credit_line is None:
        raise ValueError("لم يتم التعرف على سطري قيد شراء الأصل؛ لم يتم تعديل أي مبلغ.")

    debit_line.debit = new_cost
    credit_line.credit = new_cost
    transaction.amount = new_cost
    asset.acquisition_cost = new_cost
    entry.description = f"شراء أصل {asset.name}"
    return old_cost, new_cost, transaction, entry
