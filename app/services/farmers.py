from decimal import Decimal,InvalidOperation
from sqlalchemy import func
from ..extensions import db
from ..models import Document,EmployeeProfile,Farmer,FarmerDocument,FarmerQuotaMovement,FuelDispense,ProjectSettings,User
from .documents import create_document

PROJECT_COMMITMENT_STATUSES=("submitted","changes_requested","approved","suspended")
ZERO=Decimal("0")


def _decimal(value,label="الكمية"):
    try:
        return Decimal(str(value if value not in (None,"") else 0))
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError(f"قيمة {label} غير صحيحة.")


def project_diesel_capacity(exclude_farmer_id=None,lock=False):
    """Return the remaining allocation after farmer commitments and general sales.

    A farmer's full agreed quota reserves diesel even before it is drawn. General
    sales consume only the surplus left after those reservations.
    """
    settings_query=ProjectSettings.query.filter_by(singleton_key="default")
    if lock:
        settings_query=settings_query.with_for_update()
    settings=settings_query.first() or ProjectSettings.get()
    drum_liters=_decimal(settings.drum_liters,"لترات الدبة")
    limit_liters=_decimal(getattr(settings,"project_diesel_limit_liters",6000),"حد ديزل المشروع")
    quota_query=db.session.query(func.coalesce(func.sum(Farmer.quota_drums),0)).filter(
        Farmer.status.in_(PROJECT_COMMITMENT_STATUSES)
    )
    if exclude_farmer_id is not None:
        quota_query=quota_query.filter(Farmer.id!=exclude_farmer_id)
    quota_drums=_decimal(quota_query.scalar(),"كميات المزارعين")
    farmer_quota_liters=quota_drums*drum_liters
    general_sale_query=(
        db.session.query(func.coalesce(func.sum(FuelDispense.liters),0))
        .join(Document,FuelDispense.document_id==Document.id)
        .filter(
            FuelDispense.sale_type=="general",
            FuelDispense.status=="approved",
            Document.status!="reversed",
        )
    )
    general_sale_liters=_decimal(general_sale_query.scalar(),"مبيعات البيع العام")
    used_liters=farmer_quota_liters+general_sale_liters
    raw_remaining=limit_liters-used_liters
    remaining=max(raw_remaining,ZERO)
    return {
        "limit_liters":limit_liters,
        "drum_liters":drum_liters,
        "farmer_quota_drums":quota_drums,
        "farmer_quota_liters":farmer_quota_liters,
        "general_sale_liters":general_sale_liters,
        "used_liters":used_liters,
        "remaining_liters":remaining,
        "remaining_liters_raw":raw_remaining,
        "remaining_drums":remaining/drum_liters if drum_liters>0 else ZERO,
        "over_limit_liters":max(-raw_remaining,ZERO),
    }


def _ensure_project_quota_available(quota_drums,exclude_farmer_id=None,current_quota=None,lock=False):
    quota=_decimal(quota_drums,"كمية المزارع")
    if quota<0:
        raise ValueError("كمية المزارع لا يمكن أن تكون سالبة.")
    capacity=project_diesel_capacity(exclude_farmer_id=exclude_farmer_id,lock=lock)
    # Existing allocations may be reduced even if an older setup is already over
    # the cap. A new allocation or an increase must fit fully inside the cap.
    is_reduction=current_quota is not None and quota<=_decimal(current_quota,"الكمية الحالية")
    requested_liters=quota*capacity["drum_liters"]
    if not is_reduction and requested_liters>capacity["remaining_liters_raw"]:
        available=max(capacity["remaining_liters_raw"],ZERO)
        if capacity["remaining_liters_raw"]<0:
            raise ValueError(
                f"تم تجاوز حد ديزل المشروع بمقدار {abs(capacity['remaining_liters_raw'])} لتر. "
                "خفّض كميات المزارعين أو ارفع حد المشروع قبل إضافة كمية جديدة."
            )
        raise ValueError(
            f"كمية المزارع المطلوبة تعادل {requested_liters} لتر، بينما الفائض المتاح "
            f"للمشروع {available} لتر فقط (حوالي {capacity['remaining_drums']} دبة)."
        )
    return capacity


