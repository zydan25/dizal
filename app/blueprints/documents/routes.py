from pathlib import Path
from flask import abort,current_app,make_response,render_template,request,send_file
from flask_login import current_user
from ...decorators import permission_required
from ...models import Document,DocumentAttachment
from ...permissions import user_has_permission
from ...services.document_views import get_document
from ...services.audit import audit
from ...services.reversals import reverse_document
from . import documents_bp

def _allowed(document):
    return user_has_permission(current_user,"users.manage") or document.created_by_id==current_user.id or user_has_permission(current_user,"documents.reverse")

def _attachment_file(attachment):
    root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target=(root/attachment.storage_key).resolve()
    if root not in target.parents or not target.is_file():
        abort(404)
    return target

@documents_bp.get("/")
@permission_required("documents.view")
def index():
    status=request.args.get("status")
    document_type=request.args.get("type")
    query=Document.query.order_by(Document.created_at.desc())
    if status: query=query.filter_by(status=status)
    if document_type: query=query.filter_by(document_type=document_type)
    documents=query.limit(200).all()
    types=[row[0] for row in Document.query.with_entities(Document.document_type).distinct().order_by(Document.document_type).all()]
    return render_template("documents/index.html",documents=documents,types=types,status=status,document_type=document_type)

@documents_bp.get("/<int:document_id>")
@permission_required("documents.view")
def view(document_id):
    document,source=get_document(document_id)
    if not _allowed(document): abort(403)
    return render_template("documents/view.html",document=document,source=source)

@documents_bp.get("/<int:document_id>/print")
@permission_required("documents.view")
def print_document(document_id):
    document,source=get_document(document_id)
    if not _allowed(document): abort(403)
    return render_template("documents/print.html",document=document,source=source)

@documents_bp.get("/<int:document_id>/pdf")
@permission_required("documents.view")
def pdf(document_id):
    document,source=get_document(document_id)
    if not _allowed(document): abort(403)
    try:
        from weasyprint import HTML
    except ImportError:
        abort(503,description="مولد PDF غير مثبت على الخادم.")
    html=render_template("documents/print.html",document=document,source=source)
    pdf_bytes=HTML(string=html,base_url=request.url_root).write_pdf()
    response=make_response(pdf_bytes)
    response.headers["Content-Type"]="application/pdf"
    response.headers["Content-Disposition"]=(
        f'attachment; filename="{document.number}.pdf"'
        if request.args.get("download")=="1"
        else f'inline; filename="{document.number}.pdf"'
    )
    return response

@documents_bp.get("/<int:document_id>/attachments/<int:attachment_id>")
@permission_required("documents.view")
def attachment(document_id,attachment_id):
    document,source=get_document(document_id)
    if not _allowed(document): abort(403)
    row=DocumentAttachment.query.filter_by(id=attachment_id,document_id=document.id).first_or_404()
    return send_file(_attachment_file(row),as_attachment=request.args.get("download")=="1",download_name=row.original_name)

@documents_bp.post("/<int:document_id>/reverse")
@permission_required("documents.reverse")
def reverse(document_id):
    document,_=get_document(document_id)
    reason=(request.form.get("reason") or "").strip()
    if not reason:
        from flask import flash,redirect,url_for
        flash("سبب العكس مطلوب حتى يبقى السجل واضحًا.","danger")
        return redirect(url_for("documents.view",document_id=document.id))
    try:
        reversal=reverse_document(document,current_user.id,reason)
        audit("document.reversed","document",document.id,after={"status":"reversed","reversal_document":reversal.number,"reason":reason})
        from flask import flash,redirect,url_for
        flash(f"تم عكس السند وإنشاء {reversal.number}.","success")
        return redirect(url_for("documents.view",document_id=reversal.id))
    except ValueError as exc:
        from flask import flash,redirect,url_for
        from ...extensions import db
        db.session.rollback()
        flash(str(exc),"danger")
        return redirect(url_for("documents.view",document_id=document.id))
