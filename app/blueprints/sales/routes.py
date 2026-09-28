from flask import flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Document,Farmer,FarmerPayment,FuelDispense,FuelTank,User,ProjectSettings
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.sales import create_dispense,farmer_account,farmer_account_metrics,register_payment
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
    farmer_info={str(farmer.id):farmer_account(farmer) for farmer in farmers}
    return render_template("sales/dispense.html",farmers=farmers,tanks=tanks,employees=employees,settings=settings,farmer_info=farmer_info)

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
    accounts_json={str(key):{name:(float(value) if hasattr(value,"as_integer_ratio") else str(value)) for name,value in item.items()} for key,item in accounts.items()}
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    return render_template("sales/payment.html",farmers=farmers,accounts=accounts,accounts_json=accounts_json,employees=employees)

@sales_bp.get("/farmer/<int:farmer_id>")
@permission_required("farmers.view")
def farmer_account_view(farmer_id):
    from datetime import date,datetime,time,timezone
    farmer=Farmer.query.get_or_404(farmer_id)
    if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=current_user.id:
        abort(403)
    try:
        start_date=date.fromisoformat(request.args.get("start") or date.today().replace(day=1).isoformat())
        end_date=date.fromisoformat(request.args.get("end") or date.today().isoformat())
    except ValueError:
        abort(400,description="صيغة التاريخ غير صحيحة.")
    if end_date<start_date:
        abort(400,description="نهاية الفترة لا يمكن أن تسبق بدايتها.")
    start_dt=datetime.combine(start_date,time.min).replace(tzinfo=timezone.utc)
    end_dt=datetime.combine(end_date,time.max).replace(tzinfo=timezone.utc)

    dispenses=(FuelDispense.query
               .filter_by(farmer_id=farmer.id,status="approved")
               .filter(FuelDispense.created_at>=start_dt,FuelDispense.created_at<=end_dt)
               .order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc()).all())
    payments=(FarmerPayment.query
              .join(Document,FarmerPayment.document_id==Document.id)
              .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed",
                      FarmerPayment.created_at>=start_dt,FarmerPayment.created_at<=end_dt)
              .order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc()).all())
    ledger=[{"kind":"dispense","date":row.created_at,"row":row} for row in dispenses]
    ledger += [{"kind":"payment","date":row.created_at,"row":row} for row in payments]
    ledger.sort(key=lambda item:item["date"],reverse=True)
    account=farmer_account_metrics(farmer,start=start_date)
    return render_template("sales/farmer_account.html",farmer=farmer,account=account,dispenses=dispenses,payments=payments,ledger=ledger,start=start_date,end=end_date)
