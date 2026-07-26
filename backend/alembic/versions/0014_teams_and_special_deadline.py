"""teams reference (ru names + logos), special_deadline, RPL leader+scorer

- Таблица teams: русские названия и логотипы клубов (заполняется при синке).
- rooms.special_deadline: отдельный настраиваемый срок подачи спецпрогноза
  (NULL = как раньше, по первому матчу турнира).
- РПЛ получает спецпрогноз бомбардира в дополнение к лидеру лиги: тип рпл
  становится special_kind='leader_scorer'.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("api_football_id", sa.Integer(), primary_key=True),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("logo_local", sa.String(length=60), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_teams_name_en", "teams", ["name_en"])

    op.add_column(
        "rooms", sa.Column("special_deadline", sa.DateTime(timezone=True), nullable=True)
    )

    # РПЛ: лидер + бомбардир.
    op.execute(
        "UPDATE rooms SET special_kind = 'leader_scorer' "
        "WHERE tournament_type = 'rpl'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE rooms SET special_kind = 'leader' WHERE tournament_type = 'rpl'"
    )
    op.drop_column("rooms", "special_deadline")
    op.drop_index("ix_teams_name_en", table_name="teams")
    op.drop_table("teams")
