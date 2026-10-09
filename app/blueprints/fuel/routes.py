from datetime import date
from flask import current_app,flash,redirect,render_template,request,url_for
from flask_login import current_user
from sqlalchemy import func
from ...decorators import permission_required
from ...extensions import db
from ...models import Asset,Cashbox,FuelPurchase,FuelStockMovement,FuelTank,ProjectSettings,User
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.cashbox import balance
from ...services.files import save_attachment
from ...services.fuel import approve_purchase,attach_proof,create_purchase,current_stock_liters,update_purchase
from ...services.assets import create_asset
from ...services.notifications import notify_user
from . import fuel_bp

def _use_employee_water_theme():
    settings=ProjectSettings.get()
    return (
        current_user.is_authenticated
        and current_user.is_employee
        and settings.employee_dashboard_theme=="water"
        and not user_has_permission(current_user,"users.manage")
    )


def _notify_supply_reviewers(purchase,title,message):
    for reviewer in User.query.filter_by(active=True).all():
        if reviewer.id==current_user.id:
            continue
        if user_has_permission(reviewer,"fuel.supply.approve"):
            notify_user(reviewer.id,title,message,"info",url_for("fuel.supply"))


def _supply_cashbox_balance(user_id):
    box=Cashbox.query.filter_by(owner_user_id=user_id,box_type="employee",is_active=True).first()
    return balance(box.id) if box else None


