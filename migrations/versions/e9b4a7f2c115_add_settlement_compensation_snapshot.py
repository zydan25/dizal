"""freeze compensation mode on employee settlements

Revision ID: e9b4a7f2c115
Revises: e9b4a7f2c114
"""

from alembic import op
import sqlalchemy as sa


revision = "e9b4a7f2c115"
down_revision = "e9b4a7f2c114"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("employee_settlement", schema=None) as batch_op:
        batch_op.add_column(sa.Column("compensation_type_snapshot", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("compensation_value_snapshot", sa.Numeric(precision=18, scale=3), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        """
        SELECT
            es.id,
            ep.salary_type,
            ep.salary_value
        FROM employee_settlement es
        LEFT JOIN employee_profile ep ON ep.user_id = es.employee_id
        """
    )).mappings().all()

    updates = [
        {
            "id": row["id"],
            "compensation_type": (row["salary_type"] or "fixed").strip(),
            "compensation_value": row["salary_value"] or 0,
        }
        for row in rows
    ]
    if updates:
        conn.execute(
            sa.text(
                """
                UPDATE employee_settlement
                SET compensation_type_snapshot = :compensation_type,
                    compensation_value_snapshot = :compensation_value
                WHERE id = :id
                """
            ),
            updates,
        )


def downgrade():
    with op.batch_alter_table("employee_settlement", schema=None) as batch_op:
        batch_op.drop_column("compensation_value_snapshot")
        batch_op.drop_column("compensation_type_snapshot")
