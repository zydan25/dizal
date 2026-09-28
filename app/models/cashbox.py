from datetime import datetime,timezone
from ..extensions import db

class Cashbox(db.Model):
    __tablename__="cashbox"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(160),nullable=False)
    box_type=db.Column(db.String(30),nullable=False,default="employee",index=True)
    owner_user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True,index=True)
    is_active=db.Column(db.Boolean,nullable=False,default=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    owner_user=db.relationship("User",foreign_keys=[owner_user_id])

class CashboxTransaction(db.Model):
    __tablename__="cashbox_transaction"
    id=db.Column(db.Integer,primary_key=True)
    cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id",ondelete="CASCADE"),nullable=False,index=True)
    direction=db.Column(db.String(3),nullable=False)
    transaction_type=db.Column(db.String(50),nullable=False,index=True)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=True,index=True)
    reference_type=db.Column(db.String(60),nullable=True)
    reference_id=db.Column(db.String(80),nullable=True)
    description=db.Column(db.Text,nullable=True)
    posted_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    cashbox=db.relationship("Cashbox",backref=db.backref("transactions",cascade="all, delete-orphan"))
    posted_by=db.relationship("User",foreign_keys=[posted_by_id])
    document=db.relationship("Document",foreign_keys=[document_id])
