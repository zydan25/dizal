from datetime import date
from flask import flash,redirect,render_template,request,url_for
from sqlalchemy import func
from ...decorators import permission_required
from ...extensions import db
from ...models import Asset,Cashbox,CapitalContribution,FuelTank,User
from ...services.assets import create_asset
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
    if request.method=="POST":
        before={"name":asset.name,"category":asset.category,"location":asset.location,"status":asset.status}
        asset.name=(request.form.get("name") or asset.name).strip()
        asset.category=(request.form.get("category") or asset.category).strip()
        asset.acquisition_date=date.fromisoformat(request.form.get("acquisition_date") or asset.acquisition_date.isoformat())
        asset.custodian_user_id=int(request.form["custodian_user_id"]) if request.form.get("custodian_user_id") else None
        asset.location=(request.form.get("location") or "").strip() or None
        asset.status=(request.form.get("status") or asset.status).strip()
        asset.notes=request.form.get("notes")
        audit("asset.updated","asset",asset.id,before=before,after={"name":asset.name,"category":asset.category,"location":asset.location,"status":asset.status})
        db.session.commit()
        flash("تم تحديث بيانات الأصل.","success")
        return redirect(url_for("assets.detail",asset_id=asset.id))
    return render_template("assets/form.html",asset=asset,editing=True,cashboxes=[],employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all(),today=asset.acquisition_date.isoformat())

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
                notes=request.form.get("notes")
            )
            audit("asset.created","asset",asset.id,after={"asset_code":asset.asset_code,"cost":str(asset.acquisition_cost),"document_id":asset.document_id})
            db.session.commit()
            flash("تم تسجيل الأصل وخصم قيمته من الصندوق المحدد.","success")
            return redirect(url_for("assets.index"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template("assets/form.html",cashboxes=Cashbox.query.filter_by(is_active=True).all(),employees=User.query.filter_by(is_employee=True,active=True).all(),today=date.today().isoformat())