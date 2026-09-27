from flask import render_template,request
from ...decorators import permission_required
from ...services.reports import employee_performance,farmer_debts,inventory_commitment,project_summary
from . import reports_bp

@reports_bp.get("/")
@permission_required("reports.view")
def index():
    return render_template("reports/index.html",summary=project_summary(),inventory=inventory_commitment())

@reports_bp.get("/farmers-debts")
@permission_required("reports.view")
def farmers_debts():
    return render_template("reports/farmer_debts.html",rows=farmer_debts())

@reports_bp.get("/employees")
@permission_required("reports.view")
def employees():
    return render_template("reports/employees.html",rows=employee_performance())
