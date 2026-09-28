from datetime import datetime,timezone
from ..extensions import db

class EmployeeSettlement(db.Model):
    __tablename__="employee_settlement"
    id=db.Column(db.Integer,primary_key=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False,unique=True)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    period_start=db.Column(db.Date,nullable=False)
    period_end=db.Column(db.Date,nullable=False)
    expected_cash=db.Column(db.Numeric(18,3),nullable=False,default=0)
    actual_cash=db.Column(db.Numeric(18,3),nullable=False,default=0)
    cash_shortage=db.Column(db.Numeric(18,3),nullable=False,default=0)
    cash_overage=db.Column(db.Numeric(18,3),nullable=False,default=0)
    sales_amount=db.Column(db.Numeric(18,3),nullable=False,default=0)
    cost_of_sales=db.Column(db.Numeric(18,3),nullable=False,default=0)
    gross_profit=db.Column(db.Numeric(18,3),nullable=False,default=0)
    operating_expenses=db.Column(db.Numeric(18,3),nullable=False,default=0)
    employee_salary=db.Column(db.Numeric(18,3),nullable=False,default=0)
    owner_transfer=db.Column(db.Numeric(18,3),nullable=False,default=0)
    retained_operating_capital=db.Column(db.Numeric(18,3),nullable=False,default=0)
    status=db.Column(db.String(25),nullable=False,default="draft")
    notes=db.Column(db.Text,nullable=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document")
    employee=db.relationship("User",foreign_keys=[employee_id])
    created_by=db.relationship("User",foreign_keys=[created_by_id])
