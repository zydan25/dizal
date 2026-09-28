from decimal import Decimal
from ..extensions import db
from ..models import (
    Document,CashboxTransaction,FuelStockMovement,FuelStockLayer,FuelStockConsumption,
    FuelDispense,FuelPurchase,FarmerPayment,FarmerPaymentAllocation,
    CapitalContribution,Asset,OperatingExpense,EmployeeSettlement,
    JournalEntry,JournalLine
)
from .cashbox import post_transaction
from .documents import create_document

SUPPORTED={"CAP","TRF","AST","SUP","DSP","RCV","EXP","SET"}

def _source(document):
    mapping={
        "CAP":CapitalContribution,"TRF":None,"AST":Asset,"SUP":FuelPurchase,
        "DSP":FuelDispense,"RCV":FarmerPayment,"EXP":OperatingExpense,"SET":EmployeeSettlement
    }
    model=mapping.get(document.document_type)
    if model is None:
        return None
    return model.query.get(int(document.source_id)) if document.source_id else None

def reverse_document(document,actor_id,reason):
    if document.document_type=="REV" or document.source_type=="document_reversal":
        raise ValueError("لا يمكن عكس مستند عكس.")
    if document.document_type not in SUPPORTED:
        raise ValueError("نوع السند الحالي لا يملك عملية عكس آمنة بعد.")
    if document.status!="approved":
        raise ValueError("لا يمكن عكس إلا السند المعتمد.")
    source=_source(document)

    if document.document_type=="SUP" and source:
        layer=FuelStockLayer.query.filter_by(purchase_id=source.id).first()
        if not layer:
            raise ValueError("لا توجد طبقة مخزون مرتبطة بهذا التوريد.")
        if Decimal(str(layer.remaining_liters)) != Decimal(str(layer.original_liters)):
            raise ValueError("لا يمكن عكس التوريد بعد استهلاك أي جزء منه.")
    if document.document_type=="DSP" and source:
        active_alloc=(
            db.session.query(FarmerPaymentAllocation.id)
            .join(FarmerPayment,FarmerPaymentAllocation.payment_id==FarmerPayment.id)
            .join(Document,FarmerPayment.document_id==Document.id)
            .filter(FarmerPaymentAllocation.dispense_id==source.id,Document.status!="reversed")
            .first()
        )
        if active_alloc:
            raise ValueError("لا يمكن عكس الصرف قبل عكس سندات القبض المرتبطة به.")
    reversal=create_document("REV",f"عكس {document.title}",actor_id,source_type="document_reversal",source_id=document.id,notes=reason,status="approved")

    original_cash=CashboxTransaction.query.filter_by(document_id=document.id).order_by(CashboxTransaction.id).all()
    for tx in original_cash:
        inverse="OUT" if tx.direction=="IN" else "IN"
        post_transaction(
            tx.cashbox_id,inverse,tx.amount,"reversal",actor_id,
            f"عكس {tx.description or tx.transaction_type}",reversal.id,
            "document_reversal",document.id
        )

    if document.document_type=="SUP" and source:
        layer=FuelStockLayer.query.filter_by(purchase_id=source.id).first()
        db.session.add(FuelStockMovement(
            tank_id=source.tank_id,direction="OUT",movement_type="reversal",
            liters=source.liters,unit_cost=source.unit_cost,
            source_type="document_reversal",source_id=str(document.id),
            document_id=reversal.id,created_by_id=actor_id
        ))
    elif document.document_type=="DSP" and source:
        consumptions=FuelStockConsumption.query.filter_by(dispense_id=source.id).all()
        restored=sum((Decimal(str(row.liters)) for row in consumptions),Decimal("0"))
        cost=sum((Decimal(str(row.cost_amount)) for row in consumptions),Decimal("0"))
        for row in consumptions:
            layer=row.layer
            layer.remaining_liters=Decimal(str(layer.remaining_liters))+Decimal(str(row.liters))
        db.session.add(FuelStockMovement(
            tank_id=source.tank_id,direction="IN",movement_type="reversal",
            liters=restored,unit_cost=(cost/restored if restored else 0),
            source_type="document_reversal",source_id=str(document.id),
            document_id=reversal.id,created_by_id=actor_id
        ))

    entries=JournalEntry.query.filter_by(document_id=document.id).order_by(JournalEntry.id).all()
    for original in entries:
        entry=JournalEntry(
            entry_date=original.entry_date,
            source_type="document_reversal",
            source_id=str(original.id),
            document_id=reversal.id,
            description=f"عكس القيد: {original.description}",
            created_by_id=actor_id
        )
        db.session.add(entry)
        db.session.flush()
        for line in original.lines:
            db.session.add(JournalLine(
                journal_entry_id=entry.id,
                account_id=line.account_id,
                debit=line.credit,
                credit=line.debit,
                employee_id=line.employee_id,
                farmer_id=line.farmer_id,
                description=f"عكس: {line.description or original.description}"
            ))

    if source is not None and hasattr(source,"status"):
        source.status="reversed"
    document.status="reversed"
    document.notes=(document.notes + "\n" if document.notes else "") + f"تم العكس بسبب: {reason}"
    db.session.flush()
    return reversal
