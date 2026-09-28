from datetime import date
from flask import flash,redirect,render_template,request,url_for
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import EmployeeSettlement,User
from ...services.audit import audit
from ...services.settlements import approve_settlement,create_settlement,settlement_preview
from . import settlements_bp

@settlements_bp.route("/",methods=["GET","POST"])
@permission_required("settlement.manage")
def index():
    if request.method=="POST":
        try:
            employee=User.query.filter_by(id=int(request.form["employee_id"]),is_employee=True,active=True).first()
            if not employee: raise ValueError("الموظف المحدد غير صالح.")
            start=date.fromisoformat(request.form["period_start"]); end=date.fromisoformat(request.form["period_end"])
            if end<start: raise ValueError("نهاية الفترة لا يمكن أن تسبق بدايتها.")
            row=create_settlement(employee,start,end,current_user.id,request.form.get("actual_cash"),request.form.get("owner_transfer") or 0,request.form.get("retained_operating_capital") or 0,request.form.get("notes"))
            audit("settlement.created","employee_settlement",row.id,after={"employee_id":employee.id,"expected_cash":str(row.expected_cash),"actual_cash":str(row.actual_cash)})
            db.session.commit()
            flash("تم إنشاء مسودة التسوية.","success")
            return redirect(url_for("settlements.index"))
        except (ValueError,TypeError) as exc:
            db.session.rollback()
            flash(str(exc),"danger")
    employees=User.query.filter_by(is_employee=True,active=True).order_by(User.display_name).all()
    settlements=EmployeeSettlement.query.order_by(EmployeeSettlement.id.desc()).limit(50).all()
    return render_template("settlements/index.html",employees=employees,settlements=settlements,today=date.today().isoformat())

@settlements_bp.post("/<int:settlement_id>/approve")
@permission_required("settlement.approve")
def approve(settlement_id):
    row=EmployeeSettlement.query.get_or_404(settlement_id)
    try:
        approve_settlement(row,current_user.id)
        audit("settlement.approved","employee_settlement",row.id,after={"status":"approved","owner_transfer":str(row.owner_transfer),"salary":str(row.employee_salary)})
        db.session.commit()
        flash("تم اعتماد التسوية وتنفيذ التحويل والراتب المحددين.","success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc),"danger")
    return redirect(url_for("settlements.index"))

@settlements_bp.get("/preview/<int:employee_id>")
@permission_required("settlement.manage")
def preview(employee_id):
    employee=User.query.filter_by(id=employee_id,is_employee=True,active=True).first_or_404()
    start=date.fromisoformat(request.args.get("start") or date.today().replace(day=1).isoformat())
    end=date.fromisoformat(request.args.get("end") or date.today().isoformat())
    return settlement_preview(employee,start,end)
