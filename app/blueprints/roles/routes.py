import re
from flask import abort,flash,redirect,render_template,request,url_for
from ...decorators import permission_required
from ...extensions import db
from ...models import Permission,Role,RolePermission,User
from ...permissions import PERMISSIONS
from ...services.audit import audit
from . import roles_bp


def sync_permission_catalog():
    """Ensure every permission offered by the UI exists in the database."""
    rows={row.key:row for row in Permission.query.all()}
    changed=False
    for key,(label,module) in PERMISSIONS.items():
        row=rows.get(key)
        if row is None:
            row=Permission(key=key,label=label,module=module)
            db.session.add(row)
            rows[key]=row
            changed=True
        elif row.label!=label or row.module!=module:
            row.label=label
            row.module=module
            changed=True
    if changed:
        db.session.commit()
    return rows


@roles_bp.get("/")
@permission_required("roles.manage")
def index():
    sync_permission_catalog()
    roles=Role.query.order_by(Role.name).all()
    return render_template("roles/index.html",roles=roles,permission_catalog=PERMISSIONS)


@roles_bp.route("/new",methods=["GET","POST"])
@permission_required("roles.manage")
def new():
    sync_permission_catalog()
    if request.method=="POST":
        name=(request.form.get("name") or "").strip().lower()
        label=(request.form.get("label") or "").strip()
        description=(request.form.get("description") or "").strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,39}",name):
            flash("اسم الدور البرمجي يجب أن يكون إنجليزيًا، يبدأ بحرف، ويحتوي على أحرف أو أرقام أو شرطة سفلية فقط (3–40 حرفًا).","danger")
            return render_template("roles/new.html",permissions=PERMISSIONS,values=request.form)
        if not label:
            flash("اسم الدور الظاهر للمستخدم مطلوب.","danger")
            return render_template("roles/new.html",permissions=PERMISSIONS,values=request.form)
        if Role.query.filter_by(name=name).first():
            flash("اسم الدور البرمجي مستخدم بالفعل. اختر اسمًا آخر.","danger")
            return render_template("roles/new.html",permissions=PERMISSIONS,values=request.form)
        selected=set(request.form.getlist("permission")) & set(PERMISSIONS)
        role=Role(name=name,label=label,description=description,is_system=False)
        db.session.add(role)
        db.session.flush()
        permission_rows=Permission.query.filter(Permission.key.in_(selected)).all() if selected else []
        for permission in permission_rows:
            db.session.add(RolePermission(role_id=role.id,permission_id=permission.id))
        audit("role.created","role",role.id,after={"name":name,"label":label,"permissions":sorted(selected)})
        db.session.commit()
        flash(f"تم إنشاء الدور «{label}» وربط {len(permission_rows)} صلاحية به.","success")
        return redirect(url_for("roles.edit",role_id=role.id))
    return render_template("roles/new.html",permissions=PERMISSIONS,values={})


@roles_bp.route("/<int:role_id>",methods=["GET","POST"])
@permission_required("roles.manage")
def edit(role_id):
    sync_permission_catalog()
    role=Role.query.get_or_404(role_id)
    if request.method=="POST":
        selected=set(request.form.getlist("permission")) & set(PERMISSIONS)
        permission_rows=Permission.query.filter(Permission.key.in_(selected)).all() if selected else []
        RolePermission.query.filter_by(role_id=role.id).delete(synchronize_session=False)
        for permission in permission_rows:
            db.session.add(RolePermission(role_id=role.id,permission_id=permission.id))
        audit("role.permissions.updated","role",role.id,after={"permissions":sorted(selected)})
        db.session.commit()
        flash(f"تم حفظ صلاحيات الدور «{role.label or role.name}»: {len(permission_rows)} صلاحية.","success")
        return redirect(url_for("roles.edit",role_id=role.id))
    current={link.permission.key for link in role.permission_links}
    return render_template("roles/edit.html",role=role,permissions=PERMISSIONS,current=current)


@roles_bp.post("/<int:role_id>/delete")
@permission_required("roles.manage")
def delete(role_id):
    role=Role.query.get_or_404(role_id)
    if role.is_system or role.name in {"manager","employee"}:
        flash("لا يمكن حذف الأدوار الأساسية للنظام.","danger")
        return redirect(url_for("roles.index"))
    assigned=User.query.join(User.roles).filter(Role.id==role.id).count()
    if assigned:
        flash("لا يمكن حذف هذا الدور لأنه مرتبط بمستخدمين. انقل المستخدمين إلى دور آخر أولًا.","danger")
        return redirect(url_for("roles.index"))
    name=role.label or role.name
    db.session.delete(role)
    audit("role.deleted","role",role_id,after={"name":role.name})
    db.session.commit()
    flash(f"تم حذف الدور «{name}».","success")
    return redirect(url_for("roles.index"))
