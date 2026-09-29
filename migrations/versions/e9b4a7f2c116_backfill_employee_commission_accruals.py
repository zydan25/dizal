"""backfill accounting accruals for frozen employee commissions

Revision ID: e9b4a7f2c116
Revises: e9b4a7f2c115
"""

from decimal import Decimal
from datetime import date
from alembic import op
import sqlalchemy as sa


revision = "e9b4a7f2c116"
down_revision = "e9b4a7f2c115"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    account_rows = conn.execute(
        sa.text("SELECT id, code FROM account WHERE code IN ('6100','2100')")
    ).mappings().all()
    account_ids = {row["code"]: row["id"] for row in account_rows}
    missing = {"6100", "2100"} - set(account_ids)
    if missing:
        raise RuntimeError(
            "لا يمكن ترحيل عمولات الموظفين لأن الحسابات النظامية غير موجودة: "
            + ", ".join(sorted(missing))
        )

    rows = conn.execute(
        sa.text(
            """
            SELECT
                fd.id,
                fd.document_id,
                fd.employee_id,
                fd.created_at,
                fd.employee_commission_amount
            FROM fuel_dispense fd
            WHERE fd.status = 'approved'
              AND COALESCE(fd.employee_commission_amount, 0) > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM journal_entry je
                  WHERE je.source_type = 'employee_commission_accrual'
                    AND je.source_id = CAST(fd.id AS VARCHAR)
              )
            """
        )
    ).mappings().all()

    if not rows:
        return

    for row in rows:
        amount = Decimal(str(row["employee_commission_amount"] or 0))
        entry_date = row["created_at"].date() if row["created_at"] else date.today()

        entry = conn.execute(
            sa.text(
                """
                INSERT INTO journal_entry
                    (entry_date, source_type, source_id, document_id, description, created_by_id, created_at)
                VALUES
                    (:entry_date, 'employee_commission_accrual', :source_id,
                     :document_id, 'استحقاق عمولة الموظف (ترحيل تاريخي)',
                     :created_by_id, CURRENT_TIMESTAMP)
                RETURNING id
                """
            ),
            {
                "entry_date": entry_date,
                "source_id": str(row["id"]),
                "document_id": row["document_id"],
                "created_by_id": row["employee_id"],
            },
        ).scalar_one()

        conn.execute(
            sa.text(
                """
                INSERT INTO journal_line
                    (journal_entry_id, account_id, debit, credit, employee_id, farmer_id, description)
                VALUES
                    (:entry_id, :expense_account, :amount, 0, :employee_id, NULL, 'مصروف عمولة الموظف')
                """
            ),
            {
                "entry_id": entry,
                "expense_account": account_ids["6100"],
                "amount": amount,
                "employee_id": row["employee_id"],
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO journal_line
                    (journal_entry_id, account_id, debit, credit, employee_id, farmer_id, description)
                VALUES
                    (:entry_id, :liability_account, 0, :amount, :employee_id, NULL, 'التزام عمولة الموظف')
                """
            ),
            {
                "entry_id": entry,
                "liability_account": account_ids["2100"],
                "amount": amount,
                "employee_id": row["employee_id"],
            },
        )


def downgrade():
    # Historical accrual entries are intentionally retained on downgrade.
    # Removing them could also remove legitimate newer accruals created after
    # this migration was applied.
    pass
