"""per-room match multipliers

Bonus multiplier (0 | 1 | 2 | 3) becomes a per-room property: each room admin
controls it for their own room. The global matches.points_multiplier column is
replaced by the room_match_multipliers table (absence of a row = 1). Existing
non-default multipliers are carried over to every room so already-awarded points
stay consistent.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "room_match_multipliers",
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "match_id",
            UUID(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("multiplier", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_room_match_mult_match", "room_match_multipliers", ["match_id"]
    )

    # Carry the current global multiplier of each match into every room so the
    # already-awarded points keep matching the configured multiplier.
    op.execute(
        """
        INSERT INTO room_match_multipliers (room_id, match_id, multiplier)
        SELECT r.id, m.id, m.points_multiplier
        FROM rooms r
        CROSS JOIN matches m
        WHERE m.points_multiplier <> 1
        """
    )

    op.drop_column("matches", "points_multiplier")


def downgrade() -> None:
    op.add_column(
        "matches",
        sa.Column(
            "points_multiplier", sa.SmallInteger(), nullable=False, server_default="1"
        ),
    )
    op.drop_index("ix_room_match_mult_match", table_name="room_match_multipliers")
    op.drop_table("room_match_multipliers")
