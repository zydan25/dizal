from flask import abort,flash,redirect,render_template,request,url_for
from flask_login import current_user
from flask_security.utils import hash_password,verify_password
from ...decorators import permission_required
from ...extensions import db
from ...models import Cashbox,CashboxTransaction,EmployeeProfile,Role,User,Permission,UserPermissionOverride
from ...models import Farmer
from ...permissions import PERMISSIONS
from ...services.cashbox import balance
from ...services.reports import employee_operations
from ...services.audit import audit
from . import employees_bp
import uuid
from ..models import Farmer

def employee_operations_cards(employees):
    cards=[]
    for employee in employees:
        data=employee_operations(employee.id)
        box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
        cards.append({
            "employee":employee,
            "farmer_count":Farmer.query.filter_by(assigned_employee_id=employee.id,status="approved").count(),
            "drums":data["drums"],
            "sales":data["sales"],
            "cashbox_balance":balance(box.id) if box else 0,
        })
    return cards


@employees_bp.get("/")
@permission_required("users.view")
def index():
    employees=User.query.filter_by(is_employee=True).order_by(User.id.desc()).all()
    performance_rows=employee_operations_cards(employees)
    performance_total_drums=sum((row["drums"] for row in performance_rows),0)
    performance_total_sales=sum((row["sales"] for row in performance_rows),0)
    return render_template("employees/index.html",employees=employees,employee_cards=performance_rows,performance_total_drums=performance_total_drums,performance_total_sales=performance_total_sales)

@employees_bp.route("/new",methods=["GET","POST"])
@permission_required("users.manage")
def new():
    if request.method=="POST":
        username=(request.form.get("username") or "").strip()
        phone=(request.form.get("phone") or "").strip()
        password=request.form.get("password") or ""
        name=(request.form.get("display_name") or "").strip()
        if not username or not password or not name:
            flash("الاسم واسم المستخدم وكلمة المرور مطلوبة.","danger")
            return render_template("employees/form.html")
        if User.query.filter((User.username==username)|(User.phone==phone if phone else User.phone==None)).first():
            flash("اسم المستخدم أو الهاتف مستخدم بالفعل.","danger")
            return render_template("employees/form.html")
        user=User(username=username,phone=phone or None,email=(request.form.get("email") or None),display_name=name,is_employee=True,active=True,password=hash_password(password),fs_uniquifier=uuid.uuid4().hex)
        role=Role.query.filter_by(name="employee").first()
        if not role:
            raise ValueError("دور الموظف غير موجود. نفذ seed أولًا.")
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()
        code=f"EMP-{user.id:04d}"
        profile=EmployeeProfile(user_id=user.id,employee_code=code,salary_type=request.form.get("salary_type") or "fixed",salary_value=request.form.get("salary_value") or 0,notes=request.form.get("notes"))
        db.session.add(profile)
        box=Cashbox(name=f"صندوق {name}",box_type="employee",owner_user_id=user.id,is_active=True)
        db.session.add(box)
        db.session.flush()
        audit("employee.created","user",user.id,after={"username":user.username,"employee_code":code,"cashbox_id":box.id})
        db.session.commit()
        flash("تم إنشاء الموظف والصندوق المرتبط به.","success")
        return redirect(url_for("employees.index"))
    return render_template("employees/form.html")

