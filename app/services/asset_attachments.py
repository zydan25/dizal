from pathlib import Path

from ..extensions import db
from ..models import DocumentAttachment
from .files import save_attachment

MAX_ASSET_ATTACHMENT_COUNT = 10


def cleanup_asset_uploads(storage_keys, upload_root):
    """Remove files written before a database transaction failed."""
    root = Path(upload_root).resolve()
    for storage_key in storage_keys or []:
        try:
            target = (root / storage_key).resolve()
            if root in target.parents and target.is_file():
                target.unlink()
        except OSError:
            # Do not hide the original transaction error when cleanup also fails.
            pass


def add_asset_attachments(asset, uploaded_files, upload_root):
    """Attach up to ten PDF/image receipts to the asset's purchase document."""
    files = [
        item for item in (uploaded_files or [])
        if item is not None and (getattr(item, "filename", "") or "").strip()
    ]
    if len(files) > MAX_ASSET_ATTACHMENT_COUNT:
        raise ValueError("الحد الأقصى 10 ملفات لكل عملية رفع.")
    if not files:
        return [], 0
    if not getattr(asset, "document_id", None):
        raise ValueError("لا يوجد سند شراء مرتبط بهذا الأصل لحفظ المرفقات عليه.")

    saved_keys = []
    try:
        for uploaded in files:
            metadata = save_attachment(uploaded, upload_root, folder="assets")
            saved_keys.append(metadata["storage_key"])
            db.session.add(DocumentAttachment(
                document_id=asset.document_id,
                original_name=metadata["original_name"],
                storage_key=metadata["storage_key"],
                mime_type=metadata["mime_type"],
                size_bytes=metadata["size_bytes"],
                sha256=metadata["sha256"],
            ))
        return saved_keys, len(files)
    except Exception:
        cleanup_asset_uploads(saved_keys, upload_root)
        raise
