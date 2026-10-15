from decimal import Decimal,InvalidOperation
from flask import flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Document,EmployeeSettlement,Farmer,FarmerPayment,FarmerPaymentAllocation,FarmerQuotaMovement,FuelDispense,FuelTank,JournalEntry,User,ProjectSettings
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.farmers import project_diesel_capacity
from ...services.sales import create_dispense,create_general_sale,farmer_account,farmer_account_metrics,register_payment
from ...services.fuel import current_stock_liters
from ...services.reversals import reverse_document
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


def _dispense_form_context():
    farmers=visible_farmers()
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    settings=ProjectSettings.get()
    farmer_info={
        str(farmer.id):{
            key:(float(value) if isinstance(value,(int,float)) else str(value))
            for key,value in farmer_account(farmer).items()
        }
        for farmer in farmers
    }
    form_values=request.form if request.method=="POST" else {}
    selected_farmer_id=form_values.get("farmer_id") or request.args.get("farmer_id") or ""
    selected_employee_id=form_values.get("employee_id") or request.args.get("employee_id") or ""
    if current_user.has_role("manager") and selected_farmer_id and not selected_employee_id:
        selected_farmer=Farmer.query.get(selected_farmer_id)
        if selected_farmer:
            selected_employee_id=str(selected_farmer.assigned_employee_id or "")
    selected_tank_id=form_values.get("tank_id") or request.args.get("tank_id") or (str(tanks[0].id) if tanks else "")
    values={
        "drums":form_values.get("drums",""),
        "paid_amount":form_values.get("paid_amount","0"),
        "sale_price_per_liter":form_values.get("sale_price_per_liter",str(settings.default_sale_price_per_liter)),
        "notes":form_values.get("notes",""),
    }
    return {
        "farmers":farmers,"tanks":tanks,"employees":employees,"settings":settings,
        "farmer_info":farmer_info,"selected_farmer_id":selected_farmer_id,
        "selected_employee_id":selected_employee_id,"selected_tank_id":selected_tank_id,
        "form_values":values,
    }


def _render_dispense_form():
    return render_template("sales/dispense.html",**_dispense_form_context())


@sales_bp.get("/dispense/new",endpoint="dispense_create")
@permission_required("fuel.dispense")
def dispense_create():
    return _render_dispense_form()


