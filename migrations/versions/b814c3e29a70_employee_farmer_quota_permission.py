"""ensure employees can adjust their assigned farmer quota

Revision ID: b814c3e29a70
Revises: f6c8d2a4b910
"""

from alembic import op
import sqlalchemy as sa


revision = "b814c3e29a70"
down_revision = "f6c8d2a4b910"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    permission_id = connection.execute(
        sa.text("SELECT id FROM permission WHERE key = :key"),
        {"key": "farmers.quota.change"},
    ).scalar()

    if permission_id is None:
        result = connection.execute(
            sa.text(
                "INSERT INTO permission (key, label, module) "
                "VALUES (:key, :label, :module)"
            ),
            {
                "key": "farmers.quota.change",
                "label": "تعديل كمية المزارع المتفق عليها",
                "module": "farmers",
            },
        )
        permission_id = result.lastrowid
        if permission_id is None:
            permission_id = connection.execute(
                sa.text("SELECT id FROM permission WHERE key = :key"),
                {"key": "farmers.quota.change"},
            ).scalar()

    employee_role_id = connection.execute(
        sa.text("SELECT id FROM role WHERE name = :name"),
        {"name": "employee"},
    ).scalar()

    if employee_role_id is not None and permission_id is not None:
        already_linked = connection.execute(
            sa.text(
                "SELECT 1 FROM role_permission "
                "WHERE role_id = :role_id AND permission_id = :permission_id"
            ),
            {"role_id": employee_role_id, "permission_id": permission_id},
        ).first()
        if not already_linked:
            connection.execute(
                sa.text(
                    "INSERT INTO role_permission (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {"role_id": employee_role_id, "permission_id": permission_id},
            )


def downgrade():
    # Keep permission assignments intact when rolling back the feature.
    pass
