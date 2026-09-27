from pathlib import Path
from flask import current_app,send_file,abort
from flask_login import current_user
from ...decorators import permission_required
from ...models import ProjectSettings
from . import media_bp

@media_bp.get("/branding/<path:path>")
@permission_required("settings.view")
def branding(path):
    root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target=(root/path).resolve()
    if root not in target.parents:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_file(target)
