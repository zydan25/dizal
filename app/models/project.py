from datetime import datetime,timezone
from ..extensions import db

class ProjectSettings(db.Model):
    __tablename__="project_settings"
    id=db.Column(db.Integer,primary_key=True)
    singleton_key=db.Column(db.String(20),unique=True,nullable=False,default="default")
    project_name=db.Column(db.String(150),nullable=False,default="مشروع توزيع الديزل")
    manager_name=db.Column(db.String(150),nullable=True)
    manager_phone=db.Column(db.String(40),nullable=True)
    currency=db.Column(db.String(20),nullable=False,default="ريال")
    drum_liters=db.Column(db.Numeric(12,3),nullable=False,default=20)
    max_farmers_per_employee=db.Column(db.Integer,nullable=False,default=50)
    max_credit_drums_per_farmer=db.Column(db.Numeric(12,3),nullable=False,default=7)
    max_dispense_liters_per_day=db.Column(db.Numeric(18,3),nullable=False,default=4000)
    default_sale_price_per_liter=db.Column(db.Numeric(18,3),nullable=False,default=650)
    allow_employee_sale_price_override=db.Column(db.Boolean,nullable=False,default=False)
    minimum_stock_liters=db.Column(db.Numeric(18,3),nullable=False,default=0)
    primary_color=db.Column(db.String(20),nullable=False,default="#1877F2")
    secondary_color=db.Column(db.String(20),nullable=False,default="#6c5ce7")
    accent_color=db.Column(db.String(20),nullable=False,default="#10b981")
    surface_color=db.Column(db.String(20),nullable=False,default="#f6f8fc")
    danger_color=db.Column(db.String(20),nullable=False,default="#dc3545")
    radius=db.Column(db.String(20),nullable=False,default="16px")
    font_family=db.Column(db.String(80),nullable=False,default="Tajawal")
    font_scale=db.Column(db.String(10),nullable=False,default="1")
    logo_path=db.Column(db.String(500),nullable=True)
    manager_signature_path=db.Column(db.String(500),nullable=True)
    document_header=db.Column(db.Text,nullable=True)
    document_footer=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    updated_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))

    @classmethod
    def get(cls):
        row=cls.query.filter_by(singleton_key="default").first()
        if row is None:
            row=cls(singleton_key="default")
            db.session.add(row)
            db.session.flush()
        return row
