"""merge existing Dizal migration heads

Revision ID: e9b4a7f2c117
Revises: 1f2a9b7c2026, e9b4a7f2c116
"""

from alembic import op


revision = "e9b4a7f2c117"
down_revision = ("1f2a9b7c2026", "e9b4a7f2c116")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
