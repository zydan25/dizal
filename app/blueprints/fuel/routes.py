from datetime import date
from flask import current_app,flash,redirect,render_template,request,url_for
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import FuelPurchase,FuelTank
from ...services.audit import audit
from ...services.files import save_attachment
from ...services.fuel import approve_purchase,attach_proof,create_purchase,current_stock_liters
from . import fuel_bp

@fuel_bp.route("/supply",methods=["GET","POST"])
@permission_required("fuel.supply.create")
def supply():
    if request.method=="POST":
        try:
            row=create_purchase(
                employee_id=current_user.id,
                tank_id=int(request.form["tank_id"]),
                purchase_date=date.fromisoformat(request.form.get("purchase_date") or date.today().isoformat()),
                supplier_name=request.form.get("supplier_name"),
                liters=request.form.get("liters"),
                diesel_amount=request.form.get("diesel_amount"),
                delivery_fee=request.form.get("delivery_fee") or 0,
                other_fee=request.form.get("other_fee") or 0,
                created_by_id=current_user.id,
                notes=request.form.get("notes"),
                status="submitted"
            )
            proof=request.files.get("proof")
            if proof and proof.filename:
                attach_proof(row,save_attachment(proof,current_app.config["UPLOAD_FOLDER"],"fuel"))
            if current_user.has_role("manager"):
                approve_purchase(row,current_user.id)
            audit("fuel.purchase.created","fuel_purchase",row.id,after={"status":row.status,"liters":str(row.liters),"amount":str(row.landed_cost)})
            db.session.commit()
            flash("تم تسجيل التوريد." if row.status=="submitted" else "تم تسجيل التوريد واعتماده مباشرة.","success")
            return redirect(url_for("fuel.supply"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    purchases=FuelPurchase.query.order_by(FuelPurchase.id.desc()).limit(50).all() if current_user.has_role("manager") else FuelPurchase.query.filter_by(employee_id=current_user.id).order_by(FuelPurchase.id.desc()).limit(50).all()
    tanks=FuelTank.query.filter_by(is_active=True).order_by(FuelTank.name).all()
    return render_template("fuel/supply.html",purchases=purchases,tanks=tanks,today=date.today().isoformat())

@fuel_bp.post("/supply/<int:purchase_id>/approve")
@permission_required("fuel.supply.approve")
def approve(purchase_id):
    purchase=FuelPurchase.query.get_or_404(purchase_id)
    try:
        approve_purchase(purchase,current_user.id)
        audit("fuel.purchase.approved","fuel_purchase",purchase.id,after={"status":"approved","document_id":purchase.document_id})
        db.session.commit()
        flash("تم اعتماد التوريد وإضافة الديزل للمخزون وخصمه من صندوق الموظف.","success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc),"danger")
    return redirect(url_for("fuel.supply"))

@fuel_bp.get("/stock")
@permission_required("fuel.stock.view")
def stock():
    tanks=FuelTank.query.filter_by(is_active=True).all()
    rows=[{"tank":tank,"stock":current_stock_liters(tank.id)} for tank in tanks]
    return render_template("fuel/stock.html",rows=rows,total=current_stock_liters())
