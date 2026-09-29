"""add employee sale price override policy

Revision ID: 1f2a9b7c2026
Revises: 7b1e3c9a2026
"""
from alembic import op
import sqlalchemy as sa

revision = "1f2a9b7c2026"
down_revision = "7b1e3c9a2026"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("allow_employee_sale_price_override", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("allow_employee_sale_price_override", server_default=None)

def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("allow_employee_sale_price_override")
