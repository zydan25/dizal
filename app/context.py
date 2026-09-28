from flask_login import current_user
from flask import url_for
from .models import ProjectSettings,Notification
from .navigation import build_navigation

AUDIT_ACTION_LABELS={
    "auth.login":"تسجيل دخول","auth.login_failed":"محاولة دخول فاشلة","settings.updated":"تحديث الإعدادات",
    "farmer.created":"إضافة مزارع","farmer.updated":"تعديل مزارع","farmer.document.deleted":"حذف مرفق مزارع","farmer.quota.changed":"تعديل سقف المزارع",
    "farmer.approve":"اعتماد مزارع","farmer.changes":"طلب استكمال المزارع","farmer.reject":"رفض مزارع","farmer.suspend":"إيقاف مزارع","farmer.activate":"تفعيل مزارع","farmer.delete":"أرشفة مزارع",
    "fuel.purchase.created":"إضافة توريد ديزل","fuel.purchase.reviewed":"مراجعة توريد ديزل","fuel.dispense.created":"صرف ديزل","farmer.payment.created":"تحصيل من مزارع",
    "capital.added":"إضافة رأس مال","capital.allocated":"تسليم رأس مال لموظف","asset.created":"إضافة أصل","asset.updated":"تعديل أصل",
    "document.reversed":"عكس سند","employee.created":"إضافة موظف","employee.updated":"تعديل موظف","employee.password.reset":"تغيير كلمة مرور موظف",
}

AUDIT_OBJECT_LABELS={"farmer":"المزارع","fuel_dispense":"صرف ديزل","farmer_payment":"سند قبض","fuel_purchase":"توريد ديزل","fuel_tank":"خزان","asset":"أصل","capital_contribution":"رأس مال","capital_allocation":"تسليم رأس مال","employee":"موظف","user":"مستخدم","document":"سند","project_settings":"إعدادات المشروع","system":"النظام"}

def audit_object_label(value):
    return AUDIT_OBJECT_LABELS.get(value, value.replace("_"," ") if value else "النظام")

AUDIT_VERB_LABELS={"created":"إضافة","added":"إضافة","updated":"تعديل","changed":"تغيير","reviewed":"مراجعة","deleted":"حذف","reversed":"عكس","approved":"اعتماد","rejected":"رفض","suspended":"إيقاف","activated":"تفعيل","failed":"فشل","read":"قراءة","sent":"إرسال","uploaded":"رفع"}

def audit_action_label(action):
    if not action: return "نشاط"
    if action in AUDIT_ACTION_LABELS: return AUDIT_ACTION_LABELS[action]
    parts=[]
    for token in action.replace("_",".").split("."):
        parts.append(AUDIT_VERB_LABELS.get(token, {"auth":"حساب","farmer":"مزارع","fuel":"ديزل","purchase":"توريد","dispense":"صرف","payment":"سداد","capital":"رأس مال","employee":"موظف","asset":"أصل","document":"سند","settings":"إعدادات"}.get(token,token)))
    return " · ".join(parts)

def audit_target_url(row):
    try:
        object_id=int(row.object_id) if row.object_id else None
    except (TypeError,ValueError):
        object_id=None
    if not object_id: return None
    after=row.after_json or {}
    try:
        if row.object_type=="farmer": return url_for("farmers.detail",farmer_id=object_id)
        if row.object_type=="fuel_tank": return url_for("fuel.tank_detail",tank_id=object_id)
        if row.object_type=="asset": return url_for("assets.detail",asset_id=object_id)
        if row.object_type in {"document","capital_contribution","capital_allocation","fuel_dispense","farmer_payment"} and after.get("document_id"):
            return url_for("documents.view",document_id=int(after["document_id"]))
        if row.object_type in {"employee","user"}: return url_for("employees.detail",user_id=object_id)
        if row.object_type=="project_settings": return url_for("settings.index")
        if row.object_type=="role": return url_for("roles.index")
        if row.object_type=="whatsapp": return url_for("whatsapp.index")
        if row.object_type in {"cashbox","cashbox_transaction"}: return url_for("cashbox.index")
        if row.object_type in {"operating_expense","expense"}: return url_for("expenses.index")
        if row.object_type in {"settlement","employee_settlement"}: return url_for("settlements.index")
    except Exception:
        return None
    return None

def register_context(app):
    @app.context_processor
    def inject():
        settings=ProjectSettings.get()
        unread=0
        navigation=[]
        if current_user.is_authenticated:
            unread=Notification.query.filter_by(user_id=current_user.id,read_at=None).count()
            navigation=build_navigation(current_user)
        return {"project_settings":settings,"navigation":navigation,"unread_notifications":unread,"audit_action_label":audit_action_label,"audit_object_label":audit_object_label,"audit_target_url":audit_target_url}
