from pathlib import Path
from uuid import uuid4
from PIL import Image

ALLOWED_EXTENSIONS={"png","jpg","jpeg","webp"}

def save_image(file_storage,upload_root,folder):
    original=(file_storage.filename or "").strip()
    if not original or "." not in original:
        raise ValueError("الملف غير صالح.")
    extension=original.rsplit(".",1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
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
