"""add project-wide diesel allocation limit

Revision ID: f6c8d2a4b910
Revises: d4a1b9c8e210
"""

from alembic import op
import sqlalchemy as sa


revision = "f6c8d2a4b910"
down_revision = "d4a1b9c8e210"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project_settings",
        sa.Column(
            "project_diesel_limit_liters",
            sa.Numeric(18, 3),
            nullable=False,
            server_default="6000",
        ),
    )

    # Keep existing projects valid: do not initialize the new cap below diesel
    # already reserved by farmers plus previous approved general sales.
    connection = op.get_bind()
    settings_row = connection.execute(
        sa.text(
            "SELECT id, drum_liters FROM project_settings "
            "WHERE singleton_key = :singleton_key"
        ),
        {"singleton_key": "default"},
    ).first()

    if settings_row:
        quota_drums = connection.execute(
            sa.text(
                "SELECT COALESCE(SUM(quota_drums), 0) FROM farmer "
                "WHERE status IN ('submitted', 'changes_requested', 'approved', 'suspended')"
            )
        ).scalar() or 0

        general_sales_liters = connection.execute(
            sa.text(
                "SELECT COALESCE(SUM(fd.liters), 0) "
                "FROM fuel_dispense AS fd "
                "JOIN document AS d ON d.id = fd.document_id "
                "WHERE fd.sale_type = 'general' "
                "AND fd.status = 'approved' "
                "AND d.status != 'reversed'"
            )
        ).scalar() or 0

        used_liters = (
            float(quota_drums or 0) * float(settings_row.drum_liters or 0)
            + float(general_sales_liters or 0)
        )
        connection.execute(
            sa.text(
                "UPDATE project_settings "
                "SET project_diesel_limit_liters = :limit_liters "
                "WHERE id = :settings_id"
            ),
            {
                "limit_liters": max(6000.0, used_liters),
                "settings_id": settings_row.id,
            },
        )

    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "project_diesel_limit_liters",
            server_default=None,
        )


def downgrade():
    with op.batch_alter_table("project_settings", schema=None) as batch_op:
        batch_op.drop_column("project_diesel_limit_liters")
