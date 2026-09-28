from datetime import datetime, timezone
from ..extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id = db.Column(db.BigInteger, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    object_type = db.Column(db.String(80), nullable=True, index=True)
    object_id = db.Column(db.String(80), nullable=True, index=True)
    before_json = db.Column(db.JSON, nullable=True)
    after_json = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    request_id = db.Column(db.String(80), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actor = db.relationship("User", foreign_keys=[actor_user_id])
