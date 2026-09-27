from pathlib import Path
from uuid import uuid4
import hashlib
import mimetypes
from PIL import Image

IMAGE_EXTENSIONS={"png","jpg","jpeg","webp"}
DOCUMENT_EXTENSIONS={"png","jpg","jpeg","webp","pdf"}
DOCUMENT_MIME_PREFIXES=("image/","application/pdf")

def _safe_name(original):
    original=(original or "").strip()
    if not original or "." not in original:
        raise ValueError("الملف غير صالح.")
    return original,original.rsplit(".",1)[1].lower()

def save_image(file_storage,upload_root,folder):
    original,extension=_safe_name(file_storage.filename)
    if extension not in IMAGE_EXTENSIONS:
        raise ValueError("يسمح فقط بصور PNG/JPG/JPEG/WEBP.")
    try:
        image=Image.open(file_storage)
        image.verify()
    except Exception as exc:
        raise ValueError("الملف ليس صورة سليمة.") from exc
    target_dir=Path(upload_root)/folder
    target_dir.mkdir(parents=True,exist_ok=True)
    name=f"{uuid4().hex}.{extension}"
    target=target_dir/name
    file_storage.stream.seek(0)
    with target.open("wb") as handle:
        handle.write(file_storage.stream.read())
    return str(target.relative_to(upload_root))

def save_attachment(file_storage,upload_root,folder="documents"):
    original,extension=_safe_name(file_storage.filename)
    if extension not in DOCUMENT_EXTENSIONS:
        raise ValueError("نوع الملف غير مدعوم.")
    mime=mimetypes.guess_type(original)[0] or "application/octet-stream"
    if not mime.startswith(DOCUMENT_MIME_PREFIXES):
        raise ValueError("نوع الملف غير مسموح.")
    if extension=="pdf":
        file_storage.stream.seek(0)
        header=file_storage.stream.read(4)
        file_storage.stream.seek(0)
        if header != b"%PDF":
            raise ValueError("ملف PDF غير صالح.")
    else:
        try:
            image=Image.open(file_storage)
            image.verify()
        except Exception as exc:
            raise ValueError("الملف ليس صورة سليمة.") from exc
        file_storage.stream.seek(0)

    target_dir=Path(upload_root)/folder
    target_dir.mkdir(parents=True,exist_ok=True)
    name=f"{uuid4().hex}.{extension}"
    target=target_dir/name
    digest=hashlib.sha256()
    size=0
    with target.open("wb") as handle:
        while True:
            chunk=file_storage.stream.read(1024*1024)
            if not chunk:
                break
            digest.update(chunk)
            size+=len(chunk)
            handle.write(chunk)
    return {"storage_key":str(target.relative_to(upload_root)),"original_name":original,"mime_type":mime,"size_bytes":size,"sha256":digest.hexdigest()}
