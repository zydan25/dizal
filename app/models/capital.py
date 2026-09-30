from datetime import date,datetime,timezone
from ..extensions import db

class CapitalContribution(db.Model):
    __tablename__="capital_contribution"
    id=db.Column(db.Integer,primary_key=True)
    contribution_date=db.Column(db.Date,nullable=False,default=date.today)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    contribution_type=db.Column(db.String(20),nullable=False,default="cash")
    asset_id=db.Column(db.Integer,db.ForeignKey("asset.id"),nullable=True,unique=True)
    source=db.Column(db.String(180),nullable=True)
    cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id"),nullable=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=True)
    status=db.Column(db.String(25),nullable=False,default="approved")
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    cashbox=db.relationship("Cashbox")
    asset=db.relationship("Asset",foreign_keys=[asset_id])
    document=db.relationship("Document")
    created_by=db.relationship("User",foreign_keys=[created_by_id])

class CapitalAllocation(db.Model):
    __tablename__="capital_allocation"
    id=db.Column(db.Integer,primary_key=True)
    allocation_date=db.Column(db.Date,nullable=False,default=date.today)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    source_cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id"),nullable=False)
    destination_cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id"),nullable=False)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    employee=db.relationship("User",foreign_keys=[employee_id])
    source_cashbox=db.relationship("Cashbox",foreign_keys=[source_cashbox_id])
    destination_cashbox=db.relationship("Cashbox",foreign_keys=[destination_cashbox_id])
    document=db.relationship("Document")
    created_by=db.relationship("User",foreign_keys=[created_by_id])
