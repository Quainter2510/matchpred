"""tournament_matches: explicit match set for custom tournaments

Кастомный турнир (тип custom) не привязан к одной лиге — админ вручную выбирает
матчи из разных лиг (топ-5 + РПЛ + ЛЧ). Их набор хранится в этой join-таблице.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tournament_matches",
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
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_tournament_matches_match", "tournament_matches", ["match_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tournament_matches_match", table_name="tournament_matches")
    op.drop_table("tournament_matches")
