"""add persistent font scale to project settings

Revision ID: e9b4a7f2c113
Revises: 89f47e4e0629
"""

from alembic import op
import sqlalchemy as sa

revision = "e9b4a7f2c113"
down_revision = "89f47e4e0629"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("font_scale", sa.String(length=10), nullable=False, server_default="1"))
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("font_scale", server_default=None)


def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("font_scale")
