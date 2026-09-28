from datetime import datetime,timezone
from ..extensions import db

class FuelDispense(db.Model):
    __tablename__="fuel_dispense"
    id=db.Column(db.Integer,primary_key=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False,unique=True)
    farmer_id=db.Column(db.Integer,db.ForeignKey("farmer.id"),nullable=False,index=True)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    tank_id=db.Column(db.Integer,db.ForeignKey("fuel_tank.id"),nullable=False,index=True)
    liters=db.Column(db.Numeric(18,3),nullable=False)
    drums=db.Column(db.Numeric(12,3),nullable=False)
    sale_price_per_liter=db.Column(db.Numeric(18,3),nullable=False)
    total_amount=db.Column(db.Numeric(18,3),nullable=False)
    paid_amount=db.Column(db.Numeric(18,3),nullable=False,default=0)
    credit_amount=db.Column(db.Numeric(18,3),nullable=False,default=0)
    credit_drums=db.Column(db.Numeric(12,6),nullable=False,default=0)
    cost_amount=db.Column(db.Numeric(18,3),nullable=False,default=0)
    gross_profit=db.Column(db.Numeric(18,3),nullable=False,default=0)
    payment_mode=db.Column(db.String(20),nullable=False,default="credit")
    status=db.Column(db.String(25),nullable=False,default="approved")
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document")
    farmer=db.relationship("Farmer",backref="dispenses")
    employee=db.relationship("User")
    tank=db.relationship("FuelTank")

class FarmerPayment(db.Model):
    __tablename__="farmer_payment"
    id=db.Column(db.Integer,primary_key=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False,unique=True)
    farmer_id=db.Column(db.Integer,db.ForeignKey("farmer.id"),nullable=False,index=True)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    payment_method=db.Column(db.String(30),nullable=False,default="cash")
    reference=db.Column(db.String(120),nullable=True)
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document")
    farmer=db.relationship("Farmer",backref="payments")
    employee=db.relationship("User")

class FarmerPaymentAllocation(db.Model):
    __tablename__="farmer_payment_allocation"
    id=db.Column(db.Integer,primary_key=True)
    payment_id=db.Column(db.Integer,db.ForeignKey("farmer_payment.id",ondelete="CASCADE"),nullable=False,index=True)
    dispense_id=db.Column(db.Integer,db.ForeignKey("fuel_dispense.id",ondelete="CASCADE"),nullable=False,index=True)
    amount=db.Column(db.Numeric(18,3),nullable=False)
    drums=db.Column(db.Numeric(12,6),nullable=False)
    payment=db.relationship("FarmerPayment",backref=db.backref("allocations",cascade="all, delete-orphan"))
    dispense=db.relationship("FuelDispense")
