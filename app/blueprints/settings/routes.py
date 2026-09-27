from flask import current_app,flash,redirect,render_template,request,url_for
from ...decorators import permission_required
from ...extensions import db
from ...models import ProjectSettings
from ...services.audit import audit
from ...services.files import save_image
from . import settings_bp

@settings_bp.get("/")
@permission_required("settings.view")
def index():
    return render_template("settings/index.html",settings=ProjectSettings.get())

@settings_bp.post("/")
@permission_required("settings.manage")
def update():
    settings=ProjectSettings.get()
    before={"project_name":settings.project_name,"currency":settings.currency,"drum_liters":str(settings.drum_liters),"max_farmers_per_employee":settings.max_farmers_per_employee,"max_credit_drums_per_farmer":str(settings.max_credit_drums_per_farmer),"max_dispense_liters_per_day":str(settings.max_dispense_liters_per_day),"default_sale_price_per_liter":str(settings.default_sale_price_per_liter)}
    settings.project_name=(request.form.get("project_name") or settings.project_name).strip()
    settings.currency=(request.form.get("currency") or settings.currency).strip()
    settings.drum_liters=request.form.get("drum_liters") or settings.drum_liters
    settings.max_farmers_per_employee=int(request.form.get("max_farmers_per_employee") or settings.max_farmers_per_employee)
    settings.max_credit_drums_per_farmer=request.form.get("max_credit_drums_per_farmer") or settings.max_credit_drums_per_farmer
    settings.max_dispense_liters_per_day=request.form.get("max_dispense_liters_per_day") or settings.max_dispense_liters_per_day
    settings.default_sale_price_per_liter=request.form.get("default_sale_price_per_liter") or settings.default_sale_price_per_liter
    for field in ("primary_color","secondary_color","accent_color","surface_color","danger_color"):
        value=(request.form.get(field) or getattr(settings,field)).strip()
        if not value.startswith("#") or len(value) not in (4,7):
            flash("صيغة اللون غير صالحة.","danger")
            return redirect(url_for("settings.index"))
        setattr(settings,field,value)
    settings.font_family=(request.form.get("font_family") or settings.font_family).strip()
    settings.radius=(request.form.get("radius") or settings.radius).strip()
    settings.manager_name=(request.form.get("manager_name") or "").strip()
    settings.manager_phone=(request.form.get("manager_phone") or "").strip()
    settings.document_header=request.form.get("document_header")
    settings.document_footer=request.form.get("document_footer")
    try:
        logo=request.files.get("logo")
        if logo and logo.filename:
            settings.logo_path=save_image(logo,current_app.config["UPLOAD_FOLDER"],"branding")
        signature=request.files.get("manager_signature")
        if signature and signature.filename:
            settings.manager_signature_path=save_image(signature,current_app.config["UPLOAD_FOLDER"],"branding")
    except ValueError as exc:
        flash(str(exc),"danger")
        return redirect(url_for("settings.index"))
    db.session.commit()
    after={"project_name":settings.project_name,"currency":settings.currency,"drum_liters":str(settings.drum_liters),"max_farmers_per_employee":settings.max_farmers_per_employee,"max_credit_drums_per_farmer":str(settings.max_credit_drums_per_farmer),"max_dispense_liters_per_day":str(settings.max_dispense_liters_per_day),"default_sale_price_per_liter":str(settings.default_sale_price_per_liter)}
    audit("settings.updated","project_settings",settings.id,before=before,after=after)
    db.session.commit()
    flash("تم حفظ إعدادات المشروع والثيم.","success")
    return redirect(url_for("settings.index"))
