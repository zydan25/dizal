from datetime import date,datetime,timezone
from ..extensions import db

class Asset(db.Model):
    __tablename__="asset"
    id=db.Column(db.Integer,primary_key=True)
    asset_code=db.Column(db.String(50),unique=True,nullable=False,index=True)
    name=db.Column(db.String(180),nullable=False)
    category=db.Column(db.String(80),nullable=False)
    acquisition_cost=db.Column(db.Numeric(18,3),nullable=False)
    acquisition_date=db.Column(db.Date,nullable=False,default=date.today)
    payer_cashbox_id=db.Column(db.Integer,db.ForeignKey("cashbox.id"),nullable=False)
    custodian_user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    location=db.Column(db.String(180),nullable=True)
    status=db.Column(db.String(25),nullable=False,default="active")
    document_id=db.Column(db.Integer,db.ForeignKey("document.id"),nullable=False)
    tank_id=db.Column(db.Integer,db.ForeignKey("fuel_tank.id"),nullable=True,index=True)
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    payer_cashbox=db.relationship("Cashbox")
    custodian=db.relationship("User")
    document=db.relationship("Document")
    tank=db.relationship("FuelTank")
