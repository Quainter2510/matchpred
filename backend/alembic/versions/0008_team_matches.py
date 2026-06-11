"""team_matches: reference list of national-team games in 2026

Filled once by scripts/fetch_team_fixtures.py (all competitions of the 48 WC
teams). Used only for the "recent form" block on the predict page — never for
predictions or scoring. WC matches themselves are NOT stored here (they live
in `matches` and are merged in at read time).

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("competition", sa.String(100), nullable=True),
        sa.Column("home_team", sa.String(100), nullable=False),
        sa.Column("away_team", sa.String(100), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
    )
    op.create_index("ix_team_matches_home", "team_matches", ["home_team"])
    op.create_index("ix_team_matches_away", "team_matches", ["away_team"])


def downgrade() -> None:
    op.drop_index("ix_team_matches_away", table_name="team_matches")
    op.drop_index("ix_team_matches_home", table_name="team_matches")
    op.drop_table("team_matches")
