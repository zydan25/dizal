from ..extensions import db
from ..models import Notification,NotificationPreference,User

def notify_user(user_id,title,body,severity="info",link=None):
    preference=NotificationPreference.query.filter_by(user_id=user_id).first()
    if preference is None:
        preference=NotificationPreference(user_id=user_id,in_app=True,whatsapp=False)
        db.session.add(preference)
    row=Notification(user_id=user_id,title=title,body=body,severity=severity,link=link)
    if preference.in_app:
        db.session.add(row)
    return row

def notify_role(role_name,title,body,severity="info",link=None):
    users=User.query.filter(User.roles.any(name=role_name),User.active.is_(True)).all()
    rows=[]
    for user in users:
        rows.append(notify_user(user.id,title,body,severity,link))
    return rows