@fuel_bp.route("/supply",methods=["GET","POST"])
@permission_required("fuel.supply.create")
def supply():
    form_error=False
    if request.method=="POST":
        try:
            employee_id=current_user.id
            if current_user.has_role("manager") and request.form.get("employee_id"):
                employee_id=int(request.form["employee_id"])
                employee=User.query.filter_by(id=employee_id,is_employee=True,active=True).first()
                if not employee:
                    raise ValueError("الموظف المحدد غير صالح.")
            selected_tank_id=request.form.get("tank_id")
            if selected_tank_id:
                tank_id=int(selected_tank_id)
            else:
                first_tank=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).first()
                if not first_tank:
                    raise ValueError("لا يوجد خزان فعال.")
                tank_id=first_tank.id
            row=create_purchase(
                employee_id=employee_id,
                tank_id=tank_id,
                purchase_date=date.fromisoformat(request.form.get("purchase_date") or date.today().isoformat()),
                supplier_name=(request.form.get("supplier_name") or "").strip() or None,
                liters=request.form.get("liters"),
                diesel_amount=request.form.get("diesel_amount"),
                delivery_fee=request.form.get("delivery_fee") or 0,
                other_fee=request.form.get("other_fee") or 0,
                created_by_id=current_user.id,
                notes=request.form.get("notes"),
                status="submitted",
            )
            proof=request.files.get("proof")
            if proof and proof.filename:
                attach_proof(row,save_attachment(proof,current_app.config["UPLOAD_FOLDER"],"fuel"))
            if current_user.has_role("manager"):
                approve_purchase(row,current_user.id)
            audit("fuel.purchase.created","fuel_purchase",row.id,after={
                "status":row.status,"employee_id":row.employee_id,"liters":str(row.liters),
                "amount":str(row.landed_cost),"document_id":row.document_id
            })
            if row.status=="submitted":
                _notify_supply_reviewers(row,"توريد ديزل جديد","رفع الموظف توريدًا جديدًا يحتاج إلى المراجعة والاعتماد.")
            db.session.commit()
            flash("تم تسجيل التوريد واعتماده مباشرة." if row.status=="approved" else "تم رفع التوريد بنجاح، وهو الآن بانتظار اعتماد المدير.","success")
            return redirect(url_for("fuel.supply"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            form_error=True
            flash(str(exc),"danger")

    purchases=(
        FuelPurchase.query.order_by(FuelPurchase.id.desc()).limit(50).all()
        if current_user.has_role("manager")
        else FuelPurchase.query.filter_by(employee_id=current_user.id).order_by(FuelPurchase.id.desc()).limit(50).all()
    )
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    selected_tank_id=request.args.get("tank_id") or (str(tanks[0].id) if tanks else "")
    settings=ProjectSettings.get()
    themed=_use_employee_water_theme()
    template="fuel/supply_theme2.html" if themed else "fuel/supply.html"
    return render_template(
        template,purchases=purchases,tanks=tanks,employees=employees,today=date.today().isoformat(),
        selected_tank_id=selected_tank_id,editing=None,form_error=form_error,
        supply_cashbox_balance=_supply_cashbox_balance(current_user.id) if current_user.is_employee else None,
        supply_project_name=settings.project_name,
    )


@fuel_bp.route("/supply/<int:purchase_id>/edit",methods=["GET","POST"])
@permission_required("fuel.supply.create")
def edit_supply(purchase_id):
    purchase=FuelPurchase.query.get_or_404(purchase_id)
    can_manage_all=user_has_permission(current_user,"users.manage")
    if not can_manage_all and purchase.employee_id!=current_user.id:
        abort(403)
    if purchase.status not in {"submitted","changes_requested"}:
        flash("لا يمكن تعديل التوريد بعد اعتماده أو إغلاقه.","danger")
        return redirect(url_for("fuel.supply"))

    form_error=False
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.id.asc()).all()
    if request.method=="POST":
        try:
            tank_id=int(request.form.get("tank_id") or 0)
            new_row=update_purchase(
                purchase=purchase,
                tank_id=tank_id,
                purchase_date=date.fromisoformat(request.form.get("purchase_date") or date.today().isoformat()),
                liters=request.form.get("liters"),
                diesel_amount=request.form.get("diesel_amount"),
                delivery_fee=request.form.get("delivery_fee") or 0,
                other_fee=request.form.get("other_fee") or 0,
                notes=request.form.get("notes"),
            )
            proof=request.files.get("proof")
            if proof and proof.filename:
                attach_proof(new_row,save_attachment(proof,current_app.config["UPLOAD_FOLDER"],"fuel"))
            audit("fuel.purchase.updated","fuel_purchase",new_row.id,after={
                "status":new_row.status,"employee_id":new_row.employee_id,"tank_id":new_row.tank_id,
                "liters":str(new_row.liters),"amount":str(new_row.landed_cost),"document_id":new_row.document_id
            })
            _notify_supply_reviewers(new_row,"تعديل توريد ديزل","تم تعديل توريد غير معتمد وإعادة إرساله للمراجعة.")
            db.session.commit()
            flash("تم حفظ تعديل التوريد وإعادة إرساله للمدير للاعتماد.","success")
            return redirect(url_for("fuel.supply"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            form_error=True
            flash(str(exc),"danger")
            purchase=FuelPurchase.query.get_or_404(purchase_id)

    purchases=(
        FuelPurchase.query.order_by(FuelPurchase.id.desc()).limit(50).all()
        if current_user.has_role("manager")
        else FuelPurchase.query.filter_by(employee_id=current_user.id).order_by(FuelPurchase.id.desc()).limit(50).all()
    )
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if current_user.has_role("manager") else []
    settings=ProjectSettings.get()
    themed=_use_employee_water_theme()
    template="fuel/supply_theme2.html" if themed else "fuel/supply_edit.html"
    return render_template(
        template,purchases=purchases,tanks=tanks,employees=employees,today=date.today().isoformat(),
        selected_tank_id=str(purchase.tank_id),editing=purchase,form_error=form_error,
        supply_cashbox_balance=_supply_cashbox_balance(purchase.employee_id),
        supply_project_name=settings.project_name,
    )


@fuel_bp.post("/supply/<int:purchase_id>/review")
@permission_required("fuel.supply.approve")
def review(purchase_id):
    purchase=FuelPurchase.query.get_or_404(purchase_id)
    action=request.form.get("action") or "approve"
    if action=="approve":
        try:
            approve_purchase(purchase,current_user.id)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc),"danger")
            return redirect(url_for("fuel.supply"))
        new_status="approved"
    elif action in {"changes_requested","rejected","cancelled"}:
        if purchase.status!="submitted":
            flash("لا يمكن تغيير حالة التوريد بعد اعتماده.","danger")
            return redirect(url_for("fuel.supply"))
        purchase.status=action
        purchase.document.status=action
        new_status=action
    else:
        flash("الإجراء غير صالح.","danger")
        return redirect(url_for("fuel.supply"))
    audit("fuel.purchase.reviewed","fuel_purchase",purchase.id,after={"status":new_status,"note":request.form.get("note")})
    labels={"approved":"تم اعتماد التوريد","changes_requested":"طُلب استكمال التوريد","rejected":"تم رفض التوريد","cancelled":"تم إلغاء التوريد"}
    notify_user(
        purchase.employee_id,
        labels[new_status],
        request.form.get("note") or "راجع التوريد من شاشة التوريدات.",
        "warning" if new_status!="approved" else "info",
        url_for("fuel.supply"),
    )
    db.session.commit()
    flash("تم تحديث حالة التوريد.","success")
    return redirect(url_for("fuel.supply"))

@fuel_bp.post("/supply/<int:purchase_id>/approve")
@permission_required("fuel.supply.approve")
def approve(purchase_id):
    return review(purchase_id)

@fuel_bp.get("/stock")
@permission_required("fuel.stock.view")
def stock():
    tanks=FuelTank.query.filter_by(is_active=True).all()
    rows=[{"tank":tank,"stock":current_stock_liters(tank.id)} for tank in tanks]
    return render_template("fuel/stock.html",rows=rows,total=current_stock_liters())

def _next_tank_code():
    number=FuelTank.query.count()+1
    while FuelTank.query.filter_by(code=f"TANK-{number:04d}").first():
        number+=1
    return f"TANK-{number:04d}"

def _tank_stats(tank):
    inbound=db.session.query(func.coalesce(func.sum(FuelStockMovement.liters),0)).filter(
        FuelStockMovement.tank_id==tank.id,FuelStockMovement.direction=="IN"
    ).scalar() or 0
    outbound=db.session.query(func.coalesce(func.sum(FuelStockMovement.liters),0)).filter(
        FuelStockMovement.tank_id==tank.id,FuelStockMovement.direction=="OUT"
    ).scalar() or 0
    stock=current_stock_liters(tank.id)
    capacity=tank.capacity_liters
    percent=float((stock/ capacity)*100) if capacity and capacity>0 else None
    return {"inbound":inbound,"outbound":outbound,"stock":stock,"capacity_percent":min(max(percent or 0,0),100) if percent is not None else None}

@fuel_bp.route("/tanks",methods=["GET","POST"])
@permission_required("fuel.tank.manage")
def tanks():
    if request.method=="POST":
        try:
            name=(request.form.get("name") or "").strip()
            cost=request.form.get("asset_cost")
            cashbox_id=request.form.get("payer_cashbox_id")
            capacity=request.form.get("capacity_liters") or None
            if not name: raise ValueError("اسم الخزان مطلوب.")
            if not cost or not cashbox_id: raise ValueError("قيمة الخزان والصندوق الدافع مطلوبان.")
            asset=create_asset(
                name=name,category="خزان ديزل",cost=cost,
                acquisition_date=date.fromisoformat(request.form.get("purchase_date") or date.today().isoformat()),
                payer_cashbox_id=int(cashbox_id),created_by_id=current_user.id,
                custodian_user_id=int(request.form["custodian_user_id"]) if request.form.get("custodian_user_id") else None,
                location=(request.form.get("location") or "").strip() or None,
                notes=(request.form.get("notes") or "").strip() or None,
                create_tank=True,tank_capacity_liters=capacity,
            )
            tank=asset.tank
            audit("fuel.tank.created","fuel_tank",tank.id,after={
                "name":tank.name,"code":tank.code,"asset_id":asset.id,
                "asset_code":asset.asset_code,"cost":str(asset.acquisition_cost),
                "cashbox_id":asset.payer_cashbox_id,
            })
            db.session.commit()
            flash("تم إنشاء الخزان وتسجيله تلقائيًا كأصل ثابت مع خصم قيمته من الصندوق المحدد.","success")
            return redirect(url_for("fuel.tanks"))
        except (ValueError,TypeError) as exc:
            db.session.rollback();flash(str(exc),"danger")
    tanks=FuelTank.query.order_by(FuelTank.id.desc()).all()
    ids=[tank.id for tank in tanks]
    linked=Asset.query.filter(Asset.tank_id.in_(ids)).all() if ids else []
    asset_map={asset.tank_id:asset for asset in linked}
    rows=[{"tank":tank,"stats":_tank_stats(tank),"asset":asset_map.get(tank.id)} for tank in tanks]
    cashboxes=Cashbox.query.filter_by(is_active=True).order_by(Cashbox.box_type,Cashbox.name).all()
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all()
    return render_template("fuel/tanks.html",rows=rows,cashboxes=cashboxes,employees=employees,today=date.today().isoformat())

@fuel_bp.route("/tanks/<int:tank_id>/edit",methods=["GET","POST"])
@permission_required("fuel.tank.manage")
def edit_tank(tank_id):
    tank=FuelTank.query.get_or_404(tank_id)
    if request.method=="POST":
        try:
            tank.name=(request.form.get("name") or tank.name).strip()
            tank.capacity_liters=request.form.get("capacity_liters") or None
            tank.location=(request.form.get("location") or "").strip() or None
            tank.notes=(request.form.get("notes") or "").strip() or None
            tank.is_active=request.form.get("is_active")=="1"
            audit("fuel.tank.updated","fuel_tank",tank.id,after={"name":tank.name,"capacity_liters":str(tank.capacity_liters or 0),"is_active":tank.is_active})
            db.session.commit()
            flash("تم تحديث بيانات الخزان.","success")
            return redirect(url_for("fuel.tanks"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template("fuel/tank_form.html",tank=tank)

@fuel_bp.get("/tanks/<int:tank_id>")
@permission_required("fuel.stock.view")
def tank_detail(tank_id):
    tank=FuelTank.query.get_or_404(tank_id)
    stats=_tank_stats(tank)
    purchases=FuelPurchase.query.filter_by(tank_id=tank.id).order_by(FuelPurchase.id.desc()).limit(50).all()
    movements=FuelStockMovement.query.filter_by(tank_id=tank.id).order_by(FuelStockMovement.id.desc()).limit(80).all()
    return render_template("fuel/tank_detail.html",tank=tank,stats=stats,purchases=purchases,movements=movements)
