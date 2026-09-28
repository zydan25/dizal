from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user,login_user,logout_user
from flask_security.utils import verify_password
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
