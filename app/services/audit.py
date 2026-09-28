import uuid
from flask import has_request_context, request
from flask_login import current_user
from ..extensions import db
from ..models import AuditLog

def audit(action,object_type=None,object_id=None,before=None,after=None):
    ip=request.headers.get("X-Forwarded-For",request.remote_addr) if has_request_context() else None
    user_agent=request.headers.get("User-Agent") if has_request_context() else None
    request_id=request.headers.get("X-Request-ID") if has_request_context() else str(uuid.uuid4())
    actor_id=current_user.id if has_request_context() and current_user.is_authenticated else None
    row=AuditLog(actor_user_id=actor_id,action=action,object_type=object_type,object_id=str(object_id) if object_id is not None else None,before_json=before,after_json=after,ip_address=ip,user_agent=user_agent,request_id=request_id)
    db.session.add(row)
    return row
