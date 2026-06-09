import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, func
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
