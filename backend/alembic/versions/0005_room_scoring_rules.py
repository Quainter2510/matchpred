"""per-room scoring rules

Adds editable point values to each room: exact / diff / outcome / champion /
scorer. Existing rooms keep the canonical defaults (5 / 2 / 1 / 10 / 10).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("points_exact", "5"),
    ("points_diff", "2"),
    ("points_outcome", "1"),
    ("points_champion", "10"),
    ("points_scorer", "10"),
]


def upgrade() -> None:
    for name, default in _COLUMNS:
        op.add_column(
            "rooms",
            sa.Column(name, sa.SmallInteger(), nullable=False, server_default=default),
        )


def downgrade() -> None:
    for name, _ in _COLUMNS:
        op.drop_column("rooms", name)
