"""bonus multiplier for matches/tours

Adds matches.points_multiplier (0 | 1 | 2 | 3). All prediction points for the
match are multiplied by it; 0 voids the match (emergency case). A "tour"
multiplier is just the value applied to every match of that date.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("points_multiplier", sa.SmallInteger(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("matches", "points_multiplier")