@sales_bp.route("/dispense",methods=["GET","POST"])
@permission_required("fuel.dispense")
def dispense():
        if request.method=="POST":
            try:
                farmer=Farmer.query.get_or_404(int(request.form["farmer_id"]))
                employee=selected_employee(farmer)
                tank_id=request.form.get("tank_id")
                if tank_id:
                    tank=FuelTank.query.get_or_404(int(tank_id))
                else:
                    tank=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).first()
                    if not tank:
                        raise ValueError("لا يوجد خزان فعال.")
                settings=ProjectSettings.get()
                if current_user.has_role("manager") or settings.allow_employee_sale_price_override:
                    price=request.form.get("sale_price_per_liter") or settings.default_sale_price_per_liter
                else:
                    price=settings.default_sale_price_per_liter
                row=create_dispense(employee,farmer,tank.id,request.form.get("drums"),price,request.form.get("paid_amount") or 0,request.form.get("notes"))
                audit("fuel.dispense.created","fuel_dispense",row.id,after={"farmer_id":farmer.id,"employee_id":employee.id,"drums":str(row.drums),"liters":str(row.liters),"total":str(row.total_amount),"credit":str(row.credit_amount),"cost":str(row.cost_amount),"document_id":row.document_id})
                db.session.commit()
                flash("تم تسجيل صرف الديزل وإصدار سند الصرف.","success")
                return redirect(url_for("sales.dispense"))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc),"danger")
        return _render_dispense_form()

    from datetime import date,datetime,time,timedelta,timezone
    from math import ceil
    from sqlalchemy import func,or_

    search=(request.args.get("q") or "").strip()
    farmer_id=(request.args.get("farmer_id") or "").strip()
    date_from=(request.args.get("date_from") or "").strip()
    date_to=(request.args.get("date_to") or "").strip()
    sort=request.args.get("sort","newest")
    start_date=end_date=None
    try:
        start_date=date.fromisoformat(date_from) if date_from else None
        end_date=date.fromisoformat(date_to) if date_to else None
    except ValueError:
        flash("صيغة التاريخ غير صحيحة؛ استخدم YYYY-MM-DD.","danger")
        start_date=end_date=None
    if start_date and end_date and end_date<start_date:
        flash("تاريخ البداية لا يمكن أن يأتي بعد تاريخ النهاية.","danger")
        start_date=end_date=None

    query=(
        FuelDispense.query
        .join(Document,FuelDispense.document_id==Document.id)
        .outerjoin(Farmer,FuelDispense.farmer_id==Farmer.id)
        .join(User,FuelDispense.employee_id==User.id)
        .filter(
            FuelDispense.status=="approved",
            FuelDispense.sale_type=="farmer",
            Document.status=="approved",
        )
    )
    if not current_user.has_role("manager"):
        query=query.filter(FuelDispense.employee_id==current_user.id)
    if farmer_id.isdigit():
        query=query.filter(FuelDispense.farmer_id==int(farmer_id))
    if start_date:
        query=query.filter(FuelDispense.created_at>=datetime.combine(start_date,time.min).replace(tzinfo=timezone.utc))
    if end_date:
        query=query.filter(FuelDispense.created_at<datetime.combine(end_date+timedelta(days=1),time.min).replace(tzinfo=timezone.utc))
    if search:
        pattern="%"+search.replace("%","\\%").replace("_","\\_")+"%"
        query=query.filter(or_(
            Farmer.name.ilike(pattern),Farmer.code.ilike(pattern),Farmer.phone.ilike(pattern),
            Document.number.ilike(pattern),User.display_name.ilike(pattern),FuelDispense.notes.ilike(pattern),
        ))

    agg=query.order_by(None).with_entities(
        func.count(FuelDispense.id),
        func.coalesce(func.sum(FuelDispense.drums),0),
        func.coalesce(func.sum(FuelDispense.liters),0),
        func.coalesce(func.sum(FuelDispense.total_amount),0),
        func.coalesce(func.sum(FuelDispense.paid_amount),0),
        func.coalesce(func.sum(FuelDispense.credit_amount),0),
    ).first()
    totals={
        "count":int(agg[0] or 0),"drums":agg[1] or 0,"liters":agg[2] or 0,
        "total_amount":agg[3] or 0,"paid_amount":agg[4] or 0,"credit_amount":agg[5] or 0,
    }
    total_count=totals["count"]
    try:
        page=max(1,int(request.args.get("page",1)))
    except (TypeError,ValueError):
        page=1
    per_page=25
    pages=max(1,ceil(total_count/per_page))

    if sort=="oldest":
        query=query.order_by(FuelDispense.created_at.asc(),FuelDispense.id.asc())
    elif sort=="farmer":
        query=query.order_by(Farmer.name.asc(),FuelDispense.created_at.desc(),FuelDispense.id.desc())
    elif sort=="amount":
        query=query.order_by(FuelDispense.total_amount.desc(),FuelDispense.created_at.desc())
    else:
        sort="newest"
        query=query.order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc())
    dispenses=query.offset((page-1)*per_page).limit(per_page).all()

    farmer_options=Farmer.query.order_by(Farmer.name.asc()).all()
    if not current_user.has_role("manager") and not user_has_permission(current_user,"farmers.view_all"):
        farmer_options=[row for row in farmer_options if row.assigned_employee_id==current_user.id]
    settings=ProjectSettings.get()
    return render_template(
        "sales/dispenses.html",dispenses=dispenses,totals=totals,total_count=total_count,
        page=page,pages=pages,search=search,farmer_id=farmer_id,date_from=date_from,
        date_to=date_to,sort=sort,farmer_options=farmer_options,settings=settings,
    )

def _can_edit_dispense(row):
    return bool(
        current_user.has_role("manager")
        or (
            row.employee_id==current_user.id
            and row.farmer is not None
            and row.farmer.assigned_employee_id==current_user.id
        )
    )


