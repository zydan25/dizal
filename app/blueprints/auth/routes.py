from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user,login_required,login_user,logout_user
from flask_security.utils import hash_password,verify_password
from ...models import User
from ...services.audit import audit
from . import auth_bp

@auth_bp.route("/login",methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method=="POST":
        identifier=(request.form.get("identifier") or "").strip()
        password=request.form.get("password") or ""
        user=User.query.filter((User.username==identifier)|(User.phone==identifier)|(User.email==identifier)).first()
        if user and user.active and verify_password(password,user.password):
            login_user(user,remember=request.form.get("remember")=="1")
            audit("auth.login","user",user.id,after={"identifier":identifier})
            next_url=(request.args.get("next") or "").strip()
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        audit("auth.login_failed","user",user.id if user else None,after={"identifier":identifier})
        flash("بيانات الدخول غير صحيحة أو الحساب غير فعال.","danger")
    return render_template("auth/login.html")

@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        audit("auth.logout","user",current_user.id)
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/account",methods=["GET","POST"])
@login_required
def account():
    from ...models import ProjectSettings
    user=current_user
    settings=ProjectSettings.get()
    if request.method=="POST":
        username=(request.form.get("username") or user.username or "").strip()
        display_name=(request.form.get("display_name") or "").strip()
        phone=(request.form.get("phone") or "").strip() or None
        email=(request.form.get("email") or "").strip() or None
        document_manager_name=(request.form.get("document_manager_name") or "").strip() or None
        document_manager_phone=(request.form.get("document_manager_phone") or "").strip() or None
        if not username or not display_name:
            flash("اسم المستخدم والاسم الظاهر مطلوبان.","danger")
            return render_template("auth/account.html",user=user,settings=settings)
        if User.query.filter(User.username==username,User.id!=user.id).first():
            flash("اسم المستخدم مستخدم بالفعل.","danger")
            return render_template("auth/account.html",user=user,settings=settings)
        if phone and User.query.filter(User.phone==phone,User.id!=user.id).first():
            flash("رقم الهاتف مستخدم من حساب آخر.","danger")
            return render_template("auth/account.html",user=user,settings=settings)
        new_password=request.form.get("new_password") or ""
        current_password=request.form.get("current_password") or ""
        confirm_password=request.form.get("confirm_password") or ""
        if new_password:
            if not verify_password(current_password,user.password):
                flash("كلمة المرور الحالية غير صحيحة.","danger")
                return render_template("auth/account.html",user=user,settings=settings)
            if len(new_password)<6:
                flash("كلمة المرور الجديدة يجب ألا تقل عن 6 أحرف.","danger")
                return render_template("auth/account.html",user=user,settings=settings)
            if new_password!=confirm_password:
                flash("تأكيد كلمة المرور غير مطابق.","danger")
                return render_template("auth/account.html",user=user,settings=settings)
            user.password=hash_password(new_password)
        before={"username":user.username,"display_name":user.display_name,"phone":user.phone,"email":user.email}
        user.username=username
        user.display_name=display_name
        user.phone=phone
        user.email=email
        if user.has_role("manager"):
            settings.manager_name=document_manager_name or display_name
            settings.manager_phone=document_manager_phone or phone
        audit("account.updated","user",user.id,before=before,after={"username":user.username,"display_name":user.display_name,"phone":user.phone,"email":user.email,"password_changed":bool(new_password)})
        db.session.commit()
        flash("تم تحديث بيانات حسابك.","success")
        return redirect(url_for("auth.account"))
    return render_template("auth/account.html",user=user,settings=settings)
