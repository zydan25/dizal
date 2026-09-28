from datetime import datetime,timezone
from flask import redirect,url_for,render_template
from flask_login import current_user
from ...decorators import permission_required
from ...extensions import db
from ...models import Notification
from . import notifications_bp

@notifications_bp.get("/")
@permission_required("notifications.view")
def index():
    rows=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template("notifications/index.html",notifications=rows)

@notifications_bp.post("/read-all")
@permission_required("notifications.view")
def read_all():
    Notification.query.filter_by(user_id=current_user.id,read_at=None).update({"read_at":datetime.now(timezone.utc)},synchronize_session=False)
    db.session.commit()
    return redirect(url_for("notifications.index"))

@notifications_bp.post("/<int:notification_id>/read")
@permission_required("notifications.view")
def read(notification_id):
    row=Notification.query.filter_by(id=notification_id,user_id=current_user.id).first_or_404()
    row.read_at=datetime.now(timezone.utc)
    db.session.commit()
    return redirect(row.link or url_for("notifications.index"))