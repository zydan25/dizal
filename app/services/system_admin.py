from datetime import datetime,timezone
from pathlib import Path
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from flask import current_app
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
        if db.engine.url.get_backend_name()=="sqlite":
            db_file=db.engine.url.database
            if not db_file or db_file==":memory:":
                with db.engine.connect() as connection:
                    rows=connection.exec_driver_sql("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name").fetchall()
                    sql_path.write_text("\n".join(row[0] for row in rows if row[0]),encoding="utf-8")
            else:
                raw_path=Path(db_file)
                if not raw_path.is_absolute():
                    raw_path=Path(current_app.instance_path)/raw_path
                conn=sqlite3.connect(str(raw_path))
                try:
                    with sql_path.open("w",encoding="utf-8") as handle:
                        for line in conn.iterdump():
                            handle.write(line+"\n")
                finally:
                    conn.close()
        elif db.engine.url.get_backend_name()=="postgresql":
            dump_uri=uri.replace("+psycopg2","").replace("+psycopg","")
            result=subprocess.run(["pg_dump","--dbname",dump_uri,"--no-owner","--no-acl"],capture_output=True,text=True,timeout=180)
            if result.returncode!=0:
                raise RuntimeError("فشل إنشاء نسخة PostgreSQL: "+(result.stderr.strip() or "pg_dump error"))
            sql_path.write_text(result.stdout,encoding="utf-8")
        else:
            raise RuntimeError("نوع قاعدة البيانات الحالي لا يدعم النسخ الاحتياطي الآلي.")
        manifest=tmp_path/"backup-info.txt"
        manifest.write_text("Dizal backup\nCreated: "+stamp+" UTC\nDatabase backend: "+db.engine.url.get_backend_name()+"\nUploads are included except generated runtime/cache files.\n",encoding="utf-8")
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

def reset_project_data():
    """Clear operational/project data while preserving administrator accounts and system configuration.

    This function intentionally does not commit. The caller can add the final audit row
    and commit the whole database reset atomically.
    """
    from sqlalchemy import delete
    from ..models import Role,User,Cashbox,EmployeeProfile

    manager_ids=set(
        user.id
        for user in User.query.join(User.roles).filter(Role.name=="manager").all()
    )

    # Remove non-manager employee profiles before deleting their user rows.
    employee_profile_table=db.metadata.tables.get("employee_profile")
    if employee_profile_table is not None:
        if manager_ids:
            db.session.execute(
                delete(employee_profile_table).where(
                    employee_profile_table.c.user_id.notin_(manager_ids)
                )
            )
        else:
            db.session.execute(delete(employee_profile_table))

    # Preserve active cashboxes for administrator accounts that are also employees;
    # all their transactions are removed by the general operational purge.
    cashbox_table=db.metadata.tables.get("cashbox")
    if cashbox_table is not None:
        keep_cashbox_ids=set(
            row.id for row in Cashbox.query.filter(
                Cashbox.box_type=="central"
            ).all()
        )
        if manager_ids:
            keep_cashbox_ids.update(
                row.id for row in Cashbox.query.filter(
                    Cashbox.box_type=="employee",
                    Cashbox.owner_user_id.in_(manager_ids),
                ).all()
            )

    preserve_tables={
        "user","role","permission","role_permission","roles_users",
        "project_settings","account","whatsapp_config","whatsapp_template",
        "employee_profile","cashbox","alembic_version"
    }

    # Delete every remaining operational table in dependency-safe reverse order.
    for table in reversed(db.metadata.sorted_tables):
        if table.name in preserve_tables:
            continue
        db.session.execute(table.delete())

    # Keep role links only for administrator accounts.
    roles_users=db.metadata.tables.get("roles_users")
    if roles_users is not None:
        if manager_ids:
            db.session.execute(
                delete(roles_users).where(
                    roles_users.c.user_id.notin_(manager_ids)
                )
            )
        else:
            db.session.execute(delete(roles_users))

    # Delete every non-administrator account. Manager accounts survive the reset,
    # including accounts created through the employee screen with manager role.
    if manager_ids:
        db.session.execute(
            delete(User.__table__).where(
                User.__table__.c.id.notin_(manager_ids)
            )
        )
    else:
        db.session.execute(delete(User.__table__))

    # Clear stale ORM identity state caused by bulk DELETEs.
    db.session.expire_all()

    upload_root=Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    if upload_root.exists():
        for child in upload_root.iterdir():
            if child.name=="branding":
                continue
            if child.is_dir():
                shutil.rmtree(child,ignore_errors=True)
            elif child.is_file():
                try:
                    child.unlink()
                except OSError:
                    pass

    from .accounting import ensure_accounts
    if not Cashbox.query.filter_by(box_type="central",is_active=True).first():
        db.session.add(Cashbox(name="الصندوق الرئيسي",box_type="central",is_active=True))
    ensure_accounts()
    db.session.flush()

