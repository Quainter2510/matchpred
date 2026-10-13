"""rooms: настраиваемые «зелёная» и «красная» зоны таблицы лидеров

- rooms.zone_top / rooms.zone_bottom: сколько первых мест подсвечивается
  зелёным и сколько последних — красным. По умолчанию 3/3 — как было зашито
  во фронте.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rooms",
        sa.Column("zone_top", sa.SmallInteger(), nullable=False, server_default="3"),
    )
    op.add_column(
        "rooms",
        sa.Column("zone_bottom", sa.SmallInteger(), nullable=False, server_default="3"),
    )


def downgrade() -> None:
    op.drop_column("rooms", "zone_bottom")
    op.drop_column("rooms", "zone_top")
