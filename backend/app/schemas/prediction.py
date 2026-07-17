import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    match_id: uuid.UUID
    home: int = Field(ge=0, le=20)
    away: int = Field(ge=0, le=20)


class PredictionBatchRequest(BaseModel):
    predictions: list[PredictionItem]


class AdminPredictionSet(BaseModel):
    """Суперадмин задаёт прогноз участнику (после дедлайна, до ввода счёта)."""

    home: int = Field(ge=0, le=20)
    away: int = Field(ge=0, le=20)


class PredictionResult(BaseModel):
    match_id: uuid.UUID
    accepted: bool
    reason: str | None = None


class PredictionBatchResponse(BaseModel):
    results: list[PredictionResult]


class MyPredictionOut(BaseModel):
    match_id: uuid.UUID
    predicted_home: int
    predicted_away: int
    points_awarded: int | None = None
    is_exact: bool | None = None


class TourPointsOut(BaseModel):
    date: date
    points: int
    exact_count: int


class TourPlayerMatch(BaseModel):
    """Матч тура в раскрывающемся списке игрока. predicted_* = null, если
    прогноза нет ИЛИ он ещё скрыт (чужой прогноз до начала матча)."""

    match_id: uuid.UUID
    kickoff_at: datetime
    home_team: str
    away_team: str
    status: str
    home_score: int | None = None
    away_score: int | None = None
    started: bool
    predicted_home: int | None = None
    predicted_away: int | None = None
    points_awarded: int | None = None
    is_exact: bool | None = None


class TourPlayerOut(BaseModel):
    """Строка итогов тура: очки участника за все завершённые матчи дня
    (пропущенные прогнозы дают 0) + раскрывающийся список матчей."""

    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    points: int
    exact_count: int
    predictions_count: int
    match_count: int
    matches: list[TourPlayerMatch] = []
