from datetime import date
from ..extensions import db

class EmployeeProfile(db.Model):
    __tablename__="employee_profile"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id",ondelete="CASCADE"),unique=True,nullable=False)
    employee_code=db.Column(db.String(40),unique=True,nullable=False)
    hire_date=db.Column(db.Date,nullable=True,default=date.today)
    salary_type=db.Column(db.String(30),nullable=False,default="fixed")
    salary_value=db.Column(db.Numeric(18,3),nullable=False,default=0)
    farmer_limit_override=db.Column(db.Integer,nullable=True)
    credit_limit_override=db.Column(db.Numeric(12,3),nullable=True)
    daily_liters_limit_override=db.Column(db.Numeric(18,3),nullable=True)
    can_change_farmer_quota=db.Column(db.Boolean,nullable=False,default=False)
    status=db.Column(db.String(25),nullable=False,default="active")
    notes=db.Column(db.Text,nullable=True)
    user=db.relationship("User",backref=db.backref("employee_profile",uselist=False))
