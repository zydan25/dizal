from flask import current_app,flash,redirect,render_template,request,url_for
from ...decorators import permission_required
from ...extensions import db
from ...models import ProjectSettings
from ...services.audit import audit
from ...services.files import save_image
from . import settings_bp

@settings_bp.route("/",methods=["GET","POST"])
@permission_required("settings.manage")
def index():
    settings=ProjectSettings.get()
    if request.method=="POST":
        settings.project_name=(request.form.get("project_name") or settings.project_name).strip()
        settings.manager_name=(request.form.get("manager_name") or "").strip() or None
        settings.manager_phone=(request.form.get("manager_phone") or "").strip() or None
        settings.currency=(request.form.get("currency") or settings.currency).strip()
        settings.drum_liters=request.form.get("drum_liters") or settings.drum_liters
        settings.max_farmers_per_employee=int(request.form.get("max_farmers_per_employee") or settings.max_farmers_per_employee)
        settings.max_credit_drums_per_farmer=request.form.get("max_credit_drums_per_farmer") or settings.max_credit_drums_per_farmer
        settings.max_dispense_liters_per_day=request.form.get("max_dispense_liters_per_day") or settings.max_dispense_liters_per_day
        settings.default_sale_price_per_liter=request.form.get("default_sale_price_per_liter") or settings.default_sale_price_per_liter
        settings.primary_color=(request.form.get("primary_color") or settings.primary_color).strip()
        settings.secondary_color=(request.form.get("secondary_color") or settings.secondary_color).strip()
        settings.accent_color=(request.form.get("accent_color") or settings.accent_color).strip()
        settings.surface_color=(request.form.get("surface_color") or settings.surface_color).strip()
        settings.danger_color=(request.form.get("danger_color") or settings.danger_color).strip()
        settings.radius=(request.form.get("radius") or settings.radius).strip()
        settings.font_family=(request.form.get("font_family") or settings.font_family).strip()
        settings.document_header=request.form.get("document_header")
        settings.document_footer=request.form.get("document_footer")
        logo=request.files.get("logo")
        signature=request.files.get("manager_signature")
        if logo and logo.filename:
            settings.logo_path=save_image(logo,current_app.config["UPLOAD_FOLDER"],"branding")
        if signature and signature.filename:
            settings.manager_signature_path=save_image(signature,current_app.config["UPLOAD_FOLDER"],"branding")
        audit("settings.updated","project_settings",settings.id,after={"project_name":settings.project_name,"currency":settings.currency,"primary_color":settings.primary_color})
        db.session.commit()
        flash("تم حفظ إعدادات المشروع والثيم والسندات.","success")
        return redirect(url_for("settings.index"))
    return render_template("settings/index.html",settings=settings)
