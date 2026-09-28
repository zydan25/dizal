from functools import wraps
from flask import abort, redirect, request, url_for
from flask_login import current_user
from .permissions import user_has_permission

def permission_required(permission_key):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.full_path))
            if not user_has_permission(current_user, permission_key):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
