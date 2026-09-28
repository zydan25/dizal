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
    contributions=CapitalContribution.query.order_by(CapitalContribution.id.desc()).limit(50).all()
    allocations=CapitalAllocation.query.order_by(CapitalAllocation.id.desc()).limit(50).all()
    totals={"contributed":contributed,"allocated":allocated,"central_balance":balance(central.id),"employee_cash":operating_cash,"unallocated":max(contributed-allocated,0)}
    return render_template("capital/index.html",central=central,central_balance=balance(central.id),contributions=contributions,allocations=allocations,totals=totals)

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

@capital_bp.context_processor
def capital_context():
    return {"employees_for_capital":User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all()}
