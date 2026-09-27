from datetime import datetime,timezone
from ..extensions import db

class Account(db.Model):
    __tablename__="account"
    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(30),unique=True,nullable=False,index=True)
    name=db.Column(db.String(160),nullable=False)
    account_type=db.Column(db.String(30),nullable=False,index=True)
    parent_id=db.Column(db.Integer,db.ForeignKey("account.id"),nullable=True)
    is_system=db.Column(db.Boolean,nullable=False,default=True)
    active=db.Column(db.Boolean,nullable=False,default=True)
    parent=db.relationship("Account",remote_side=[id],backref="children")

class JournalEntry(db.Model):
    __tablename__="journal_entry"
    id=db.Column(db.BigInteger,primary_key=True)
    entry_date=db.Column(db.Date,nullable=False,index=True)
    source_type=db.Column(db.String(60),nullable=False,index=True)
    source_id=db.Column(db.String(80),nullable=False,index=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=True,index=True)
    description=db.Column(db.Text,nullable=False)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document")
    created_by=db.relationship("User")
    
class JournalLine(db.Model):
    __tablename__="journal_line"
    id=db.Column(db.BigInteger,primary_key=True)
    journal_entry_id=db.Column(db.BigInteger,db.ForeignKey("journal_entry.id",ondelete="CASCADE"),nullable=False,index=True)
    account_id=db.Column(db.Integer,db.ForeignKey("account.id"),nullable=False,index=True)
    debit=db.Column(db.Numeric(18,3),nullable=False,default=0)
    credit=db.Column(db.Numeric(18,3),nullable=False,default=0)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True,index=True)
    farmer_id=db.Column(db.Integer,db.ForeignKey("farmer.id"),nullable=True,index=True)
    description=db.Column(db.Text,nullable=True)
    journal_entry=db.relationship("JournalEntry",backref=db.backref("lines",cascade="all, delete-orphan"))
    account=db.relationship("Account")
    employee=db.relationship("User",foreign_keys=[employee_id])
    farmer=db.relationship("Farmer",foreign_keys=[farmer_id])
