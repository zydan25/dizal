from flask import current_app,flash,redirect,render_template,request,url_for,send_file,abort
from ...decorators import permission_required
from flask_security.utils import verify_password
from ...extensions import db
from ...models import ProjectSettings
from ...services.audit import audit
from ...services.system_admin import create_backup,reset_project_data
from ...services.files import save_image
from . import settings_bp

PALETTES={
    "blue":{"label":"أزرق احترافي","primary":"#1877F2","secondary":"#4f46e5","accent":"#10b981","surface":"#f6f8fc","danger":"#dc3545"},
    "violet":{"label":"بنفسجي فاخر","primary":"#6d28d9","secondary":"#9333ea","accent":"#c026d3","surface":"#faf7ff","danger":"#dc3545"},
    "teal":{"label":"فيروزي هادئ","primary":"#0f766e","secondary":"#0e7490","accent":"#14b8a6","surface":"#f3fbfa","danger":"#dc3545"},
    "emerald":{"label":"أخضر تشغيلي","primary":"#15803d","secondary":"#0f766e","accent":"#16a34a","surface":"#f4fbf6","danger":"#dc3545"},
    "sunset":{"label":"مرجاني دافئ","primary":"#ea580c","secondary":"#be185d","accent":"#f59e0b","surface":"#fff8f3","danger":"#dc3545"},
    "night":{"label":"ليلي بنفسجي","primary":"#312e81","secondary":"#581c87","accent":"#a855f7","surface":"#f5f3ff","danger":"#dc3545"},
}
FONT_SCALES={"0.95":"أصغر","1":"متوسط","1.05":"كبير قليلًا","1.10":"كبير"}

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
        font_scale=request.form.get("font_scale") or settings.font_scale or "1"
        if font_scale not in FONT_SCALES: font_scale="1"
        settings.font_scale=font_scale
        selected_palette=request.form.get("color_preset") or ""
        if selected_palette in PALETTES:
            colors=PALETTES[selected_palette]
            settings.primary_color=colors["primary"]
            settings.secondary_color=colors["secondary"]
            settings.accent_color=colors["accent"]
            settings.surface_color=colors["surface"]
            settings.danger_color=colors["danger"]
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
    current_palette=next((key for key,colors in PALETTES.items() if settings.primary_color==colors["primary"] and settings.secondary_color==colors["secondary"] and settings.accent_color==colors["accent"]), "")
    return render_template("settings/index.html",settings=settings,palettes=PALETTES,font_scales=FONT_SCALES,current_palette=current_palette)

@settings_bp.post("/backup")
@permission_required("settings.manage")
def backup():
    try:
        path=create_backup()
        audit("system.backup.created","system",0,after={"filename":path.name})
        db.session.commit()
        flash("تم إنشاء النسخة الاحتياطية وحفظها على الخادم.","success")
    except Exception as exc:
        db.session.rollback()
        flash("تعذر إنشاء النسخة الاحتياطية: "+str(exc),"danger")
    return redirect(url_for("settings.index"))

@settings_bp.get("/backup/<path:filename>")
@permission_required("settings.manage")
def backup_download(filename):
    from pathlib import Path
    safe=Path(filename).name
    if safe!=filename or not safe.startswith("dizal-backup-") or not safe.endswith(".zip"): abort(404)
    root=(Path(current_app.instance_path)/"backups").resolve()
    path=(root/safe).resolve()
    if root not in path.parents or not path.is_file(): abort(404)
    return send_file(path,as_attachment=True,download_name=safe)

@settings_bp.post("/reset")
@permission_required("settings.manage")
def reset():
    from flask_login import current_user
    password=request.form.get("password") or ""
    confirmation=request.form.get("confirmation") or ""
    if not verify_password(password,current_user.password):
        flash("كلمة المرور غير صحيحة. لم يتم تصفير النظام.","danger")
        return redirect(url_for("settings.index"))
    if confirmation!="تصفير":
        flash("اكتب كلمة «تصفير» لتأكيد العملية.","danger")
        return redirect(url_for("settings.index"))
    try:
        reset_project_data()
        audit("system.reset","system",0,after={"preserved":"manager/settings/roles/permissions"})
        db.session.commit()
        flash("تم تصفير بيانات المشروع وحذف حسابات الموظفين، مع إبقاء حساب المدير والإعدادات الأساسية.","success")
    except Exception as exc:
        db.session.rollback()
        flash("فشل التصفير ولم تكتمل العملية: "+str(exc),"danger")
    return redirect(url_for("settings.index"))
