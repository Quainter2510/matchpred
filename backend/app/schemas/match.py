import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MyPrediction(BaseModel):
    predicted_home: int
    predicted_away: int
    points_awarded: int | None = None
    is_exact: bool | None = None


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    api_football_id: int | None = None
    match_date: date
    kickoff_at: datetime
    stage: str
    group_name: str | None = None
    home_team: str
    away_team: str
    home_score_ft: int | None = None
    away_score_ft: int | None = None
    status: str
    my_prediction: MyPrediction | None = None


class MatchDay(BaseModel):
    date: date
    match_count: int
    my_predictions_count: int


class MatchCreate(BaseModel):
    match_date: date
    kickoff_at: datetime
    stage: str = Field(max_length=40)
    home_team: str = Field(max_length=100)
    away_team: str = Field(max_length=100)


class MatchUpdate(BaseModel):
    kickoff_at: datetime | None = None
    match_date: date | None = None
    stage: str | None = None
    home_team: str | None = None
    away_team: str | None = None


class MatchResult(BaseModel):
    home_score_ft: int = Field(ge=0, le=50)
    away_score_ft: int = Field(ge=0, le=50)


class PlayerPredictionOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    predicted_home: int
    predicted_away: int
    points_awarded: int | None = None
    is_exact: bool | None = None
