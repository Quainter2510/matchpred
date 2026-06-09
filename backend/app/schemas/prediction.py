import uuid
from datetime import date

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    match_id: uuid.UUID
    home: int = Field(ge=0, le=20)
    away: int = Field(ge=0, le=20)


class PredictionBatchRequest(BaseModel):
    predictions: list[PredictionItem]


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
