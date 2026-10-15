"""Add independent show/hide controls for the admin and employee bottom navigation.

Revision ID: b6a2d9f42026
Revises: c9b3e5d72026
"""
from alembic import op
import sqlalchemy as sa

revision = "b6a2d9f42026"
down_revision = "c9b3e5d72026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("admin_bottom_nav_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("employee_bottom_nav_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("admin_bottom_nav_enabled", server_default=None)
        batch_op.alter_column("employee_bottom_nav_enabled", server_default=None)


def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("employee_bottom_nav_enabled")
        batch_op.drop_column("admin_bottom_nav_enabled")
