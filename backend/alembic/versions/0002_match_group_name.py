"""add matches.group_name (group letter from standings)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("group_name", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "group_name")
