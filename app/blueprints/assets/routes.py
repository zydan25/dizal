from datetime import date
from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user
from sqlalchemy import func
from ...decorators import permission_required
from ...extensions import db
from ...models import Asset,Cashbox,CashboxTransaction,CapitalContribution,FuelTank,User
from ...services.assets import create_asset,update_asset_cost
from ...services.audit import audit
from ...services.fuel import current_stock_liters
from . import assets_bp

@assets_bp.get("/")
@permission_required("assets.view")
def index():
    assets=Asset.query.order_by(Asset.id.desc()).all()
    tanks=FuelTank.query.order_by(FuelTank.id.desc()).all()
    tank_rows=[{"tank":tank,"stock_liters":current_stock_liters(tank.id)} for tank in tanks]
    capital_total=db.session.query(func.coalesce(func.sum(CapitalContribution.amount),0)).filter(CapitalContribution.status=="approved").scalar() or 0
    return render_template("assets/index.html",assets=assets,tank_rows=tank_rows,capital_total=capital_total)

@assets_bp.get("/<int:asset_id>")
@permission_required("assets.view")
def detail(asset_id):
    asset=Asset.query.get_or_404(asset_id)
    return render_template("assets/detail.html",asset=asset)

@assets_bp.route("/<int:asset_id>/edit",methods=["GET","POST"])
@permission_required("assets.create")
def edit(asset_id):
    asset=Asset.query.get_or_404(asset_id)
    # Show the financial field to managers; the service performs the strict
    # document/transaction integrity checks when the value is actually saved.
    financial_editable=current_user.has_role("manager")
    if request.method=="POST":
        before={
            "name":asset.name,
            "category":asset.category,
            "cost":str(asset.acquisition_cost),
            "location":asset.location,
            "status":asset.status,
        }
        try:
            asset.name=(request.form.get("name") or asset.name).strip()
            asset.category=(request.form.get("category") or asset.category).strip()
            asset.acquisition_date=date.fromisoformat(request.form.get("acquisition_date") or asset.acquisition_date.isoformat())
            asset.custodian_user_id=int(request.form["custodian_user_id"]) if request.form.get("custodian_user_id") else None
            asset.location=(request.form.get("location") or "").strip() or None
            asset.status=(request.form.get("status") or asset.status).strip()
            asset.notes=request.form.get("notes")

            cost_raw=(request.form.get("cost") or "").strip()
            financial_changed=False
            if cost_raw:
                if not current_user.has_role("manager"):
                    raise ValueError("تعديل القيمة المالية للأصل متاح للمدير فقط.")
                old_cost=str(asset.acquisition_cost)
                new_cost=str(cost_raw)
                if new_cost != old_cost:
                    update_asset_cost(asset,cost_raw,current_user.id)
                    financial_changed=True

            audit(
                "asset.updated",
                "asset",
                asset.id,
                before=before,
                after={
                    "name":asset.name,
                    "category":asset.category,
                    "cost":str(asset.acquisition_cost),
                    "location":asset.location,
                    "status":asset.status,
                    "financial_changed":financial_changed,
                },
            )
            db.session.commit()
            flash("تم تحديث بيانات الأصل والقيمة المالية والحركات المرتبطة بها." if financial_changed else "تم تحديث بيانات الأصل.","success")
            return redirect(url_for("assets.detail",asset_id=asset.id))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template(
        "assets/form.html",
        asset=asset,
        editing=True,
        financial_editable=financial_editable,
        cashboxes=[],
        employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all(),
        today=asset.acquisition_date.isoformat(),
    )

@assets_bp.route("/new",methods=["GET","POST"])
@permission_required("assets.create")
def new():
    if request.method=="POST":
        try:
            asset=create_asset(
                name=request.form.get("name","").strip(),
                category=request.form.get("category","").strip(),
                cost=request.form.get("cost"),
                acquisition_date=date.fromisoformat(request.form.get("acquisition_date") or date.today().isoformat()),
                payer_cashbox_id=int(request.form.get("payer_cashbox_id")),
                created_by_id=__import__("flask_login").current_user.id,
                custodian_user_id=int(request.form["custodian_user_id"]) if request.form.get("custodian_user_id") else None,
                location=request.form.get("location"),
                notes=request.form.get("notes"),
                create_tank=request.form.get("create_tank")=="1",
                tank_capacity_liters=request.form.get("tank_capacity_liters") or None,
            )
            audit("asset.created","asset",asset.id,after={"asset_code":asset.asset_code,"cost":str(asset.acquisition_cost),"document_id":asset.document_id})
            db.session.commit()
            flash("تم تسجيل الأصل وخصم قيمته من الصندوق المحدد.","success")
            return redirect(url_for("assets.index"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template("assets/form.html",cashboxes=Cashbox.query.filter_by(is_active=True).all(),employees=User.query.filter_by(is_employee=True,active=True).all(),today=date.today().isoformat())