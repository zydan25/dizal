from flask import flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Farmer,FuelTank
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.sales import create_dispense,farmer_account,register_payment
from . import sales_bp

@sales_bp.route("/dispense",methods=["GET","POST"])
@permission_required("fuel.dispense")
def dispense():
    if request.method=="POST":
        farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
        tank=FuelTank.query.get_or_404(int(request.form["tank_id"]))
        price=request.form.get("sale_price_per_liter")
        try:
            row=create_dispense(current_user,farmer,tank.id,request.form.get("drums"),price,request.form.get("paid_amount") or 0,request.form.get("notes"))
            audit("fuel.dispense.created","fuel_dispense",row.id,after={"farmer_id":farmer.id,"drums":str(row.drums),"liters":str(row.liters),"total":str(row.total_amount),"credit":str(row.credit_amount)})
            db.session.commit()
            flash("تم تسجيل صرف الديزل وإصدار سند الصرف.","success")
            return redirect(url_for("sales.dispense"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    farmers=Farmer.query.filter_by(status="approved").order_by(Farmer.name).all()
    if not user_has_permission(current_user,"farmers.view_all"): farmers=[f for f in farmers if f.assigned_employee_id==current_user.id]
    tanks=FuelTank.query.filter_by(is_active=True).all()
    return render_template("sales/dispense.html",farmers=farmers,tanks=tanks)

@sales_bp.route("/payment",methods=["GET","POST"])
@permission_required("farmer.payment.create")
def payment():
    if request.method=="POST":
        farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
        if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=current_user.id: abort(403)
        try:
            row=register_payment(current_user,farmer,request.form.get("amount"),request.form.get("payment_method") or "cash",request.form.get("reference"),request.form.get("notes"))
            audit("farmer.payment.created","farmer_payment",row.id,after={"farmer_id":farmer.id,"amount":str(row.amount),"document_id":row.document_id})
            db.session.commit()
            flash("تم تسجيل السداد وإصدار سند قبض.","success")
            return redirect(url_for("sales.payment"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    farmers=Farmer.query.filter_by(status="approved").order_by(Farmer.name).all()
    if not user_has_permission(current_user,"farmers.view_all"): farmers=[f for f in farmers if f.assigned_employee_id==current_user.id]
    accounts={farmer.id:farmer_account(farmer) for farmer in farmers}
    return render_template("sales/payment.html",farmers=farmers,accounts=accounts)

@sales_bp.get("/farmer/<int:farmer_id>")
@permission_required("farmers.view")
def farmer_account_view(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=current_user.id: abort(403)
    account=farmer_account(farmer)
    return render_template("sales/farmer_account.html",farmer=farmer,account=account,dispenses=farmer.dispenses,payments=farmer.payments)
