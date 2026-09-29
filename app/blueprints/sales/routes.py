from flask import flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Document,Farmer,FarmerPayment,FarmerQuotaMovement,FuelDispense,FuelTank,User,ProjectSettings
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.sales import create_dispense,create_general_sale,farmer_account,farmer_account_metrics,register_payment
from . import sales_bp

def selected_employee(farmer=None):
    if not current_user.has_role("manager"):
        return current_user
    employee_id=request.form.get("employee_id") or request.args.get("employee_id")
    if not employee_id and farmer is not None:
        employee_id=farmer.assigned_employee_id
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
            farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
            employee=selected_employee(farmer)
            tank_id=int(request.form.get("tank_id") or 0)
            if not tank_id:
                first_tank=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).first()
                if not first_tank:
                    raise ValueError("لا يوجد خزان فعال. أضف خزانًا أولًا.")
                tank_id=first_tank.id
            tank=FuelTank.query.get_or_404(tank_id)
            settings=ProjectSettings.get()
            can_change_price=current_user.has_role("manager") or settings.employee_can_change_sale_price
            price=request.form.get("sale_price_per_liter") if can_change_price else settings.default_sale_price_per_liter
            price=price or settings.default_sale_price_per_liter
            row=create_dispense(employee,farmer,tank.id,request.form.get("drums"),price,request.form.get("paid_amount") or 0,request.form.get("notes"))
            audit("fuel.dispense.created","fuel_dispense",row.id,after={"farmer_id":farmer.id,"employee_id":employee.id,"drums":str(row.drums),"liters":str(row.liters),"total":str(row.total_amount),"credit":str(row.credit_amount),"cost":str(row.cost_amount),"document_id":row.document_id})
            db.session.commit()
            flash("تم تسجيل صرف الديزل وإصدار سند الصرف.","success")
            return redirect(url_for("sales.dispense"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    farmers=visible_farmers()
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    settings=ProjectSettings.get()
    selected_tank_id=request.args.get("tank_id") or (str(tanks[0].id) if tanks else "")
    can_change_price=current_user.has_role("manager") or settings.employee_can_change_sale_price
    farmer_info={str(farmer.id):{key:(float(value) if isinstance(value,(int,float)) else str(value)) for key,value in farmer_account(farmer).items()} for farmer in farmers}
    selected_farmer_id=request.args.get("farmer_id") or ""
    selected_employee_id=request.args.get("employee_id") or ""
    if current_user.has_role("manager") and selected_farmer_id and not selected_employee_id:
        selected_farmer=Farmer.query.get(selected_farmer_id)
        if selected_farmer:
            selected_employee_id=str(selected_farmer.assigned_employee_id or "")
    return render_template("sales/dispense.html",farmers=farmers,tanks=tanks,employees=employees,settings=settings,farmer_info=farmer_info,selected_farmer_id=selected_farmer_id,selected_employee_id=selected_employee_id,selected_tank_id=selected_tank_id,can_change_price=can_change_price)

@sales_bp.route("/payment",methods=["GET","POST"])
@permission_required("farmer.payment.create")
def payment():
    if request.method=="POST":
        try:
            farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
            employee=selected_employee(farmer)
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
    selected_farmer_id=request.args.get("farmer_id") or ""
    selected_employee_id=request.args.get("employee_id") or ""
    if current_user.has_role("manager") and selected_farmer_id and not selected_employee_id:
        selected_farmer=Farmer.query.get(selected_farmer_id)
        if selected_farmer:
            selected_employee_id=str(selected_farmer.assigned_employee_id or "")
    return render_template("sales/payment.html",farmers=farmers,accounts=accounts,accounts_json=accounts_json,employees=employees,selected_farmer_id=selected_farmer_id,selected_employee_id=selected_employee_id)

@sales_bp.route("/point-of-sale",methods=["GET","POST"],endpoint="point_of_sale")
@sales_bp.route("/pos",methods=["GET","POST"],endpoint="point_of_sale_short")
@permission_required("fuel.dispense")
def point_of_sale():
    if request.method=="POST":
        try:
            employee=current_user
            if current_user.has_role("manager") and request.form.get("employee_id"):
                employee=User.query.filter_by(id=int(request.form["employee_id"]),is_employee=True,active=True).first()
                if not employee:
                    raise ValueError("الموظف المحدد غير صالح.")
            settings=ProjectSettings.get()
            can_change_price=current_user.has_role("manager") or settings.employee_can_change_sale_price
            tank_id=int(request.form.get("tank_id") or 0)
            if not tank_id:
                first_tank=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).first()
                if not first_tank:
                    raise ValueError("لا يوجد خزان فعال. أضف خزانًا أولًا.")
                tank_id=first_tank.id
            price=request.form.get("sale_price_per_liter") if can_change_price else settings.default_sale_price_per_liter
            price=price or settings.default_sale_price_per_liter
            row=create_general_sale(
                employee=employee,
                tank_id=tank_id,
                drums=request.form.get("drums"),
                sale_price_per_liter=price,
                customer_name=request.form.get("customer_name"),
                notes=request.form.get("notes"),
            )
            audit("general.sale.created","fuel_dispense",row.id,after={
                "employee_id":employee.id,"tank_id":row.tank_id,"drums":str(row.drums),
                "liters":str(row.liters),"total":str(row.total_amount),"document_id":row.document_id,
            })
            db.session.commit()
            flash("تم تسجيل البيع العام وقبض المبلغ وإصدار السند.","success")
            return redirect(url_for("sales.point_of_sale"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    settings=ProjectSettings.get()
    selected_tank_id=request.args.get("tank_id") or (str(tanks[0].id) if tanks else "")
    can_change_price=current_user.has_role("manager") or settings.employee_can_change_sale_price
    selected_employee_id=request.args.get("employee_id") or ""
    if current_user.has_role("manager") and not selected_employee_id and employees:
        selected_employee_id=str(employees[0].id)
    return render_template("sales/point_of_sale.html",tanks=tanks,employees=employees,settings=settings,selected_employee_id=selected_employee_id,selected_tank_id=selected_tank_id,can_change_price=can_change_price)

@sales_bp.get("/farmer/<int:farmer_id>")
@permission_required("farmers.view")
def farmer_account_view(farmer_id):
    from datetime import date,datetime,time,timezone
    farmer=Farmer.query.get_or_404(farmer_id)
    if not user_has_permission(current_user,"farmers.view_all") and farmer.assigned_employee_id!=current_user.id:
        abort(403)
    start_value=request.args.get("start")
    end_value=request.args.get("end")
    try:
        start_date=date.fromisoformat(start_value) if start_value else None
        end_date=date.fromisoformat(end_value) if end_value else None
    except ValueError:
        abort(400,description="صيغة التاريخ غير صحيحة.")
    if start_date and end_date and end_date<start_date:
        abort(400,description="نهاية الفترة لا يمكن أن تسبق بدايتها.")
    dispenses_q=FuelDispense.query.filter_by(farmer_id=farmer.id,status="approved")
    payments_q=(FarmerPayment.query.join(Document,FarmerPayment.document_id==Document.id)
                .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed"))
    if start_date:
        start_dt=datetime.combine(start_date,time.min).replace(tzinfo=timezone.utc)
        dispenses_q=dispenses_q.filter(FuelDispense.created_at>=start_dt)
        payments_q=payments_q.filter(FarmerPayment.created_at>=start_dt)
    if end_date:
        end_dt=datetime.combine(end_date,time.max).replace(tzinfo=timezone.utc)
        dispenses_q=dispenses_q.filter(FuelDispense.created_at<=end_dt)
        payments_q=payments_q.filter(FarmerPayment.created_at<=end_dt)
    dispenses=dispenses_q.order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc()).all()
    payments=payments_q.order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc()).all()
    quota_movements=FarmerQuotaMovement.query.filter_by(farmer_id=farmer.id).order_by(FarmerQuotaMovement.created_at.desc(),FarmerQuotaMovement.id.desc()).limit(100).all()
    ledger=[{"kind":"dispense","date":row.created_at,"row":row} for row in dispenses]
    ledger += [{"kind":"payment","date":row.created_at,"row":row} for row in payments]
    ledger.sort(key=lambda item:item["date"],reverse=True)
    account=farmer_account_metrics(farmer,start=start_date)
    return render_template("sales/farmer_account.html",farmer=farmer,account=account,dispenses=dispenses,payments=payments,quota_movements=quota_movements,ledger=ledger,start=start_date,end=end_date)
