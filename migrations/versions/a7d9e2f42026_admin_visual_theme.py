"""Add the optional, system-wide Water POS administration theme.

Revision ID: a7d9e2f42026
Revises: f6c8d2a4b910
"""
from alembic import op
import sqlalchemy as sa

revision = "a7d9e2f42026"
down_revision = "f6c8d2a4b910"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "admin_theme",
                sa.String(length=30),
                nullable=False,
                server_default="classic",
            )
        )
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("admin_theme", server_default=None)


def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("admin_theme")
