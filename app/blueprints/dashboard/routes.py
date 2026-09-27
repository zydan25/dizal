from flask import render_template
from flask_login import current_user
from ...decorators import permission_required
from ...models import AuditLog,User
from ...permissions import user_has_permission
from . import dashboard_bp

@dashboard_bp.get("/")
@permission_required("dashboard.view")
def index():
    manager=user_has_permission(current_user,"users.manage")
    employee_count=User.query.filter_by(is_employee=True).count()
    recent_audits=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    return render_template("dashboard/index.html",manager=manager,employee_count=employee_count,recent_audits=recent_audits)
