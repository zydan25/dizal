"""system operations, direct sales, tank-asset links

Revision ID: 7b1e3c9a2026
Revises: e9b4a7f2c113
"""
from alembic import op
import sqlalchemy as sa

revision = "7b1e3c9a2026"
down_revision = "e9b4a7f2c113"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tank_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_asset_tank_id", ["tank_id"], unique=False)
        batch_op.create_foreign_key("fk_asset_tank_id_fuel_tank", "fuel_tank", ["tank_id"], ["id"])

    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.alter_column("farmer_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("sale_type", sa.String(length=20), nullable=False, server_default="farmer"))
        batch_op.add_column(sa.Column("customer_name", sa.String(length=180), nullable=True))
        batch_op.create_index("ix_fuel_dispense_sale_type", ["sale_type"], unique=False)

    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.alter_column("sale_type", server_default=None)

def downgrade():
    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.drop_index("ix_fuel_dispense_sale_type")
        batch_op.drop_column("customer_name")
        batch_op.drop_column("sale_type")
        batch_op.alter_column("farmer_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.drop_constraint("fk_asset_tank_id_fuel_tank", type_="foreignkey")
        batch_op.drop_index("ix_asset_tank_id")
        batch_op.drop_column("tank_id")
