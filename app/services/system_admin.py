from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import zipfile
from flask import current_app
from sqlalchemy import inspect
from ..extensions import db

def backup_folder():
    folder=Path(current_app.instance_path)/"backups"
    folder.mkdir(parents=True,exist_ok=True)
    return folder

def create_backup():
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target=backup_folder()/f"dizal-backup-{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="dizal-backup-") as tmp:
        tmp_path=Path(tmp)
        sql_path=tmp_path/"database.sql"
        uri=str(db.engine.url)
        backend=db.engine.url.get_backend_name()
        if backend=="sqlite":
            db_file=db.engine.url.database
            if not db_file or db_file==":memory:":
                with db.engine.connect() as connection:
                    rows=connection.exec_driver_sql(
                        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"
                    ).fetchall()
                    sql_path.write_text("\n".join(row[0] for row in rows if row[0]),encoding="utf-8")
            else:
                raw_path=Path(db_file)
                if not raw_path.is_absolute():
                    raw_path=Path(current_app.instance_path)/raw_path
                if not raw_path.exists():
                    raise RuntimeError("ملف قاعدة SQLite غير موجود.")
                conn=sqlite3.connect(str(raw_path))
                try:
                    with sql_path.open("w",encoding="utf-8") as handle:
                        for line in conn.iterdump():
                            handle.write(line+"\n")
                finally:
                    conn.close()
        elif backend=="postgresql":
            dump_uri=uri.replace("+psycopg2","").replace("+psycopg","")
            result=subprocess.run(
                ["pg_dump","--dbname",dump_uri,"--no-owner","--no-acl"],
                capture_output=True,text=True,timeout=180
            )
            if result.returncode!=0:
                raise RuntimeError("فشل إنشاء نسخة PostgreSQL: "+(result.stderr.strip() or "pg_dump error"))
            sql_path.write_text(result.stdout,encoding="utf-8")
        else:
            raise RuntimeError("نوع قاعدة البيانات الحالي لا يدعم النسخ الاحتياطي الآلي.")
        manifest=tmp_path/"backup-info.txt"
        manifest.write_text(
            "Dizal backup\nCreated: "+stamp+" UTC\nDatabase backend: "+backend+
            "\nUploads are included except generated runtime/cache files.\n",
            encoding="utf-8"
        )
        with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
            archive.write(sql_path,"database.sql")
            archive.write(manifest,"backup-info.txt")
            upload_root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
            if upload_root.exists():
                for path in upload_root.rglob("*"):
                    if path.is_file():
                        archive.write(path,path.relative_to(upload_root).as_posix())
    return target

def list_backups():
    return sorted(backup_folder().glob("dizal-backup-*.zip"),key=lambda p:p.stat().st_mtime,reverse=True)

def reset_project_data(preserve_user_id=None):
    inspector=inspect(db.engine)
    table_names=set(inspector.get_table_names())
    preserve={
        "user","role","permission","role_permission","roles_users","project_settings",
        "account","whatsapp_config","whatsapp_template","alembic_version"
    }
    # Remove all transactional/operational rows first, children before parents.
    # The metadata dependency order is deterministic for the current schema.
    for table in reversed(db.metadata.sorted_tables):
        if table.name in preserve or table.name not in table_names:
            continue
        db.session.execute(table.delete())
    roles_users=db.metadata.tables.get("roles_users")
    if roles_users is not None:
        if preserve_user_id is not None:
            db.session.execute(roles_users.delete().where(roles_users.c.user_id!=preserve_user_id))
        else:
            db.session.execute(roles_users.delete())
    from ..models import User,Cashbox,Role
    if preserve_user_id is not None:
        db.session.query(User).filter(User.id!=preserve_user_id).delete(synchronize_session=False)
    # Safety: the active operator must remain a manager after a system reset.
    preserved=db.session.get(User,preserve_user_id) if preserve_user_id is not None else None
    manager_role=Role.query.filter_by(name="manager").first()
    if preserved is not None and manager_role is not None and manager_role not in preserved.roles:
        preserved.roles.clear()
        preserved.roles.append(manager_role)
        preserved.active=True
    db.session.flush()
    upload_root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    if upload_root.exists():
        for child in upload_root.iterdir():
            if child.name=="branding":
                continue
            if child.is_dir():
                import shutil
                shutil.rmtree(child,ignore_errors=True)
            elif child.is_file():
                try:
                    child.unlink()
                except OSError:
                    pass
    if not Cashbox.query.filter_by(box_type="central",is_active=True).first():
        db.session.add(Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True))
    from .accounting import ensure_accounts
    ensure_accounts()
    db.session.flush()
