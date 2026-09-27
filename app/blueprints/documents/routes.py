from flask import render_template
from flask_login import current_user
from ...decorators import permission_required
from ...models import Document
from ...services.document_views import get_document
from ...permissions import user_has_permission
from . import documents_bp

@documents_bp.get("/<int:document_id>")
@permission_required("documents.view")
def view(document_id):
    document,source=get_document(document_id)
    if not user_has_permission(current_user,"users.manage") and document.created_by_id!=current_user.id:
        from flask import abort
        abort(403)
    return render_template("documents/view.html",document=document,source=source)

@documents_bp.get("/<int:document_id>/print")
@permission_required("documents.view")
def print_document(document_id):
    document,source=get_document(document_id)
    if not user_has_permission(current_user,"users.manage") and document.created_by_id!=current_user.id:
        from flask import abort
        abort(403)
    return render_template("documents/print.html",document=document,source=source)
