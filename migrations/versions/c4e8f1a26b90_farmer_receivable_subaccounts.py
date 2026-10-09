"""create dedicated receivable subaccounts for farmers

Revision ID: c4e8f1a26b90
Revises: b814c3e29a70
"""

from alembic import op
import sqlalchemy as sa


revision = "c4e8f1a26b90"
down_revision = "b814c3e29a70"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    control_id = connection.execute(
        sa.text("SELECT id FROM account WHERE code = :code"),
        {"code": "1400"},
    ).scalar()
    if control_id is None:
        connection.execute(
            sa.text(
                "INSERT INTO account "
                "(code, name, account_type, parent_id, is_system, active) "
                "VALUES (:code, :name, :account_type, :parent_id, :is_system, :active)"
            ),
            {
                "code": "1400",
                "name": "ذمم المزارعين",
                "account_type": "asset",
                "parent_id": None,
                "is_system": True,
                "active": True,
            },
        )
        control_id = connection.execute(
            sa.text("SELECT id FROM account WHERE code = :code"),
            {"code": "1400"},
        ).scalar()

    farmers = connection.execute(
        sa.text("SELECT id, name FROM farmer ORDER BY id")
    ).fetchall()

    for farmer_id, farmer_name in farmers:
        code = f"1400-F{int(farmer_id):06d}"
        account_id = connection.execute(
            sa.text("SELECT id FROM account WHERE code = :code"),
            {"code": code},
        ).scalar()

        if account_id is None:
            connection.execute(
                sa.text(
                    "INSERT INTO account "
                    "(code, name, account_type, parent_id, is_system, active) "
                    "VALUES (:code, :name, :account_type, :parent_id, :is_system, :active)"
                ),
                {
                    "code": code,
                    "name": f"ذمم المزارع - {farmer_name}",
                    "account_type": "asset",
                    "parent_id": control_id,
                    "is_system": False,
                    "active": True,
                },
            )
            account_id = connection.execute(
                sa.text("SELECT id FROM account WHERE code = :code"),
                {"code": code},
            ).scalar()
        else:
            connection.execute(
                sa.text(
                    "UPDATE account SET name = :name, parent_id = :parent_id, "
                    "account_type = :account_type, active = :active WHERE id = :id"
                ),
                {
                    "name": f"ذمم المزارع - {farmer_name}",
                    "parent_id": control_id,
                    "account_type": "asset",
                    "active": True,
                    "id": account_id,
                },
            )

        # Move previously posted receivable journal lines into the farmer's own
        # subaccount, retaining the farmer dimension and the original journal.
        connection.execute(
            sa.text(
                "UPDATE journal_line SET account_id = :farmer_account_id "
                "WHERE farmer_id = :farmer_id AND account_id = :control_account_id"
            ),
            {
                "farmer_account_id": account_id,
                "farmer_id": farmer_id,
                "control_account_id": control_id,
            },
        )


def downgrade():
    connection = op.get_bind()
    control_id = connection.execute(
        sa.text("SELECT id FROM account WHERE code = :code"),
        {"code": "1400"},
    ).scalar()
    if control_id is None:
        return

    connection.execute(
        sa.text(
            "UPDATE journal_line SET account_id = :control_id "
            "WHERE account_id IN (SELECT id FROM account WHERE code LIKE '1400-F%')"
        ),
        {"control_id": control_id},
    )
    connection.execute(
        sa.text("DELETE FROM account WHERE code LIKE '1400-F%'")
    )
