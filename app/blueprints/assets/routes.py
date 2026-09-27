from datetime import date
from flask import flash,redirect,render_template,request,url_for
from ...decorators import permission_required
from ...extensions import db
from ...models import Asset,Cashbox,User
from ...services.assets import create_asset
from ...services.audit import audit
from . import assets_bp

@assets_bp.get("/")
@permission_required("assets.view")
def index():
    assets=Asset.query.order_by(Asset.id.desc()).all()
    return render_template("assets/index.html",assets=assets)

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
