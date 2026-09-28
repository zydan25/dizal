from datetime import datetime,timezone
from ..extensions import db

class Farmer(db.Model):
    __tablename__="farmer"
    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(50),unique=True,nullable=False,index=True)
    name=db.Column(db.String(180),nullable=False,index=True)
    phone=db.Column(db.String(40),nullable=False,index=True)
    address=db.Column(db.String(250),nullable=True)
    notes=db.Column(db.Text,nullable=True)
    quota_drums=db.Column(db.Numeric(12,3),nullable=False,default=0)
    credit_limit_drums=db.Column(db.Numeric(12,3),nullable=False,default=0)
    assigned_employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    status=db.Column(db.String(30),nullable=False,default="submitted",index=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    approved_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    review_note=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    updated_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))
    assigned_employee=db.relationship("User",foreign_keys=[assigned_employee_id])
    created_by=db.relationship("User",foreign_keys=[created_by_id])
    approved_by=db.relationship("User",foreign_keys=[approved_by_id])

class FarmerDocument(db.Model):
    __tablename__="farmer_document"
    id=db.Column(db.Integer,primary_key=True)
    farmer_id=db.Column(db.Integer,db.ForeignKey("farmer.id",ondelete="CASCADE"),nullable=False,index=True)
    document_type=db.Column(db.String(40),nullable=False,index=True)
    original_name=db.Column(db.String(250),nullable=False)
    storage_key=db.Column(db.String(500),nullable=False)
    mime_type=db.Column(db.String(120),nullable=True)
    size_bytes=db.Column(db.BigInteger,nullable=True)
    sha256=db.Column(db.String(64),nullable=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    farmer=db.relationship("Farmer",backref=db.backref("documents",cascade="all, delete-orphan"))
    created_by=db.relationship("User")

class FarmerQuotaMovement(db.Model):
    __tablename__="farmer_quota_movement"
    id=db.Column(db.Integer,primary_key=True)
    farmer_id=db.Column(db.Integer,db.ForeignKey("farmer.id",ondelete="CASCADE"),nullable=False,index=True)
    old_quota_drums=db.Column(db.Numeric(12,3),nullable=False)
    new_quota_drums=db.Column(db.Numeric(12,3),nullable=False)
    old_credit_limit_drums=db.Column(db.Numeric(12,3),nullable=False)
    new_credit_limit_drums=db.Column(db.Numeric(12,3),nullable=False)
    reason=db.Column(db.Text,nullable=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    farmer=db.relationship("Farmer")
    created_by=db.relationship("User")
