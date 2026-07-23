import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Room(Base):
    """Один турнир прогнозов. Много турниров идут параллельно; у каждого свой
    тип, привязка к реальной лиге+сезону, пул матчей, пароль, участники,
    прогнозы и таблица. Создаёт только суперадмин. (Историческое имя таблицы —
    `rooms`; в UI это «турнир».)"""

    __tablename__ = "rooms"
    __table_args__ = (Index("ix_rooms_name", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_match_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # is_active=False means the room is archived: read-only, not scored, but the
    # leaderboard stays viewable.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---- Тип турнира и привязка к реальной лиге ----
    # tournament_type: world_cup | rpl | ucl | custom (см. services/tournament.py).
    # league_id/season — реальная лига+сезон API-Football (None у custom).
    # tour_anchor — якорный день недели туров (Пн=0…Вс=6); NULL = суточная
    #   группировка (ЧМ). starts_on/ends_on — окно включения матчей по метке
    #   тура (NULL = весь турнир). special_kind — вид спецпрогноза.
    #   special_result_team — вручную заданный ответ спецпрогноза (лидер лиги).
    tournament_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="world_cup"
    )
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tour_anchor: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    special_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="wc"
    )
    special_result_team: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Free-form regulations text shown behind the "i" button next to the
    # title. NULL = show the default description built from the point values.
    rules_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Per-room scoring rules (a superadmin may change these per room).
    points_exact: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="5")
    points_diff: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="2")
    points_outcome: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    points_champion: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="10")
    points_scorer: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="10")


class RoomMember(Base):
    __tablename__ = "room_members"
    __table_args__ = (
        Index(
            "ix_room_members_leaderboard",
            "room_id",
            "total_points",
            "exact_scores_count",
        ),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    room_role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    exact_scores_count: Mapped[int] = mapped_column(Integer, default=0)
    # Visual-only flag retained from the single-tournament version.
    participation_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
