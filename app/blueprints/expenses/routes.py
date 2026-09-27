from datetime import date
from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Cashbox,User,OperatingExpense
from ...services.audit import audit
from ...services.expenses import create_expense
from . import expenses_bp

@expenses_bp.route("/",methods=["GET","POST"])
@permission_required("expenses.manage")
def index():
    if request.method=="POST":
        try:
            employee_id=int(request.form["employee_id"]) if request.form.get("employee_id") else None
            cashbox=Cashbox.query.get_or_404(int(request.form["cashbox_id"]))
            expense=create_expense(cashbox.id,employee_id,request.form.get("category","").strip(),request.form.get("amount"),date.fromisoformat(request.form.get("expense_date") or date.today().isoformat()),current_user.id,request.form.get("description"))
            audit("expense.created","operating_expense",expense.id,after={"amount":str(expense.amount),"category":expense.category,"cashbox_id":cashbox.id})
            db.session.commit()
            flash("تم تسجيل المصروف وإصداره كسند.","success")
            return redirect(url_for("expenses.index"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all()
    cashboxes=Cashbox.query.filter_by(is_active=True).all()
    expenses=OperatingExpense.query.order_by(OperatingExpense.id.desc()).limit(100).all()
    return render_template("expenses/index.html",employees=employees,cashboxes=cashboxes,expenses=expenses,today=date.today().isoformat())
