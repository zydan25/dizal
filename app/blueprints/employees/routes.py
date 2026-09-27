from flask import flash,redirect,render_template,request,url_for
from flask_security.utils import hash_password
from ...decorators import permission_required
from ...extensions import db
from ...models import EmployeeProfile,Role,User
from ...services.audit import audit
from ...models import Cashbox
from . import employees_bp

@employees_bp.get("/")
@permission_required("users.view")
def index():
    employees=User.query.filter_by(is_employee=True).order_by(User.id.desc()).all()
    return render_template("employees/index.html",employees=employees)

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
        if User.query.filter((User.username==username)|(User.phone==phone)).first():
            flash("اسم المستخدم أو الهاتف مستخدم بالفعل.","danger")
            return render_template("employees/form.html")
        user=User(username=username,phone=phone or None,email=(request.form.get("email") or None),display_name=name,is_employee=True,active=True,password=hash_password(password),fs_uniquifier=__import__("uuid").uuid4().hex)
        role=Role.query.filter_by(name="employee").first()
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
