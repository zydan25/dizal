import os
from app import create_app
from app.extensions import db
from app.models import Permission,ProjectSettings,Role,RolePermission,User
from app.permissions import PERMISSIONS,ROLE_PERMISSIONS
from flask_security.utils import hash_password

app=create_app()

with app.app_context():
    ProjectSettings.get()
    rows={}
    for key,(label,module) in PERMISSIONS.items():
        row=Permission.query.filter_by(key=key).first()
        if not row:
            row=Permission(key=key,label=label,module=module)
            db.session.add(row)
        else:
            row.label=label
            row.module=module
        rows[key]=row
    db.session.flush()
    for role_name,permission_keys in ROLE_PERMISSIONS.items():
        role=Role.query.filter_by(name=role_name).first()
        if not role:
            role=Role(name=role_name,description=role_name,label="مدير" if role_name=="manager" else "موظف",is_system=True)
            db.session.add(role)
            db.session.flush()
        RolePermission.query.filter_by(role_id=role.id).delete()
        for key in permission_keys:
            db.session.add(RolePermission(role_id=role.id,permission_id=rows[key].id))
    db.session.flush()
    username=os.getenv("DIZAL_ADMIN_USERNAME","admin")
    email=os.getenv("DIZAL_ADMIN_EMAIL","admin@dizal.local")
    password=os.getenv("DIZAL_ADMIN_PASSWORD","change-me-now")
    user=User.query.filter_by(username=username).first()
    if not user:
        user=User(username=username,email=email,password=hash_password(password),display_name="مدير المشروع",active=True,fs_uniquifier=os.urandom(16).hex())
        db.session.add(user)
        db.session.flush()
    manager_role=Role.query.filter_by(name="manager").first()
    if manager_role not in user.roles:
        user.roles.append(manager_role)
    db.session.commit()
    print("Dizal Phase 1 seed completed.")