def validate_project_diesel_sale(liters):
    requested=_decimal(liters,"كمية البيع")
    if requested<=0:
        raise ValueError("كمية البيع يجب أن تكون أكبر من صفر.")
    capacity=project_diesel_capacity(lock=True)
    if requested>capacity["remaining_liters_raw"]:
        available=max(capacity["remaining_liters_raw"],ZERO)
        raise ValueError(
            f"لا يمكن تنفيذ البيع العام. فائض المشروع المتاح {available} لتر فقط، "
            f"وكمية البيع المطلوبة {requested} لتر. حد المشروع {capacity['limit_liters']} لتر، "
            f"وحجوزات المزارعين {capacity['farmer_quota_liters']} لتر، ومبيعات البيع العام السابقة "
            f"{capacity['general_sale_liters']} لتر."
        )
    return capacity

def employee_limits(employee):
    settings=ProjectSettings.get()
    profile=EmployeeProfile.query.filter_by(user_id=employee.id).first()
    return {
        "max_farmers":profile.farmer_limit_override if profile and profile.farmer_limit_override is not None else settings.max_farmers_per_employee,
    }


def active_farmer_count(employee_id):
    return Farmer.query.filter(
        Farmer.assigned_employee_id==employee_id,
        Farmer.status.in_(PROJECT_COMMITMENT_STATUSES),
    ).count()


def validate_farmer_limits(employee,quota_drums,credit_limit_drums=None):
    limits=employee_limits(employee)
    if active_farmer_count(employee.id)>=int(limits["max_farmers"]):
        raise ValueError("وصل الموظف إلى الحد المسموح لعدد المزارعين.")
    quota=_decimal(quota_drums,"كمية المزارع")
    if quota<=0:
        raise ValueError("الكمية المتفق عليها يجب أن تكون أكبر من صفر دبة.")
    _ensure_project_quota_available(quota,lock=True)

def create_farmer(name,phone,address,notes,quota_drums,credit_limit_drums,assigned_employee_id,created_by_id,attachments=None):
    if not name or not phone:
        raise ValueError("اسم المزارع ورقم الهاتف مطلوبان.")
    employee=User.query.filter_by(id=assigned_employee_id,is_employee=True,active=True).first()
    if not employee:
        raise ValueError("الموظف المحدد غير صالح.")
    quota=_decimal(quota_drums,"كمية المزارع")
    validate_farmer_limits(employee,quota,credit_limit_drums)
    code=f"F-{Farmer.query.count()+1:06d}"
    # Keep the legacy database column in sync for old reports, but there is now
    # only one business value: the agreed quota in drums.
    row=Farmer(code=code,name=name.strip(),phone=phone.strip(),address=address,notes=notes,quota_drums=quota,credit_limit_drums=quota,assigned_employee_id=assigned_employee_id,created_by_id=created_by_id,status="submitted")
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
    # new_credit remains in the signature for compatibility with historical callers.
    new_quota=_decimal(new_quota,"كمية المزارع")
    if new_quota<0:
        raise ValueError("كمية المزارع لا يمكن أن تكون سالبة.")
    _ensure_project_quota_available(
        new_quota,
        exclude_farmer_id=farmer.id,
        current_quota=farmer.quota_drums,
        lock=True,
    )
    movement=FarmerQuotaMovement(
        farmer_id=farmer.id,
        old_quota_drums=farmer.quota_drums,
        new_quota_drums=new_quota,
        old_credit_limit_drums=farmer.credit_limit_drums,
        new_credit_limit_drums=new_quota,
        reason=reason,
        created_by_id=manager_id,
    )
    farmer.quota_drums=new_quota
    farmer.credit_limit_drums=new_quota
    db.session.add(movement)
    return movement
