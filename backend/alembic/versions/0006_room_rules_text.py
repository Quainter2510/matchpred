"""per-room regulations text

Adds rooms.rules_text — free-form regulations shown to players behind the
"i" button next to the competition title. NULL means "use the default
description built from the room's point values".

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rooms", sa.Column("rules_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rooms", "rules_text")
