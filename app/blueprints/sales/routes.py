from flask import flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Farmer,FuelTank,User,ProjectSettings
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.sales import create_dispense,farmer_account,register_payment
from . import sales_bp

def selected_employee():
    if not current_user.has_role("manager"):
        return current_user
    employee_id=request.form.get("employee_id") or request.args.get("employee_id")
    if not employee_id:
        raise ValueError("اختر الموظف المسؤول عن العملية.")
    employee=User.query.filter_by(id=int(employee_id),is_employee=True,active=True).first()
    if not employee:
        raise ValueError("الموظف المحدد غير صالح.")
    return employee

def visible_farmers(employee=None):
    query=Farmer.query.filter_by(status="approved").order_by(Farmer.name)
    if employee and not current_user.has_role("manager"):
        query=query.filter_by(assigned_employee_id=employee.id)
    elif not user_has_permission(current_user,"farmers.view_all"):
        query=query.filter_by(assigned_employee_id=current_user.id)
    return query.all()

@sales_bp.route("/dispense",methods=["GET","POST"])
@permission_required("fuel.dispense")
def dispense():
    if request.method=="POST":
        try:
            employee=selected_employee()
            farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
            tank=FuelTank.query.get_or_404(int(request.form["tank_id"]))
            settings=ProjectSettings.get()
            if current_user.has_role("manager") or user_has_permission(current_user,"fuel.price.override"):
                price=request.form.get("sale_price_per_liter") or settings.default_sale_price_per_liter
            else:
                price=settings.default_sale_price_per_liter
            row=create_dispense(employee,farmer,tank.id,request.form.get("drums"),price,request.form.get("paid_amount") or 0,request.form.get("notes"))
            audit("fuel.dispense.created","fuel_dispense",row.id,after={"farmer_id":farmer.id,"employee_id":employee.id,"drums":str(row.drums),"liters":str(row.liters),"total":str(row.total_amount),"credit":str(row.credit_amount),"cost":str(row.cost_amount)})
            db.session.commit()
            flash("تم تسجيل صرف الديزل وإصدار سند الصرف.","success")
            return redirect(url_for("sales.dispense"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    farmers=visible_farmers()
    tanks=FuelTank.query.filter_by(is_active=True).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    settings=ProjectSettings.get()
    return render_template("sales/dispense.html",farmers=farmers,tanks=tanks,employees=employees,settings=settings)

@sales_bp.route("/payment",methods=["GET","POST"])
@permission_required("farmer.payment.create")
def payment():
    if request.method=="POST":
        try:
            employee=selected_employee()
            farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
            if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=employee.id:
                abort(403)
            row=register_payment(employee,farmer,request.form.get("amount"),request.form.get("payment_method") or "cash",request.form.get("reference"),request.form.get("notes"))
            audit("farmer.payment.created","farmer_payment",row.id,after={"farmer_id":farmer.id,"employee_id":employee.id,"amount":str(row.amount),"document_id":row.document_id})
            db.session.commit()
            flash("تم تسجيل السداد وإصدار سند قبض.","success")
            return redirect(url_for("sales.payment"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    farmers=visible_farmers()
    accounts={farmer.id:farmer_account(farmer) for farmer in farmers}
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    return render_template("sales/payment.html",farmers=farmers,accounts=accounts,employees=employees)

@sales_bp.get("/farmer/<int:farmer_id>")
@permission_required("farmers.view")
def farmer_account_view(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=current_user.id: abort(403)
    account=farmer_account(farmer)
    return render_template("sales/farmer_account.html",farmer=farmer,account=account,dispenses=farmer.dispenses,payments=farmer.payments)
