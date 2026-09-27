from flask import flash,redirect,render_template,request,url_for
from ...decorators import permission_required
from ...extensions import db
from ...models import Permission,Role,RolePermission
from ...permissions import PERMISSIONS
from ...services.audit import audit
from . import roles_bp

@roles_bp.get("/")
@permission_required("roles.manage")
def index():
    roles=Role.query.order_by(Role.name).all()
    return render_template("roles/index.html",roles=roles,permission_catalog=PERMISSIONS)

@roles_bp.route("/<int:role_id>",methods=["GET","POST"])
@permission_required("roles.manage")
def edit(role_id):
    role=Role.query.get_or_404(role_id)
    if request.method=="POST":
        selected=set(request.form.getlist("permission"))
        Permission.query.count()
        RolePermission.query.filter_by(role_id=role.id).delete()
        rows=Permission.query.filter(Permission.key.in_(selected)).all() if selected else []
        for permission in rows:
            db.session.add(RolePermission(role_id=role.id,permission_id=permission.id))
        audit("role.permissions.updated","role",role.id,after={"permissions":sorted(selected)})
        db.session.commit()
        flash("تم حفظ صلاحيات الدور.","success")
        return redirect(url_for("roles.index"))
    current={link.permission.key for link in role.permission_links}
    return render_template("roles/edit.html",role=role,permissions=PERMISSIONS,current=current)
