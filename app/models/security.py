from flask_security.models import fsqla_v2 as fsqla
from ..extensions import db

fsqla.FsModels.set_db_info(db)

class Role(db.Model, fsqla.FsRoleMixin):
    __tablename__ = "role"
    label = db.Column(db.String(120), nullable=True)
    is_system = db.Column(db.Boolean, nullable=False, default=True)

class User(db.Model, fsqla.FsUserMixin):
    __tablename__ = "user"
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(32), unique=True, nullable=True, index=True)
    # Email is optional in Dizal; phone/username are the primary employee identifiers.
    # Override Flask-Security's default non-null email column to keep the model aligned with the database migration.
    email = db.Column(db.String(255), unique=True, nullable=True)
    display_name = db.Column(db.String(160), nullable=True)
    locale = db.Column(db.String(10), nullable=False, default="ar")
    is_employee = db.Column(db.Boolean, nullable=False, default=False)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    @property
    def role_names(self):
        return [role.name for role in self.roles]

class Permission(db.Model):
    __tablename__ = "permission"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    label = db.Column(db.String(180), nullable=False)
    module = db.Column(db.String(80), nullable=False, index=True)

class RolePermission(db.Model):
    __tablename__ = "role_permission"
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)
    role = db.relationship("Role", backref=db.backref("permission_links", cascade="all, delete-orphan"))
    permission = db.relationship("Permission")

class UserPermissionOverride(db.Model):
    __tablename__ = "user_permission_override"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_key = db.Column(db.String(120), nullable=False, index=True)
    allowed = db.Column(db.Boolean, nullable=False)
    user = db.relationship("User", backref="permission_overrides")
