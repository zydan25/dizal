from decimal import Decimal
from sqlalchemy import func
from ..extensions import db
from ..models import EmployeeProfile,Farmer,FarmerDocument,FarmerQuotaMovement,ProjectSettings,User
from .documents import create_document

def employee_limits(employee):
    settings=ProjectSettings.get()
    profile=EmployeeProfile.query.filter_by(user_id=employee.id).first()
    return {
        "max_farmers":profile.farmer_limit_override if profile and profile.farmer_limit_override is not None else settings.max_farmers_per_employee,
        "max_credit_drums":Decimal(str(profile.credit_limit_override if profile and profile.credit_limit_override is not None else settings.max_credit_drums_per_farmer)),
        "max_daily_liters":Decimal(str(profile.daily_liters_limit_override if profile and profile.daily_liters_limit_override is not None else settings.max_dispense_liters_per_day)),
    }

def active_farmer_count(employee_id):
    return Farmer.query.filter(Farmer.assigned_employee_id==employee_id,Farmer.status.in_([ "submitted","changes_requested","approved" ])).count()

def validate_farmer_limits(employee,quota_drums,credit_limit_drums):
    limits=employee_limits(employee)
    if active_farmer_count(employee.id)>=int(limits["max_farmers"]):
        raise ValueError("وصل الموظف إلى الحد المسموح لعدد المزارعين.")
    quota=Decimal(str(quota_drums))
    credit=Decimal(str(credit_limit_drums))
    if quota<0 or credit<0:
        raise ValueError("السقوف لا يمكن أن تكون سالبة.")
    if credit>limits["max_credit_drums"]:
        raise ValueError(f"الحد الأعلى للمديونية هو {limits['max_credit_drums']} دبة.")
    if quota>limits["max_credit_drums"]:
        raise ValueError(f"الحد الأعلى للسقف هو {limits['max_credit_drums']} دبة.")

def create_farmer(name,phone,address,notes,quota_drums,credit_limit_drums,assigned_employee_id,created_by_id,attachments=None):
    if not name or not phone:
        raise ValueError("اسم المزارع ورقم الهاتف مطلوبان.")
    employee=User.query.filter_by(id=assigned_employee_id,is_employee=True,active=True).first()
    if not employee:
        raise ValueError("الموظف المحدد غير صالح.")
    validate_farmer_limits(employee,quota_drums,credit_limit_drums)
    code=f"F-{Farmer.query.count()+1:06d}"
    row=Farmer(code=code,name=name.strip(),phone=phone.strip(),address=address,notes=notes,quota_drums=quota_drums,credit_limit_drums=credit_limit_drums,assigned_employee_id=assigned_employee_id,created_by_id=created_by_id,status="submitted")
    db.session.add(row)
    db.session.flush()
    document=create_document("FAR","ملف مزارع",created_by_id,source_type="farmer",source_id=row.id,status="submitted")
    if attachments:
        for document_type,attachment in attachments:
            db.session.add(FarmerDocument(farmer_id=row.id,document_type=document_type,created_by_id=created_by_id,**attachment))
    return row

def review_farmer(farmer,action,manager_id,note=None):
    if farmer.status not in {"submitted","changes_requested"}:
        raise ValueError("المزارع ليس في حالة مراجعة.")
    if action=="approve":
        farmer.status="approved"
        farmer.approved_by_id=manager_id
        farmer.review_note=note
    elif action=="changes":
        farmer.status="changes_requested"
        farmer.review_note=note
    elif action=="reject":
        farmer.status="rejected"
        farmer.review_note=note
    else:
        raise ValueError("إجراء المراجعة غير صالح.")
    return farmer

def change_quota(farmer,new_quota,new_credit,manager_id,reason=None):
    new_quota=Decimal(str(new_quota))
    new_credit=Decimal(str(new_credit))
    if new_quota<0 or new_credit<0:
        raise ValueError("السقوف لا يمكن أن تكون سالبة.")
    limits=employee_limits(farmer.assigned_employee)
    if new_credit>limits["max_credit_drums"]:
        raise ValueError("السقف يتجاوز الحد المسموح للموظف.")
    movement=FarmerQuotaMovement(farmer_id=farmer.id,old_quota_drums=farmer.quota_drums,new_quota_drums=new_quota,old_credit_limit_drums=farmer.credit_limit_drums,new_credit_limit_drums=new_credit,reason=reason,created_by_id=manager_id)
    farmer.quota_drums=new_quota
    farmer.credit_limit_drums=new_credit
    db.session.add(movement)
    return movement
