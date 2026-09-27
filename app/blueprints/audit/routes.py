from flask import render_template
from ...decorators import permission_required
from ...models import AuditLog
from . import audit_bp

@audit_bp.get("/")
@permission_required("audit.view")
def index():
    rows=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("audit/index.html",rows=rows)
