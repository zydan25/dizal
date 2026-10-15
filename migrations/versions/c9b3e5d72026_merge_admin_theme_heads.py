"""Merge the existing farmer-ledger migration branch with the Water POS theme.

Revision ID: c9b3e5d72026
Revises: a7d9e2f42026, c4e8f1a26b90
"""
from alembic import op

revision = "c9b3e5d72026"
down_revision = ("a7d9e2f42026", "c4e8f1a26b90")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
