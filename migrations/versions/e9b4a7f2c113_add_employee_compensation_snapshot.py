"""freeze employee compensation on each fuel dispense

Revision ID: e9b4a7f2c114
Revises: e9b4a7f2c113
"""

from decimal import Decimal
from alembic import op
import sqlalchemy as sa


revision = "e9b4a7f2c114"
down_revision = "e9b4a7f2c113"
branch_labels = None
depends_on = None


VARIABLE_TYPES = {"per_liter", "per_drum", "percent_profit", "commission"}


def _commission_amount(salary_type, value, liters, drums, gross_profit):
    value = Decimal(str(value or 0))
    liters = Decimal(str(liters or 0))
    drums = Decimal(str(drums or 0))
    gross_profit = Decimal(str(gross_profit or 0))
    if salary_type == "per_liter":
        return liters * value
    if salary_type == "per_drum":
        return drums * value
    if salary_type in {"percent_profit", "commission"}:
        return max(gross_profit, Decimal("0")) * value / Decimal("100")
    return Decimal("0")


def upgrade():
    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.add_column(sa.Column("employee_compensation_type", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("employee_compensation_value", sa.Numeric(precision=18, scale=3), nullable=True))
        batch_op.add_column(sa.Column("employee_commission_amount", sa.Numeric(precision=18, scale=3), nullable=False, server_default="0"))

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        """
        SELECT
            fd.id,
            fd.liters,
            fd.drums,
            fd.gross_profit,
            ep.salary_type,
            ep.salary_value
        FROM fuel_dispense fd
        LEFT JOIN employee_profile ep ON ep.user_id = fd.employee_id
        """
    )).mappings().all()

    updates = []
    for row in rows:
        salary_type = (row["salary_type"] or "fixed").strip()
        value = Decimal(str(row["salary_value"] or 0))
        amount = _commission_amount(
            salary_type,
            value,
            row["liters"],
            row["drums"],
            row["gross_profit"],
        ) if salary_type in VARIABLE_TYPES else Decimal("0")
        updates.append({
            "id": row["id"],
            "compensation_type": salary_type,
            "compensation_value": value,
            "commission_amount": amount,
        })

    if updates:
        conn.execute(
            sa.text(
                """
                UPDATE fuel_dispense
                SET employee_compensation_type = :compensation_type,
                    employee_compensation_value = :compensation_value,
                    employee_commission_amount = :commission_amount
                WHERE id = :id
                """
            ),
            updates,
        )

    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.alter_column("employee_commission_amount", server_default=None)


def downgrade():
    with op.batch_alter_table("fuel_dispense", schema=None) as batch_op:
        batch_op.drop_column("employee_commission_amount")
        batch_op.drop_column("employee_compensation_value")
        batch_op.drop_column("employee_compensation_type")
