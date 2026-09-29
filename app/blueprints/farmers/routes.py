from pathlib import Path
from flask import current_app,flash,redirect,render_template,request,url_for,abort,send_file
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Document,EmployeeProfile,Farmer,FarmerDocument,FarmerPayment,FuelDispense,User
from ...permissions import user_has_permission
from ...services.audit import audit
from ...services.files import save_attachment
from ...services.farmers import change_quota,create_farmer,review_farmer
from ...services.sales import farmer_account
from . import farmers_bp

def visible_farmer(farmer):
    if user_has_permission(current_user,"farmers.view_all"): return True
    return farmer.assigned_employee_id==current_user.id

def editable_farmer(farmer):
    if current_user.has_role("manager"): return True
    return farmer.assigned_employee_id==current_user.id and farmer.status in {"draft","changes_requested","submitted"}

def _farmer_file_path(row):
    root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target=(root/row.storage_key).resolve()
    if root not in target.parents:
        abort(404)
    return target

def _farmer_file(row):
    target=_farmer_file_path(row)
    if not target.is_file():
        abort(404)
    return target

@farmers_bp.get("/")
@permission_required("farmers.view")
def index():
    query=Farmer.query.order_by(Farmer.created_at.desc())
    if not user_has_permission(current_user,"farmers.view_all"):
        query=query.filter_by(assigned_employee_id=current_user.id)
    status=request.args.get("status")
    search=(request.args.get("search") or "").strip()
    sort=request.args.get("sort") or "name"
    if search:
        like="%"+search+"%"
        query=query.filter((Farmer.name.ilike(like))|(Farmer.phone.ilike(like))|(Farmer.code.ilike(like)))
    if status:
        query=query.filter_by(status=status)
    else:
        query=query.filter(Farmer.status!="deleted")
    farmers=query.limit(100).all()
    cards=[]
    for farmer in farmers:
        account=farmer_account(farmer)
        cards.append({"farmer":farmer,"account":account})
    visible_query=Farmer.query
    if not user_has_permission(current_user,"farmers.view_all"):
        visible_query=visible_query.filter_by(assigned_employee_id=current_user.id)
    visible=visible_query.filter(Farmer.status!="deleted").all()
    sorters={"name":lambda x:x["farmer"].name.casefold(),"consumed":lambda x:x["account"]["consumed_drums"],"remaining":lambda x:x["account"]["remaining_quota_drums"],"debt":lambda x:x["account"]["outstanding_amount"]}
    cards.sort(key=sorters.get(sort,sorters["name"]),reverse=sort!="name")
    stats={
        "total":len(visible),
        "approved":sum(1 for row in visible if row.status=="approved"),
        "suspended":sum(1 for row in visible if row.status=="suspended"),
        "pending":sum(1 for row in visible if row.status in {"submitted","changes_requested"}),
        "consumed":sum((item["account"]["consumed_drums"] for item in cards),0),
        "remaining":sum((item["account"]["remaining_quota_drums"] for item in cards),0),
        "debt":sum((item["account"]["outstanding_amount"] for item in cards),0),
    }
    return render_template("farmers/index.html",cards=cards,farmers=farmers,status=status,search=search,sort=sort,stats=stats,can_create_farmer=user_has_permission(current_user,"farmers.create"))

@farmers_bp.route("/new",methods=["GET","POST"])
@permission_required("farmers.create")
def new():
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all() if user_has_role_manager() else []
    if request.method=="POST":
        try:
            assigned=int(request.form.get("employee_id") or current_user.id)
            if not user_has_role_manager() and assigned!=current_user.id: abort(403)
            attachments=[]
            for field,doc_type in (("id_front","id_front"),("id_back","id_back"),("contract","contract"),("other_document","other")):
                file=request.files.get(field)
                if file and file.filename:
                    attachments.append((doc_type,save_attachment(file,current_app.config["UPLOAD_FOLDER"],"farmers")))
            farmer=create_farmer(request.form.get("name",""),request.form.get("phone",""),request.form.get("address"),request.form.get("notes"),request.form.get("quota_drums") or 0,request.form.get("credit_limit_drums") or 0,assigned,current_user.id,attachments)
            audit("farmer.created","farmer",farmer.id,after={"code":farmer.code,"assigned_employee_id":assigned,"status":"submitted"})
            db.session.commit()
            flash("تم إرسال المزارع للمراجعة والاعتماد.","success")
            return redirect(url_for("farmers.detail",farmer_id=farmer.id))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    return render_template("farmers/form.html",employees=employees)

