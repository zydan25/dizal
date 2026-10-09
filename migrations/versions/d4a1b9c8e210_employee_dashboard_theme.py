"""add selectable employee dashboard theme

Revision ID: d4a1b9c8e210
Revises: 4c8d2e9f2026
"""

from alembic import op
import sqlalchemy as sa


revision = "d4a1b9c8e210"
down_revision = "4c8d2e9f2026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "employee_dashboard_theme",
                sa.String(length=20),
                nullable=False,
                server_default="classic",
            )
        )
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("employee_dashboard_theme", server_default=None)


def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("employee_dashboard_theme")