def _dispense_edit_block_reason(row):
    if row.sale_type!="farmer" or row.farmer is None:
        return "يمكن تعديل صرف المزارعين من هذه الشاشة فقط."
    if row.status!="approved" or row.document.status!="approved":
        return "هذا الصرف ليس معتمدًا أو سبق تصحيحه."
    if row.farmer.status!="approved":
        return "لا يمكن تعديل صرف لأن حساب المزارع لم يعد معتمدًا."
    allocation=(
        db.session.query(FarmerPaymentAllocation.id)
        .join(FarmerPayment,FarmerPaymentAllocation.payment_id==FarmerPayment.id)
        .join(Document,FarmerPayment.document_id==Document.id)
        .filter(
            FarmerPaymentAllocation.dispense_id==row.id,
            Document.status!="reversed",
        )
        .first()
    )
    if allocation:
        return "لا يمكن تعديل هذا الصرف لأنه مرتبط بسند قبض سابق. اعكس سند القبض أولًا حتى لا تتغير مديونية المزارع بأثر غير صحيح."
    event_date=row.created_at.date()
    settled=EmployeeSettlement.query.filter(
        EmployeeSettlement.employee_id==row.employee_id,
        EmployeeSettlement.status=="approved",
        EmployeeSettlement.period_start<=event_date,
        EmployeeSettlement.period_end>=event_date,
    ).first()
    if settled:
        return "لا يمكن تعديل هذا الصرف لأن فترة الموظف التي ينتمي إليها معتمدة في التسويات."
    return None


