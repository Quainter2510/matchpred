import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class Room(Base):
    """A single prediction competition. Many rooms run in parallel over the
    same (global) set of matches; each room has its own password, members,
    predictions and leaderboard. Only a superadmin can create rooms."""

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
