from datetime import datetime,timezone
from ..extensions import db

class Notification(db.Model):
    __tablename__="notification"
    id=db.Column(db.BigInteger,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,index=True)
    title=db.Column(db.String(180),nullable=False)
    body=db.Column(db.Text,nullable=False)
    severity=db.Column(db.String(20),nullable=False,default="info")
    link=db.Column(db.String(500),nullable=True)
    read_at=db.Column(db.DateTime(timezone=True),nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    user=db.relationship("User",backref=db.backref("notifications",cascade="all, delete-orphan"))

class NotificationPreference(db.Model):
    __tablename__="notification_preference"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),nullable=False,unique=True)
    in_app=db.Column(db.Boolean,nullable=False,default=True)
    whatsapp=db.Column(db.Boolean,nullable=False,default=False)
    user=db.relationship("User",backref=db.backref("notification_preference",uselist=False))
