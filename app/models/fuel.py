from datetime import datetime,date,timezone
from ..extensions import db

class FuelTank(db.Model):
    __tablename__="fuel_tank"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(160),nullable=False)
    code=db.Column(db.String(50),unique=True,nullable=False,index=True)
    capacity_liters=db.Column(db.Numeric(18,3),nullable=True)
    location=db.Column(db.String(180),nullable=True)
    custodian_user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    is_active=db.Column(db.Boolean,nullable=False,default=True)
    notes=db.Column(db.Text,nullable=True)
    custodian=db.relationship("User")

class FuelPurchase(db.Model):
    __tablename__="fuel_purchase"
    id=db.Column(db.Integer,primary_key=True)
    employee_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False,index=True)
    tank_id=db.Column(db.Integer,db.ForeignKey("fuel_tank.id"),nullable=False,index=True)
    purchase_date=db.Column(db.Date,nullable=False,default=date.today)
    supplier_name=db.Column(db.String(180),nullable=True)
    liters=db.Column(db.Numeric(18,3),nullable=False)
    diesel_amount=db.Column(db.Numeric(18,3),nullable=False)
    delivery_fee=db.Column(db.Numeric(18,3),nullable=False,default=0)
    other_fee=db.Column(db.Numeric(18,3),nullable=False,default=0)
    landed_cost=db.Column(db.Numeric(18,3),nullable=False)
    unit_cost=db.Column(db.Numeric(18,6),nullable=False)
    status=db.Column(db.String(30),nullable=False,default="submitted",index=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False)
    submitted_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    approved_at=db.Column(db.DateTime(timezone=True),nullable=True)
    approved_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    notes=db.Column(db.Text,nullable=True)
    employee=db.relationship("User",foreign_keys=[employee_id])
    tank=db.relationship("FuelTank")
    document=db.relationship("Document")
    approved_by=db.relationship("User",foreign_keys=[approved_by_id])

class FuelStockMovement(db.Model):
    __tablename__="fuel_stock_movement"
    id=db.Column(db.Integer,primary_key=True)
    tank_id=db.Column(db.Integer,db.ForeignKey("fuel_tank.id",ondelete="CASCADE"),nullable=False,index=True)
    direction=db.Column(db.String(3),nullable=False)
    movement_type=db.Column(db.String(50),nullable=False,index=True)
    liters=db.Column(db.Numeric(18,3),nullable=False)
    unit_cost=db.Column(db.Numeric(18,6),nullable=True)
    source_type=db.Column(db.String(60),nullable=True)
    source_id=db.Column(db.String(80),nullable=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    tank=db.relationship("FuelTank",backref=db.backref("stock_movements",cascade="all, delete-orphan"))
    document=db.relationship("Document")
    created_by=db.relationship("User")

class FuelStockLayer(db.Model):
    __tablename__="fuel_stock_layer"
    id=db.Column(db.Integer,primary_key=True)
    tank_id=db.Column(db.Integer,db.ForeignKey("fuel_tank.id",ondelete="CASCADE"),nullable=False,index=True)
    purchase_id=db.Column(db.Integer,db.ForeignKey("fuel_purchase.id",ondelete="CASCADE"),nullable=False,index=True)
    original_liters=db.Column(db.Numeric(18,3),nullable=False)
    remaining_liters=db.Column(db.Numeric(18,3),nullable=False)
    unit_cost=db.Column(db.Numeric(18,6),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    tank=db.relationship("FuelTank")
    purchase=db.relationship("FuelPurchase")

class FuelStockConsumption(db.Model):
    __tablename__="fuel_stock_consumption"
    id=db.Column(db.Integer,primary_key=True)
    dispense_id=db.Column(db.Integer,db.ForeignKey("fuel_dispense.id",ondelete="CASCADE"),nullable=False,index=True)
    layer_id=db.Column(db.Integer,db.ForeignKey("fuel_stock_layer.id",ondelete="RESTRICT"),nullable=False,index=True)
    liters=db.Column(db.Numeric(18,3),nullable=False)
    unit_cost=db.Column(db.Numeric(18,6),nullable=False)
    cost_amount=db.Column(db.Numeric(18,3),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    layer=db.relationship("FuelStockLayer")
    dispense=db.relationship("FuelDispense")