@sales_bp.route("/dispense/<int:dispense_id>/edit",methods=["GET","POST"])
@permission_required("fuel.dispense")
def edit_dispense(dispense_id):
    dispense=FuelDispense.query.get_or_404(dispense_id)
    if not _can_edit_dispense(dispense):
        abort(403)

    block_reason=_dispense_edit_block_reason(dispense)
    if block_reason:
        flash(block_reason,"danger")
        if dispense.farmer_id:
            return redirect(url_for("farmers.detail",farmer_id=dispense.farmer_id))
        return redirect(url_for("sales.dispense"))

    settings=ProjectSettings.get()
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).all()
    if request.method=="POST":
        try:
            farmer=dispense.farmer
            employee=dispense.employee
            tank_id=int(request.form.get("tank_id") or 0)
            tank=FuelTank.query.filter_by(id=tank_id,is_active=True).first()
            if not tank:
                raise ValueError("اختر خزانًا فعالًا.")
            try:
                drums=Decimal(str(request.form.get("drums") or ""))
                paid=Decimal(str(request.form.get("paid_amount") or 0))
                if current_user.has_role("manager") or settings.allow_employee_sale_price_override:
                    raw_price=request.form.get("sale_price_per_liter") or settings.default_sale_price_per_liter
                else:
                    raw_price=settings.default_sale_price_per_liter
                price=Decimal(str(raw_price))
            except (InvalidOperation,TypeError,ValueError):
                raise ValueError("تحقق من عدد الدباب والمدفوع وسعر اللتر؛ يجب إدخال أرقام صحيحة.")

            if drums<=0 or price<=0:
                raise ValueError("عدد الدباب وسعر اللتر يجب أن يكونا أكبر من صفر.")
            if paid<0:
                raise ValueError("المدفوع لا يمكن أن يكون سالبًا.")
            liters=drums*Decimal(str(settings.drum_liters))
            total=liters*price
            if paid>total:
                raise ValueError("المدفوع لا يمكن أن يتجاوز قيمة الصرف.")
            available_quota=farmer_account(farmer)["remaining_quota_drums"]+Decimal(str(dispense.drums))
            if drums>available_quota:
                raise ValueError(f"المتبقي للمزارع بعد احتساب الصرف الحالي هو {available_quota} دبة.")
            available_stock=current_stock_liters(tank.id)
            if tank.id==dispense.tank_id:
                available_stock+=Decimal(str(dispense.liters))
            if liters>available_stock:
                raise ValueError("المخزون في الخزان المحدد لا يكفي للكمية الجديدة.")

            before={
                "document_number":dispense.document.number,
                "farmer_id":dispense.farmer_id,
                "employee_id":dispense.employee_id,
                "tank_id":dispense.tank_id,
                "drums":str(dispense.drums),
                "liters":str(dispense.liters),
                "sale_price_per_liter":str(dispense.sale_price_per_liter),
                "total_amount":str(dispense.total_amount),
                "paid_amount":str(dispense.paid_amount),
                "credit_amount":str(dispense.credit_amount),
                "notes":dispense.notes,
            }
            original_created_at=dispense.created_at
            original_issue_date=dispense.document.issue_date
            compensation_snapshot={
                "type":dispense.employee_compensation_type or "fixed",
                "value":str(dispense.employee_compensation_value or 0),
            }

            # Keep the original approved document as an auditable reversal, then
            # post a replacement sale through the normal stock/accounting flow.
            reversal=reverse_document(
                dispense.document,current_user.id,
                "تصحيح صرف ديزل بناءً على تعديل السجل؛ راجع سند الصرف البديل في سجل التدقيق."
            )
            replacement=create_dispense(
                employee,farmer,tank.id,drums,price,paid,
                (request.form.get("notes") or "").strip() or None,
                compensation_snapshot=compensation_snapshot,
            )
            # Keep the operational occurrence date while the correction itself
            # is traceable through the newly created reversal and replacement documents.
            replacement.created_at=original_created_at
            replacement.document.issue_date=original_issue_date
            for entry in JournalEntry.query.filter_by(document_id=replacement.document_id).all():
                entry.entry_date=original_created_at.date()

            audit(
                "fuel.dispense.corrected","fuel_dispense",dispense.id,
                before=before,
                after={
                    "status":"reversed",
                    "reversal_document_id":reversal.id,
                    "replacement_dispense_id":replacement.id,
                    "replacement_document_id":replacement.document_id,
                    "drums":str(replacement.drums),
                    "liters":str(replacement.liters),
                    "total_amount":str(replacement.total_amount),
                    "credit_amount":str(replacement.credit_amount),
                },
            )
            audit(
                "fuel.dispense.replacement_created","fuel_dispense",replacement.id,
                after={"corrected_from_dispense_id":dispense.id,"document_id":replacement.document_id},
            )
            db.session.commit()
            flash(f"تم تصحيح الصرف وإصدار السند البديل {replacement.document.number}.","success")
            return redirect(url_for("farmers.detail",farmer_id=farmer.id))
        except (ValueError,TypeError,InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
            dispense=FuelDispense.query.get_or_404(dispense_id)

    return render_template(
        "sales/dispense_edit.html",
        dispense=dispense,tanks=tanks,settings=settings,
    )


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
    settings=ProjectSettings.get()
    if request.method=="POST":
        try:
            employee=current_user
            if current_user.has_role("manager") and request.form.get("employee_id"):
                employee=User.query.filter_by(id=int(request.form["employee_id"]),is_employee=True,active=True).first()
                if not employee:
                    raise ValueError("الموظف المحدد غير صالح.")
            tank_id=int(request.form.get("tank_id")) if request.form.get("tank_id") else None
            if not tank_id:
                default_tank=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).first()
                if not default_tank:
                    raise ValueError("لا يوجد خزان فعال.")
                tank_id=default_tank.id
            price=(request.form.get("sale_price_per_liter") or settings.default_sale_price_per_liter) if (current_user.has_role("manager") or settings.allow_employee_sale_price_override) else settings.default_sale_price_per_liter
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
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    selected_employee_id=request.args.get("employee_id") or ""
    if current_user.has_role("manager") and not selected_employee_id and employees:
        selected_employee_id=str(employees[0].id)
    selected_tank_id=request.args.get("tank_id") or (str(tanks[0].id) if tanks else "")
    return render_template("sales/point_of_sale.html",tanks=tanks,employees=employees,settings=settings,selected_employee_id=selected_employee_id,selected_tank_id=selected_tank_id,project_capacity=project_diesel_capacity())

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
    if start_date:
        from ...services.sales import farmer_outstanding_amount
        account["prior_balance"]=farmer_outstanding_amount(farmer.id,before_date=start_date)
    return render_template("sales/farmer_account.html",farmer=farmer,account=account,dispenses=dispenses,payments=payments,quota_movements=quota_movements,ledger=ledger,start=start_date,end=end_date)