@farmers_bp.route("/<int:farmer_id>/edit",methods=["GET","POST"])
@permission_required("farmers.create")
def edit(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not editable_farmer(farmer): abort(403)
    if request.method=="POST":
        before={"name":farmer.name,"phone":farmer.phone,"address":farmer.address,"status":farmer.status}
        try:
            farmer.name=(request.form.get("name") or farmer.name).strip()
            farmer.phone=(request.form.get("phone") or farmer.phone).strip()
            farmer.address=(request.form.get("address") or "").strip() or None
            farmer.notes=request.form.get("notes")
            uploaded=0
            for field,doc_type in (("id_front","id_front"),("id_back","id_back"),("contract","contract"),("other_document","other")):
                file=request.files.get(field)
                if file and file.filename:
                    db.session.add(FarmerDocument(farmer_id=farmer.id,document_type=doc_type,created_by_id=current_user.id,**save_attachment(file,current_app.config["UPLOAD_FOLDER"],"farmers")))
                    uploaded+=1
            replaced=0
            for doc in list(farmer.documents):
                file=request.files.get(f"replace_{doc.id}")
                if not file or not file.filename:
                    continue
                old_key=doc.storage_key
                saved=save_attachment(file,current_app.config["UPLOAD_FOLDER"],"farmers")
                doc.original_name=saved["original_name"]
                doc.storage_key=saved["storage_key"]
                doc.mime_type=saved.get("mime_type")
                doc.size_bytes=saved.get("size_bytes")
                doc.sha256=saved.get("sha256")
                try:
                    root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
                    old_path=(root/old_key).resolve()
                    if root in old_path.parents and old_path.is_file():
                        old_path.unlink()
                except OSError:
                    pass
                replaced+=1
            if not current_user.has_role("manager") and farmer.status=="changes_requested":
                farmer.status="submitted";farmer.review_note=None
            audit("farmer.updated","farmer",farmer.id,before=before,after={"name":farmer.name,"phone":farmer.phone,"status":farmer.status,"uploaded_documents":uploaded,"replaced_documents":replaced})
            db.session.commit()
            flash("تم حفظ بيانات المزارع وإعادة إرساله للمراجعة." if before["status"]=="changes_requested" and farmer.status=="submitted" else "تم تحديث بيانات المزارع.","success")
            return redirect(url_for("farmers.detail",farmer_id=farmer.id))
        except (ValueError,TypeError) as exc:
            db.session.rollback();flash(str(exc),"danger")
    return render_template("farmers/edit.html",farmer=farmer)

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
    account=farmer_account(farmer)
    dispenses=FuelDispense.query.filter_by(farmer_id=farmer.id).order_by(FuelDispense.created_at.desc(),FuelDispense.id.desc()).limit(120).all()
    payments=(FarmerPayment.query.join(Document,FarmerPayment.document_id==Document.id)
              .filter(FarmerPayment.farmer_id==farmer.id,Document.status!="reversed")
              .order_by(FarmerPayment.created_at.desc(),FarmerPayment.id.desc()).limit(120).all())
    operations=[{"kind":"dispense","date":row.created_at,"row":row} for row in dispenses if row.status=="approved"]
    operations += [{"kind":"payment","date":row.created_at,"row":row} for row in payments]
    operations.sort(key=lambda item:item["date"],reverse=True)
    return render_template("farmers/detail.html",farmer=farmer,account=account,operations=operations)

@farmers_bp.get("/<int:farmer_id>/documents/<int:document_id>")
@permission_required("farmers.view")
def farmer_document(farmer_id,document_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not visible_farmer(farmer): abort(403)
    row=FarmerDocument.query.filter_by(id=document_id,farmer_id=farmer.id).first_or_404()
    return send_file(_farmer_file(row),as_attachment=request.args.get("download")=="1",download_name=row.original_name)

@farmers_bp.post("/<int:farmer_id>/review")
@permission_required("farmers.approve")
def review(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    try:
        action=request.form.get("action")
        review_farmer(farmer,action,current_user.id,request.form.get("note"))
        audit(f"farmer.{action}","farmer",farmer.id,after={"status":farmer.status,"note":farmer.review_note})
        db.session.commit();flash("تم تحديث حالة المزارع.","success")
    except ValueError as exc:
        db.session.rollback();flash(str(exc),"danger")
    return redirect(url_for("farmers.pending"))

@farmers_bp.post("/<int:farmer_id>/quota")
@permission_required("farmers.quota.change")
def quota(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    try:
        movement=change_quota(farmer,request.form.get("quota_drums"),request.form.get("credit_limit_drums"),current_user.id,request.form.get("reason"))
        audit("farmer.quota.changed","farmer",farmer.id,after={"quota_drums":str(movement.new_quota_drums),"credit_limit_drums":str(movement.new_credit_limit_drums)})
        db.session.commit();flash("تم تعديل سقف المزارع وتسجيل سبب التغيير.","success")
    except ValueError as exc:
        db.session.rollback();flash(str(exc),"danger")
    return redirect(url_for("farmers.detail",farmer_id=farmer.id))

@farmers_bp.post("/<int:farmer_id>/documents/<int:document_id>/delete")
@permission_required("farmers.create")
def delete_document(farmer_id,document_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    if not editable_farmer(farmer):
        abort(403)
    row=FarmerDocument.query.filter_by(id=document_id,farmer_id=farmer.id).first_or_404()
    old_path=_farmer_file_path(row)
    db.session.delete(row)
    audit("farmer.document.deleted","farmer",farmer.id,after={"document_id":document_id,"document_type":row.document_type})
    db.session.commit()
    try:
        root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
        if root in old_path.parents and old_path.is_file():
            old_path.unlink()
    except OSError:
        pass
    flash("تم حذف المرفق من ملف المزارع.","success")
    return redirect(url_for("farmers.edit",farmer_id=farmer.id))


def user_has_role_manager():
    return current_user.has_role("manager")
@farmers_bp.post("/<int:farmer_id>/status")
@permission_required("farmers.approve")
def status_change(farmer_id):
    farmer=Farmer.query.get_or_404(farmer_id)
    action=request.form.get("action")
    if action=="suspend":
        farmer.status="suspended"; message="تم إيقاف المزارع مع إبقاء سجله وحركاته المالية."
    elif action=="activate":
        farmer.status="approved"; message="تم إعادة تفعيل المزارع."
    elif action=="delete":
        farmer.status="deleted"; message="تمت أرشفة المزارع وإخفاؤه من القوائم التشغيلية مع الحفاظ على السجلات."
    else:
        abort(400,description="إجراء غير معروف.")
    audit("farmer."+action,"farmer",farmer.id,after={"status":farmer.status})
    db.session.commit()
    flash(message,"success")
    return redirect(url_for("farmers.index"))

