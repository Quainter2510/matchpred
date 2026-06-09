"""add tournament_members.participation_confirmed (visual-only flag)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tournament_members",
        sa.Column(
            "participation_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("tournament_members", "participation_confirmed")
