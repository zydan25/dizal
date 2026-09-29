from datetime import date,datetime,time,timedelta,timezone
from flask import abort,flash,redirect,render_template,request,url_for
from flask_login import current_user
from sqlalchemy import desc
from ...decorators import permission_required
from ...extensions import db
from ...models import Cashbox,CashboxTransaction
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.cashbox import balance
from ...services.reports import employee_finance_summary
from . import cashbox_bp

def _period_window(value):
    today=date.today()
    if value=="week":
        start=today-timedelta(days=today.weekday())
        return start,today
    if value=="month":
        return today.replace(day=1),today
    return None,None

def _load_transactions(cashbox_id,period="all"):
    query=CashboxTransaction.query.filter_by(cashbox_id=cashbox_id)
    start,end=_period_window(period)
    if start:
        query=query.filter(
            CashboxTransaction.created_at>=datetime.combine(start,time.min).replace(tzinfo=timezone.utc),
            CashboxTransaction.created_at<=datetime.combine(end,time.max).replace(tzinfo=timezone.utc),
        )
    return query.order_by(desc(CashboxTransaction.created_at),desc(CashboxTransaction.id)).limit(200).all()

def _box_or_403(cashbox_id):
    box=Cashbox.query.get_or_404(cashbox_id)
    if not user_has_permission(current_user,"cashbox.view_all") and box.owner_user_id!=current_user.id:
        abort(403)
    return box

@cashbox_bp.get("/")
@permission_required("cashbox.view")
def index():
    if user_has_permission(current_user,"cashbox.view_all"):
        boxes=Cashbox.query.filter_by(is_active=True).all()
    else:
        boxes=Cashbox.query.filter_by(owner_user_id=current_user.id,is_active=True).all()
    rows=[{"box":box,"balance":balance(box.id)} for box in boxes]
    return render_template("cashbox/index.html",rows=rows)

@cashbox_bp.get("/<int:cashbox_id>")
@permission_required("cashbox.view")
def detail(cashbox_id):
    box=_box_or_403(cashbox_id)
    period=request.args.get("period") or "all"
    if period not in {"all","week","month"}: period="all"
    transactions=_load_transactions(box.id,period)
    total_in=sum((row.amount for row in transactions if row.direction=="IN"),0)
    total_out=sum((row.amount for row in transactions if row.direction=="OUT"),0)
    finance=None
    owner=None
    if box.owner_user_id:
        from ...models import User
        owner=User.query.get(box.owner_user_id)
        if owner and owner.is_employee:
            finance=employee_finance_summary(owner)
    return render_template(
        "cashbox/detail.html",
        box=box,balance=balance(box.id),transactions=transactions,period=period,
        total_in=total_in,total_out=total_out,finance=finance,owner=owner,
    )

@cashbox_bp.get("/<int:cashbox_id>/report")
@permission_required("cashbox.view")
def report(cashbox_id):
    box=_box_or_403(cashbox_id)
    period=request.args.get("period") or "month"
    if period not in {"all","week","month"}: period="month"
    transactions=_load_transactions(box.id,period)
    total_in=sum((row.amount for row in transactions if row.direction=="IN"),0)
    total_out=sum((row.amount for row in transactions if row.direction=="OUT"),0)
    start,end=_period_window(period)
    return render_template("cashbox/report.html",box=box,balance=balance(box.id),transactions=transactions,period=period,start=start,end=end,total_in=total_in,total_out=total_out)

@cashbox_bp.route("/<int:cashbox_id>/transaction/<int:transaction_id>/edit",methods=["GET","POST"])
@permission_required("cashbox.view_all")
def edit_transaction(cashbox_id,transaction_id):
    box=Cashbox.query.get_or_404(cashbox_id)
    tx=CashboxTransaction.query.filter_by(id=transaction_id,cashbox_id=box.id).first_or_404()
    if request.method=="POST":
        before={"description":tx.description}
        tx.description=(request.form.get("description") or "").strip() or None
        audit("cashbox.transaction.updated","cashbox_transaction",tx.id,before=before,after={"description":tx.description})
        db.session.commit()
        flash("تم تحديث بيان الحركة. لتصحيح المبلغ أو الاتجاه استخدم عكس السند ثم سجّل الحركة الصحيحة.","success")
        return redirect(url_for("cashbox.detail",cashbox_id=box.id,period=request.form.get("period") or "all"))
    return render_template("cashbox/edit.html",box=box,transaction=tx,period=request.args.get("period") or "all")