"""make user email optional

Revision ID: 4c8d2e9f2026
Revises: e9b4a7f2c117
"""

from alembic import op
import sqlalchemy as sa


revision = "4c8d2e9f2026"
down_revision = "e9b4a7f2c117"
branch_labels = None
depends_on = None


def upgrade():
    # Dizal employees may authenticate using username/phone and may not have an email.
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade():
    # Restore the old NOT NULL contract with deterministic placeholder emails
    # for users that were created without an email after this migration.
    op.execute(
        'UPDATE "user" '
        "SET email = 'user-' || id::text || '@invalid.local' "
        "WHERE email IS NULL"
    )
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            nullable=False,
        )
