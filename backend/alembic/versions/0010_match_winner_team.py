"""match winner team (for champion award on penalty finals)

Adds matches.winner_team: the team that actually won the match (including a
penalty shootout / extra time). Used ONLY to award the champion special
prediction when the final ends level in regular time. Prediction points are
still scored strictly on the main-time (FT) score — ET/PKS scores are not
stored, only which team advanced.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("winner_team", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "winner_team")