@employees_bp.route("/<int:user_id>/edit",methods=["GET","POST"])
@permission_required("users.manage")
def edit(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    profile=EmployeeProfile.query.filter_by(user_id=employee.id).first()
    if request.method=="POST":
        before={"display_name":employee.display_name,"phone":employee.phone,"active":employee.active,"salary_type":profile.salary_type if profile else None,"salary_value":str(profile.salary_value if profile else 0)}
        employee.display_name=(request.form.get("display_name") or employee.display_name).strip()
        employee.phone=(request.form.get("phone") or employee.phone or "").strip() or None
        employee.email=(request.form.get("email") or employee.email or "").strip() or None
        employee.active=request.form.get("active")=="1"
        if profile:
            profile.salary_type=request.form.get("salary_type") or profile.salary_type
            profile.salary_value=request.form.get("salary_value") or profile.salary_value
            profile.farmer_limit_override=request.form.get("farmer_limit_override") or None
            profile.credit_limit_override=request.form.get("credit_limit_override") or None
            profile.daily_liters_limit_override=request.form.get("daily_liters_limit_override") or None
            profile.can_change_farmer_quota=request.form.get("can_change_farmer_quota")=="1"
        audit("employee.updated","user",employee.id,before=before,after={"active":employee.active,"display_name":employee.display_name})
        db.session.commit()
        flash("تم تحديث بيانات الموظف.","success")
        return redirect(url_for("employees.index"))
    return render_template("employees/edit.html",employee=employee,profile=profile)

@employees_bp.route("/<int:user_id>/permissions",methods=["GET","POST"])
@permission_required("users.manage")
def permissions(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    role_keys=set()
    for role in employee.roles:
        role_keys.update(link.permission.key for link in role.permission_links)
    if request.method=="POST":
        UserPermissionOverride.query.filter_by(user_id=employee.id).delete()
        selected=set(request.form.getlist("permission"))
        for key in PERMISSIONS:
            if (key in selected) != (key in role_keys):
                db.session.add(UserPermissionOverride(user_id=employee.id,permission_key=key,allowed=key in selected))
        audit("employee.permissions.updated","user",employee.id,after={"permissions":sorted(selected)})
        db.session.commit()
        flash("تم حفظ صلاحيات الموظف الإضافية والاستثناءات.","success")
        return redirect(url_for("employees.index"))
    effective=set(role_keys)
    overrides={row.permission_key:row.allowed for row in employee.permission_overrides}
    for key,val in overrides.items():
        if val: effective.add(key)
        else: effective.discard(key)
    return render_template("employees/permissions.html",employee=employee,permissions=PERMISSIONS,effective=effective)



@employees_bp.get("/<int:user_id>")
@permission_required("users.view")
def detail(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    if not current_user.has_role("manager") and current_user.id!=employee.id:
        abort(403)
    operations=employee_operations(employee.id)
    farmers=Farmer.query.filter_by(assigned_employee_id=employee.id).filter(Farmer.status!="deleted").order_by(Farmer.name).limit(100).all()
    box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    sales=operations["sales"]; cost=sum((getattr(row,"cost_amount",0) for row in operations["dispenses"] if row.status=="approved"),0)
    return render_template("employees/detail.html",employee=employee,operations=operations,farmers=farmers,box=box,cashbox_balance=balance(box.id) if box else 0,profit=sales-cost)


@employees_bp.route("/password",methods=["GET","POST"])
def my_password():
    if request.method=="POST":
        current=request.form.get("current_password") or ""
        new=request.form.get("new_password") or ""
        confirm=request.form.get("confirm_password") or ""
        if not verify_password(current,current_user.password):
            flash("كلمة المرور الحالية غير صحيحة.","danger")
        elif len(new)<6:
            flash("كلمة المرور الجديدة يجب ألا تقل عن 6 أحرف.","danger")
        elif new!=confirm:
            flash("تأكيد كلمة المرور غير مطابق.","danger")
        else:
            current_user.password=hash_password(new)
            audit("employee.password.changed","user",current_user.id)
            db.session.commit()
            flash("تم تحديث كلمة المرور بنجاح.","success")
            return redirect(url_for("dashboard.index"))
    return render_template("employees/password.html",manager_reset=False,employee=current_user)


@employees_bp.route("/<int:user_id>/password",methods=["GET","POST"])
@permission_required("users.manage")
def reset_password(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    if request.method=="POST":
        new=request.form.get("new_password") or ""
        confirm=request.form.get("confirm_password") or ""
        if len(new)<6:
            flash("كلمة المرور الجديدة يجب ألا تقل عن 6 أحرف.","danger")
        elif new!=confirm:
            flash("تأكيد كلمة المرور غير مطابق.","danger")
        else:
            employee.password=hash_password(new)
            audit("employee.password.reset","user",employee.id)
            db.session.commit()
            flash("تمت إعادة تعيين كلمة مرور الموظف.","success")
            return redirect(url_for("employees.detail",user_id=employee.id))
    return render_template("employees/password.html",manager_reset=True,employee=employee)
