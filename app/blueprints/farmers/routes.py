from flask import current_app,flash,redirect,render_template,request,url_for,abort
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import EmployeeProfile,Farmer,User
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.files import save_attachment
from ...services.farmers import change_quota,create_farmer,review_farmer
from . import farmers_bp

def visible_farmer(farmer):
    if user_has_permission(current_user,"farmers.view_all"): return True
    return farmer.assigned_employee_id==current_user.id

@farmers_bp.get("/")
@permission_required("farmers.view")
def index():
    query=Farmer.query.order_by(Farmer.created_at.desc())
    if not user_has_permission(current_user,"farmers.view_all"):
        query=query.filter_by(assigned_employee_id=current_user.id)
    status=request.args.get("status")
    if status: query=query.filter_by(status=status)
    return render_template("farmers/index.html",farmers=query.limit(100).all(),status=status)

@farmers_bp.route("/new",methods=["GET","POST"])
@permission_required("farmers.create")
def new():
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if user_has_role_manager() else []
    if request.method=="POST":
        try:
            assigned=int(request.form.get("employee_id") or current_user.id)
            if not user_has_role_manager() and assigned!=current_user.id:
                abort(403)
            attachments=[]
            for field,doc_type in (("id_front","id_front"),("id_back","id_back"),("contract","contract"),("other_document","other")):
                file=request.files.get(field)
                if file and file.filename:
                    attachments.append((doc_type,save_attachment(file,current_app.config["UPLOAD_FOLDER"],"farmers")))
            farmer=create_farmer(request.form.get("name",""),request.form.get("phone",""),request.form.get("address"),request.form.get("notes"),request.form.get("quota_drums") or 0,request.form.get("credit_limit_drums") or 0,assigned,current_user.id,attachments)
            audit("farmer.created","farmer",farmer.id,after={"code":farmer.code,"assigned_employee_id":assigned,"status":"submitted"})
            db.session.commit()
            flash("تم إرسال المزارع للمراجعة والاعتماد.","success")
            return redirect(url_for("farmers.index"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template("farmers/form.html",employees=employees)

@farmers_bp.get("/pending")
@permission_required("farmers.approve")
def pending():
    rows=Farmer.query.filter(Farmer.status.in_([ "submitted","changes_requested" ])).order_by(Farmer.created_at.desc()).all()
    return render_template("farmers/pending.html",farmers=rows)

@farmers_bp.get("/<int:farmer_id>")
@permission_required("farmers.view")
def detail(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not visible_farmer(farmer): abort(403)
    return render_template("farmers/detail.html",farmer=farmer)

@farmers_bp.post("/<int:farmer_id>/review")
@permission_required("farmers.approve")
def review(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    try:
        action=request.form.get("action")
        review_farmer(farmer,action,current_user.id,request.form.get("note"))
        audit(f"farmer.{action}","farmer",farmer.id,after={"status":farmer.status,"note":farmer.review_note})
        db.session.commit()
        flash("تم تحديث حالة المزارع.","success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc),"danger")
    return redirect(url_for("farmers.pending"))

@farmers_bp.post("/<int:farmer_id>/quota")
@permission_required("farmers.quota.change")
def quota(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    try:
        movement=change_quota(farmer,request.form.get("quota_drums"),request.form.get("credit_limit_drums"),current_user.id,request.form.get("reason"))
        audit("farmer.quota.changed","farmer",farmer.id,after={"quota_drums":str(movement.new_quota_drums),"credit_limit_drums":str(movement.new_credit_limit_drums)})
        db.session.commit()
        flash("تم تعديل سقف المزارع وتسجيل سبب التغيير.","success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc),"danger")
    return redirect(url_for("farmers.detail",farmer_id=farmer.id))

def user_has_role_manager():
    return current_user.has_role("manager")
