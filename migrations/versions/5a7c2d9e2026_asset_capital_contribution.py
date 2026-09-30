"""support asset-based capital contributions

Revision ID: 5a7c2d9e2026
Revises: 4c8d2e9f2026
"""

from alembic import op
import sqlalchemy as sa


revision = "5a7c2d9e2026"
down_revision = "4c8d2e9f2026"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.alter_column(
            "payer_cashbox_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    with op.batch_alter_table("capital_contribution", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "contribution_type",
                sa.String(length=20),
                nullable=False,
                server_default="cash",
            )
        )
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=True))
        batch_op.alter_column(
            "cashbox_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_unique_constraint(
            "uq_capital_contribution_asset_id",
            ["asset_id"],
        )
        batch_op.create_foreign_key(
            "fk_capital_contribution_asset_id",
            "asset",
            ["asset_id"],
            ["id"],
        )
        batch_op.alter_column("contribution_type", server_default=None)


def downgrade():
    with op.batch_alter_table("capital_contribution", schema=None) as batch_op:
        batch_op.drop_constraint("fk_capital_contribution_asset_id", type_="foreignkey")
        batch_op.drop_constraint("uq_capital_contribution_asset_id", type_="unique")
        batch_op.drop_column("asset_id")
        batch_op.alter_column(
            "cashbox_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column("contribution_type")

    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.alter_column(
            "payer_cashbox_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
