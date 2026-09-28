from datetime import date,timedelta
from flask import flash,redirect,render_template,request,url_for
from flask_security import current_user
from sqlalchemy import func
from ...decorators import permission_required
from ...extensions import db
from ...models import CapitalAllocation,CapitalContribution,Cashbox,Document,User
from ...services.audit import audit
from ...services.capital import add_capital,allocate_to_employee,central_cashbox
from ...services.cashbox import balance
from . import capital_bp

def _period_window(value):
    today=date.today()
    if value=="week":
        start=today-timedelta(days=today.weekday())
        return start,today
    if value=="month":
        return today.replace(day=1),today
    return None,None

@capital_bp.get("/")
@permission_required("capital.view")
def index():
    central=central_cashbox()
    contributed=db.session.query(func.coalesce(func.sum(CapitalContribution.amount),0)).filter(CapitalContribution.status=="approved").scalar() or 0
    allocated=(
        db.session.query(func.coalesce(func.sum(CapitalAllocation.amount),0))
        .join(Document,CapitalAllocation.document_id==Document.id)
        .filter(Document.status!="reversed").scalar() or 0
    )
    employee_boxes=Cashbox.query.filter_by(box_type="employee",is_active=True).all()
    operating_cash=sum((balance(box.id) for box in employee_boxes),0)
    period=request.args.get("period") or "all"
    if period not in {"all","week","month"}: period="all"
    start,end=_period_window(period)
    contributions_q=CapitalContribution.query
    allocations_q=CapitalAllocation.query
    if start:
        contributions_q=contributions_q.filter(CapitalContribution.contribution_date>=start,CapitalContribution.contribution_date<=end)
        allocations_q=allocations_q.filter(CapitalAllocation.allocation_date>=start,CapitalAllocation.allocation_date<=end)
    contributions=contributions_q.order_by(CapitalContribution.id.desc()).limit(100).all()
    allocations=allocations_q.order_by(CapitalAllocation.id.desc()).limit(100).all()
    totals={
        "contributed":contributed,"allocated":allocated,"central_balance":balance(central.id),
        "employee_cash":operating_cash,"unallocated":max(contributed-allocated,0),
        "period_contributed":sum((row.amount for row in contributions if row.status=="approved"),0),
        "period_allocated":sum((row.amount for row in allocations if row.document and row.document.status!="reversed"),0),
    }
    return render_template("capital/index.html",central=central,central_balance=balance(central.id),contributions=contributions,allocations=allocations,totals=totals,period=period)

@capital_bp.get("/report")
@permission_required("capital.view")
def report():
    period=request.args.get("period") or "month"
    if period not in {"all","week","month"}: period="month"
    start,end=_period_window(period)
    contributions_q=CapitalContribution.query
    allocations_q=CapitalAllocation.query
    if start:
        contributions_q=contributions_q.filter(CapitalContribution.contribution_date>=start,CapitalContribution.contribution_date<=end)
        allocations_q=allocations_q.filter(CapitalAllocation.allocation_date>=start,CapitalAllocation.allocation_date<=end)
    contributions=contributions_q.order_by(CapitalContribution.id.desc()).limit(200).all()
    allocations=allocations_q.order_by(CapitalAllocation.id.desc()).limit(200).all()
    central=central_cashbox()
    return render_template("capital/report.html",central=central,central_balance=balance(central.id),contributions=contributions,allocations=allocations,period=period,start=start,end=end,total_in=sum((row.amount for row in contributions if row.status=="approved"),0),total_out=sum((row.amount for row in allocations if row.document and row.document.status!="reversed"),0))

@capital_bp.post("/add")
@permission_required("capital.create")
def add():
    try:
        row=add_capital(request.form.get("amount"),request.form.get("source"),current_user.id,request.form.get("notes"))
        audit("capital.added","capital_contribution",row.id,after={"amount":str(row.amount),"document_id":row.document_id})
        db.session.commit();flash("تمت إضافة رأس المال للصندوق الرئيسي.","success")
    except ValueError as exc:
        db.session.rollback();flash(str(exc),"danger")
    return redirect(url_for("capital.index"))

@capital_bp.post("/allocate")
@permission_required("capital.allocate")
def allocate():
    employee=User.query.filter_by(id=int(request.form["employee_id"]),is_employee=True).first_or_404()
    try:
        row=allocate_to_employee(employee,request.form.get("amount"),current_user.id,request.form.get("notes"))
        audit("capital.allocated","capital_allocation",row.id,after={"employee_id":employee.id,"amount":str(row.amount),"document_id":row.document_id})
        db.session.commit();flash("تم تسليم رأس المال للموظف وتسجيل سند التحويل.","success")
    except ValueError as exc:
        db.session.rollback();flash(str(exc),"danger")
    return redirect(url_for("capital.index"))

@capital_bp.route("/contribution/<int:contribution_id>/edit",methods=["GET","POST"])
@permission_required("capital.create")
def edit_contribution(contribution_id):
    row=CapitalContribution.query.get_or_404(contribution_id)
    if row.status=="reversed" or (row.document and row.document.status=="reversed"):
        flash("لا يمكن تعديل عملية رأس مال معكوسة.","danger")
        return redirect(url_for("capital.index"))
    if request.method=="POST":
        before={"source":row.source,"notes":row.notes}
        row.source=(request.form.get("source") or "").strip() or None
        row.notes=(request.form.get("notes") or "").strip() or None
        audit("capital.contribution.updated","capital_contribution",row.id,before=before,after={"source":row.source,"notes":row.notes})
        db.session.commit()
        flash("تم تحديث بيانات رأس المال. لتصحيح المبلغ استخدم عكس السند.","success")
        return redirect(url_for("capital.index"))
    return render_template("capital/edit_contribution.html",row=row)

@capital_bp.route("/allocation/<int:allocation_id>/edit",methods=["GET","POST"])
@permission_required("capital.allocate")
def edit_allocation(allocation_id):
    row=CapitalAllocation.query.get_or_404(allocation_id)
    if row.document and row.document.status=="reversed":
        flash("لا يمكن تعديل تحويل رأس مال معكوس.","danger")
        return redirect(url_for("capital.index"))
    if request.method=="POST":
        before={"notes":row.notes}
        row.notes=(request.form.get("notes") or "").strip() or None
        audit("capital.allocation.updated","capital_allocation",row.id,before=before,after={"notes":row.notes})
        db.session.commit()
        flash("تم تحديث بيان تحويل رأس المال. لتصحيح المبلغ استخدم عكس السند.","success")
        return redirect(url_for("capital.index"))
    return render_template("capital/edit_allocation.html",row=row)

@capital_bp.context_processor
def capital_context():
    return {"employees_for_capital":User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all()}