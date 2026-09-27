from datetime import datetime,timezone
from ..extensions import db

class WhatsAppConfig(db.Model):
    __tablename__="whatsapp_config"
    id=db.Column(db.Integer,primary_key=True)
    provider=db.Column(db.String(40),nullable=False,default="http")
    enabled=db.Column(db.Boolean,nullable=False,default=False)
    base_url=db.Column(db.String(500),nullable=True)
    api_token=db.Column(db.String(1000),nullable=True)
    sender_number=db.Column(db.String(50),nullable=True)
    webhook_secret=db.Column(db.String(200),nullable=True)
    timeout_seconds=db.Column(db.Integer,nullable=False,default=15)
    retry_limit=db.Column(db.Integer,nullable=False,default=3)
    updated_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))

class WhatsAppTemplate(db.Model):
    __tablename__="whatsapp_template"
    id=db.Column(db.Integer,primary_key=True)
    key=db.Column(db.String(80),unique=True,nullable=False)
    title=db.Column(db.String(160),nullable=False)
    body=db.Column(db.Text,nullable=False)
    enabled=db.Column(db.Boolean,nullable=False,default=True)

class WhatsAppMessage(db.Model):
    __tablename__="whatsapp_message"
    id=db.Column(db.BigInteger,primary_key=True)
    recipient=db.Column(db.String(40),nullable=False,index=True)
    template_key=db.Column(db.String(80),nullable=True)
    body=db.Column(db.Text,nullable=False)
    message_type=db.Column(db.String(20),nullable=False,default="text")
    attachment_storage_key=db.Column(db.String(500),nullable=True)
    status=db.Column(db.String(25),nullable=False,default="queued",index=True)
    provider_message_id=db.Column(db.String(160),nullable=True)
    retry_count=db.Column(db.Integer,nullable=False,default=0)
    error=db.Column(db.Text,nullable=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    sent_at=db.Column(db.DateTime(timezone=True),nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    created_by=db.relationship("User")
