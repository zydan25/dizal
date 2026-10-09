from flask import abort,flash,redirect,render_template,request,url_for
from flask_login import current_user
from flask_security.utils import hash_password,verify_password
from ...decorators import permission_required
from ...extensions import db
from ...models import Cashbox,CashboxTransaction,EmployeeProfile,Role,User,Permission,UserPermissionOverride
from ...models import Farmer,FuelDispense,FuelPurchase,FarmerPayment,CapitalAllocation,EmployeeSettlement,OperatingExpense,JournalLine,AuditLog
from ...permissions import PERMISSIONS
from ...services.cashbox import balance
from ...services.reports import employee_operations,employee_finance_summary
from ...services.audit import audit
from . import employees_bp
import uuid

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
    roles=Role.query.order_by(Role.name).all()
    if request.method=="POST":
        username=(request.form.get("username") or "").strip()
        phone=(request.form.get("phone") or "").strip()
        password=request.form.get("password") or ""
        name=(request.form.get("display_name") or "").strip()
        role_name=(request.form.get("role") or "employee").strip()
        if not username or not password or not name:
            flash("الاسم واسم المستخدم وكلمة المرور مطلوبة.","danger")
            return render_template("employees/form.html",roles=roles)
        if User.query.filter((User.username==username)|(User.phone==phone if phone else User.phone==None)).first():
            flash("اسم المستخدم أو الهاتف مستخدم بالفعل.","danger")
            return render_template("employees/form.html",roles=roles)
        role=Role.query.filter_by(name=role_name).first()
        if not role:
            flash("الدور المحدد غير موجود.","danger")
            return render_template("employees/form.html",roles=roles)
        user=User(username=username,phone=phone or None,email=(request.form.get("email") or None),display_name=name,is_employee=True,active=True,password=hash_password(password),fs_uniquifier=uuid.uuid4().hex)
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()
        code=f"EMP-{user.id:04d}"
        salary_type=request.form.get("salary_type") or "fixed"
        if salary_type not in {"fixed","per_liter","per_drum","percent_profit","commission"}: salary_type="fixed"
        profile=EmployeeProfile(user_id=user.id,employee_code=code,salary_type=salary_type,salary_value=request.form.get("salary_value") or 0,notes=request.form.get("notes"))
        db.session.add(profile)
        box=Cashbox(name=f"صندوق {name}",box_type="employee",owner_user_id=user.id,is_active=True)
        db.session.add(box)
        db.session.flush()
        audit("employee.created","user",user.id,after={"username":user.username,"employee_code":code,"cashbox_id":box.id})
        db.session.commit()
        flash("تم إنشاء الموظف والصندوق المرتبط به.","success")
        return redirect(url_for("employees.index"))
    return render_template("employees/form.html",roles=roles)

