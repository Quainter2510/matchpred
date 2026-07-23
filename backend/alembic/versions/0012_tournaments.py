"""tournaments: tournament type + real league binding

Пивот «сайт ЧМ» → «платформа турниров». Комната расширяется до турнира:
тип, привязка к реальной лиге+сезону, схема туров, окно длительности и вид
спецпрогноза. Матчи получают метки league_id/season/round, по которым турнир
отбирает свой пул.

Бэкфилл: существующие данные — это ЧМ-2026 (league_id=1, season=2026). Все
текущие комнаты становятся типом world_cup с суточной группировкой и
спецпрогнозом wc — поведение не меняется.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

# Значения ЧМ-2026 для бэкфилла существующих данных.
WC_LEAGUE_ID = 1
WC_SEASON = 2026


def upgrade() -> None:
    # ---- matches: метки лиги/сезона/тура ----
    op.add_column("matches", sa.Column("league_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("season", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("round", sa.String(length=40), nullable=True))
    op.create_index(
        "ix_matches_league_season", "matches", ["league_id", "season", "kickoff_at"]
    )
    op.execute(
        f"UPDATE matches SET league_id = {WC_LEAGUE_ID}, season = {WC_SEASON} "
        "WHERE league_id IS NULL"
    )

    # ---- rooms: тип турнира + привязка ----
    op.add_column(
        "rooms",
        sa.Column(
            "tournament_type",
            sa.String(length=20),
            nullable=False,
            server_default="world_cup",
        ),
    )
    op.add_column("rooms", sa.Column("league_id", sa.Integer(), nullable=True))
    op.add_column("rooms", sa.Column("season", sa.Integer(), nullable=True))
    op.add_column("rooms", sa.Column("tour_anchor", sa.SmallInteger(), nullable=True))
    op.add_column("rooms", sa.Column("starts_on", sa.Date(), nullable=True))
    op.add_column("rooms", sa.Column("ends_on", sa.Date(), nullable=True))
    op.add_column(
        "rooms",
        sa.Column(
            "special_kind", sa.String(length=20), nullable=False, server_default="wc"
        ),
    )
    op.add_column(
        "rooms", sa.Column("special_result_team", sa.String(length=100), nullable=True)
    )
    # Существующие комнаты — ЧМ: привязываем к лиге/сезону; тип/схема/спецпрогноз
    # уже проставлены server_default.
    op.execute(
        f"UPDATE rooms SET league_id = {WC_LEAGUE_ID}, season = {WC_SEASON} "
        "WHERE league_id IS NULL"
    )


def downgrade() -> None:
    op.drop_column("rooms", "special_result_team")
    op.drop_column("rooms", "special_kind")
    op.drop_column("rooms", "ends_on")
    op.drop_column("rooms", "starts_on")
    op.drop_column("rooms", "tour_anchor")
    op.drop_column("rooms", "season")
    op.drop_column("rooms", "league_id")
    op.drop_column("rooms", "tournament_type")

    op.drop_index("ix_matches_league_season", table_name="matches")
    op.drop_column("matches", "round")
    op.drop_column("matches", "season")
    op.drop_column("matches", "league_id")
