from decimal import Decimal
from datetime import date
from ..extensions import db
from ..models import Account,JournalEntry,JournalLine

SYSTEM_ACCOUNTS={
"1100":("النقدية الرئيسية","asset"),
"1110":("عهدة الموظفين","asset"),
"1200":("مخزون الديزل","asset"),
"1300":("الأصول الثابتة","asset"),
"1400":("ذمم المزارعين","asset"),
"2100":("التزامات الموظفين","liability"),
"3000":("رأس مال المالك","equity"),
"4000":("مبيعات الديزل","income"),
"5000":("تكلفة الديزل المباع","expense"),
"6000":("المصروفات التشغيلية","expense"),
"6100":("رواتب وعمولات الموظفين","expense"),
}

def ensure_accounts():
    for code,(name,account_type) in SYSTEM_ACCOUNTS.items():
        row=Account.query.filter_by(code=code).first()
        if not row:
            db.session.add(Account(code=code,name=name,account_type=account_type,is_system=True,active=True))
    db.session.flush()

def account(code):
    ensure_accounts()
    row=Account.query.filter_by(code=code).first()
    if not row: raise ValueError(f"الحساب {code} غير موجود.")
    return row

def post_journal(source_type,source_id,description,created_by_id,lines,document_id=None,entry_date=None):
    entry_date=entry_date or date.today()
    debit_total=sum((Decimal(str(item.get("debit",0))) for item in lines),Decimal("0"))
    credit_total=sum((Decimal(str(item.get("credit",0))) for item in lines),Decimal("0"))
    if debit_total<=0 or debit_total!=credit_total:
        raise ValueError("القيد المحاسبي غير متوازن.")
    entry=JournalEntry(entry_date=entry_date,source_type=source_type,source_id=str(source_id),document_id=document_id,description=description,created_by_id=created_by_id)
    db.session.add(entry)
    db.session.flush()
    for item in lines:
        db.session.add(JournalLine(journal_entry_id=entry.id,account_id=account(item["account_code"]).id,debit=Decimal(str(item.get("debit",0))),credit=Decimal(str(item.get("credit",0))),employee_id=item.get("employee_id"),farmer_id=item.get("farmer_id"),description=item.get("description")))
    db.session.flush()
    return entry

def post_capital(contribution,created_by_id):
    return post_journal("capital",contribution.id,"إضافة رأس مال",created_by_id,[{"account_code":"1100","debit":contribution.amount},{"account_code":"3000","credit":contribution.amount}],contribution.document_id)

def post_employee_transfer(allocation,created_by_id):
    return post_journal("capital_allocation",allocation.id,"تحويل رأس مال لعهدة الموظف",created_by_id,[{"account_code":"1110","debit":allocation.amount,"employee_id":allocation.employee_id},{"account_code":"1100","credit":allocation.amount}],allocation.document_id)

def post_asset(asset,created_by_id):
    payer = asset.payer_cashbox
    credit_account = "1110" if payer and payer.box_type=="employee" else "1100"
    line={"account_code":credit_account,"credit":asset.acquisition_cost}
    if credit_account=="1110": line["employee_id"]=payer.owner_user_id
    return post_journal("asset",asset.id,f"شراء أصل {asset.name}",created_by_id,[{"account_code":"1300","debit":asset.acquisition_cost},line],asset.document_id)

def post_fuel_purchase(purchase,created_by_id):
    return post_journal("fuel_purchase",purchase.id,"شراء ديزل",created_by_id,[{"account_code":"1200","debit":purchase.landed_cost},{"account_code":"1110","credit":purchase.landed_cost,"employee_id":purchase.employee_id}],purchase.document_id)

def post_sale(dispense,created_by_id):
    # Farmer sales may create a receivable; direct sales are cash-only.
    if dispense.farmer_id:
        lines=[
            {"account_code":"4000","credit":dispense.total_amount},
            {"account_code":"5000","debit":dispense.cost_amount},
            {"account_code":"1200","credit":dispense.cost_amount},
        ]
        if dispense.paid_amount and dispense.credit_amount:
            lines.append({"account_code":"1110","debit":dispense.paid_amount,"employee_id":dispense.employee_id})
            lines.append({"account_code":"1400","debit":dispense.credit_amount,"farmer_id":dispense.farmer_id})
        elif dispense.paid_amount:
            lines.append({"account_code":"1110","debit":dispense.paid_amount,"employee_id":dispense.employee_id,"farmer_id":dispense.farmer_id})
        else:
            lines.append({"account_code":"1400","debit":dispense.total_amount,"farmer_id":dispense.farmer_id})
        return post_journal("fuel_dispense",dispense.id,"بيع وصرف ديزل",created_by_id,lines,dispense.document_id)
    lines=[
        {"account_code":"4000","credit":dispense.total_amount},
        {"account_code":"5000","debit":dispense.cost_amount},
        {"account_code":"1200","credit":dispense.cost_amount},
        {"account_code":"1110","debit":dispense.total_amount,"employee_id":dispense.employee_id},
    ]
    return post_journal("general_sale",dispense.id,"بيع ديزل مباشر",created_by_id,lines,dispense.document_id)
def post_payment(payment,created_by_id):
    return post_journal("farmer_payment",payment.id,"تحصيل من مزارع",created_by_id,[{"account_code":"1110","debit":payment.amount,"employee_id":payment.employee_id},{"account_code":"1400","credit":payment.amount,"farmer_id":payment.farmer_id}],payment.document_id)

def post_expense(expense,created_by_id):
    payer=expense.cashbox
    credit_account="1110" if payer and payer.box_type=="employee" else "1100"
    line={"account_code":credit_account,"credit":expense.amount}
    if credit_account=="1110": line["employee_id"]=payer.owner_user_id
    return post_journal("operating_expense",expense.id,expense.description or expense.category,created_by_id,[{"account_code":"6000","debit":expense.amount},line],expense.document_id)

def post_salary(employee_id,amount,document_id,created_by_id):
    return post_journal("employee_salary",employee_id,"راتب/عمولة الموظف",created_by_id,[{"account_code":"6100","debit":amount,"employee_id":employee_id},{"account_code":"1110","credit":amount,"employee_id":employee_id}],document_id)