@employees_bp.route("/<int:user_id>/edit",methods=["GET","POST"])
@permission_required("users.manage")
def edit(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    roles=Role.query.order_by(Role.name).all()
    profile=EmployeeProfile.query.filter_by(user_id=employee.id).first()
    if request.method=="POST":
        before={"display_name":employee.display_name,"phone":employee.phone,"active":employee.active,"salary_type":profile.salary_type if profile else None,"salary_value":str(profile.salary_value if profile else 0)}
        employee.display_name=(request.form.get("display_name") or employee.display_name).strip()
        employee.phone=(request.form.get("phone") or employee.phone or "").strip() or None
        employee.email=(request.form.get("email") or employee.email or "").strip() or None
        employee.active=request.form.get("active")=="1"
        role_name=(request.form.get("role") or "").strip()
        role_changed=False
        if role_name:
            role=Role.query.filter_by(name=role_name).first()
            if not role: raise ValueError("الدور المحدد غير موجود.")
            if employee.id==current_user.id and employee.has_role("manager") and role.name!="manager":
                raise ValueError("لا يمكنك إزالة صلاحية المدير من حسابك الحالي.")
            prior_role_ids={item.id for item in employee.roles}
            role_changed=prior_role_ids!={role.id}
            employee.roles[:]=[role]
            if role_changed:
                # Overrides are relative to the old role. Clear them on role
                # changes so they cannot silently defeat the newly selected role.
                UserPermissionOverride.query.filter_by(user_id=employee.id).delete(synchronize_session=False)
        if profile:
            salary_type=request.form.get("salary_type") or profile.salary_type
            if salary_type not in {"fixed","per_liter","per_drum","percent_profit","commission"}: salary_type=profile.salary_type
            profile.salary_type=salary_type
            profile.salary_value=request.form.get("salary_value") or profile.salary_value
            profile.farmer_limit_override=request.form.get("farmer_limit_override") or None
            profile.can_change_farmer_quota=request.form.get("can_change_farmer_quota")=="1"
        audit("employee.updated","user",employee.id,before=before,after={"active":employee.active,"display_name":employee.display_name})
        db.session.commit()
        flash("تم تحديث بيانات الموظف وتطبيق الدور الجديد. أزيلت استثناءات الدور السابق." if role_changed else "تم تحديث بيانات الموظف.","success")
        return redirect(url_for("employees.index"))
    return render_template("employees/edit.html",employee=employee,profile=profile,roles=roles)

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
        return redirect(url_for("employees.permissions",user_id=employee.id))
    effective=set(role_keys)
    overrides={row.permission_key:row.allowed for row in employee.permission_overrides}
    for key,val in overrides.items():
        if val: effective.add(key)
        else: effective.discard(key)
    return render_template("employees/permissions.html",employee=employee,permissions=PERMISSIONS,effective=effective)



@employees_bp.post("/<int:user_id>/toggle")
@permission_required("users.manage")
def toggle(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    if employee.id==current_user.id:
        flash("لا يمكن تعطيل حساب المدير الحالي من هذه الشاشة.","danger")
        return redirect(url_for("employees.index"))
    employee.active=not employee.active
    if employee.employee_profile:
        employee.employee_profile.status="active" if employee.active else "inactive"
    audit("employee.activated" if employee.active else "employee.suspended","user",employee.id,after={"active":employee.active})
    db.session.commit()
    flash("تم تفعيل الموظف." if employee.active else "تم تعطيل الموظف.","success")
    return redirect(url_for("employees.index"))

@employees_bp.post("/<int:user_id>/delete")
@permission_required("users.manage")
def delete(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    if employee.id==current_user.id:
        flash("لا يمكن حذف الحساب المستخدم حاليًا.","danger")
        return redirect(url_for("employees.index"))
    linked=(
        FuelDispense.query.filter_by(employee_id=employee.id).count()+
        FarmerPayment.query.filter_by(employee_id=employee.id).count()+
        FuelPurchase.query.filter_by(employee_id=employee.id).count()+
        CapitalAllocation.query.filter_by(employee_id=employee.id).count()+
        EmployeeSettlement.query.filter_by(employee_id=employee.id).count()+
        OperatingExpense.query.filter_by(employee_id=employee.id).count()+
        JournalLine.query.filter_by(employee_id=employee.id).count()+
        Farmer.query.filter_by(assigned_employee_id=employee.id).count()
    )
    cashbox=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee").first()
    if linked or (cashbox and CashboxTransaction.query.filter_by(cashbox_id=cashbox.id).count()):
        flash("لا يمكن حذف الموظف نهائيًا لأن له بيانات تشغيلية أو مزارعين أو حركات صندوق. عطّل الحساب بدل الحذف، أو استخدم «تصفير النظام» لمسح بيانات المشروع ثم الحسابات.","danger")
        return redirect(url_for("employees.index"))
    AuditLog.query.filter_by(actor_user_id=employee.id).update({"actor_user_id":None},synchronize_session=False)
    if cashbox: db.session.delete(cashbox)
    deleted_id=employee.id
    db.session.delete(employee)
    audit("employee.deleted","user",deleted_id,after={"deleted":True})
    db.session.commit()
    flash("تم حذف الموظف نهائيًا.","success")
    return redirect(url_for("employees.index"))

@employees_bp.get("/<int:user_id>")
@permission_required("employee.statement.view")
def detail(user_id):
    employee=User.query.filter_by(id=user_id,is_employee=True).first_or_404()
    if not current_user.has_role("manager") and current_user.id!=employee.id:
        abort(403)
    operations=employee_operations(employee.id)
    farmers=Farmer.query.filter_by(assigned_employee_id=employee.id).filter(Farmer.status!="deleted").order_by(Farmer.name).limit(100).all()
    box=Cashbox.query.filter_by(owner_user_id=employee.id,box_type="employee",is_active=True).first()
    sales=operations["sales"]; cost=sum((getattr(row,"cost_amount",0) for row in operations["dispenses"] if row.status=="approved"),0)
    finance=employee_finance_summary(employee,operations)
    return render_template("employees/detail.html",employee=employee,operations=operations,farmers=farmers,box=box,cashbox_balance=balance(box.id) if box else 0,profit=sales-cost,finance=finance)


@employees_bp.route("/password",methods=["GET","POST"])
@permission_required("employee.statement.view")
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
