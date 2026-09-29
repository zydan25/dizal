"""employee sale price policy

Revision ID: 3a2c7e1f2026
Revises: 7b1e3c9a2026
"""
from alembic import op
import sqlalchemy as sa

revision = "3a2c7e1f2026"
down_revision = "7b1e3c9a2026"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("employee_can_change_sale_price", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column("employee_can_change_sale_price", server_default=None)

def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("employee_can_change_sale_price")
