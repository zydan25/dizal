from datetime import date,datetime,timezone
from ..extensions import db

class OperatingExpense(db.Model):
    __tablename__="operating_expense"
    id=db.Column(db.Integer,primary_key=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False,unique=True)
    cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id"),nullable=False)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True,index=True)
    expense_date=db.Column(db.Date,nullable=False,default=date.today)
    category=db.Column(db.String(80),nullable=False)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    description=db.Column(db.Text,nullable=True)
    status=db.Column(db.String(25),nullable=False,default="approved")
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document")
    cashbox=db.relationship("Cashbox")
    employee=db.relationship("User",foreign_keys=[employee_id])
    created_by=db.relationship("User",foreign_keys=[created_by_id])
