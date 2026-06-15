import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        Index("ix_matches_match_date", "match_date"),
        Index("ix_matches_kickoff_at", "kickoff_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_football_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True
    )
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    group_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    home_score_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    # Команда-победитель матча. Нужна ТОЛЬКО для начисления чемпиона по финалу,
    # когда основное время — ничья (победа по пенальти/допвремени). Очки за
    # прогнозы по-прежнему считаются строго по основному времени; счёт ET/PKS
    # нигде не хранится — только сам факт «кто прошёл дальше».
    winner_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RoomMatchMultiplier(Base):
    """Бонусный коэффициент матча — **свойство комнаты**: у каждой комнаты свой
    множитель (0 | 1 | 2 | 3) для каждого матча. Отсутствие строки = 1.
    0 — аннулирование матча в этой комнате (очки 0, точный счёт не в тайбрейк).
    Задаётся админом комнаты; применяется при начислении/симуляции только в этой
    комнате."""

    __tablename__ = "room_match_multipliers"
    __table_args__ = (Index("ix_room_match_mult_match", "match_id"),)

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    multiplier: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1", default=1
    )


class TeamMatch(Base):
    """Справочник матчей сборных за 2026 год во всех турнирах (форма команд
    на странице прогноза). Заполняется разово скриптом
    scripts/fetch_team_fixtures.py и НЕ участвует в прогнозах/очках — матчи
    самого ЧМ сюда не пишутся (они в matches и подмешиваются при чтении)."""

    __tablename__ = "team_matches"
    __table_args__ = (
        Index("ix_team_matches_home", "home_team"),
        Index("ix_team_matches_away", "away_team"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_football_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    kickoff_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    competition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
