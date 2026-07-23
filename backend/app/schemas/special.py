import uuid

from pydantic import BaseModel


class SpecialPredictionOut(BaseModel):
    champion_team: str | None = None
    top_scorer_name: str | None = None
    top_scorer_api_id: int | None = None
    champion_points: int | None = None
    scorer_points: int | None = None
    locked: bool = False


class SpecialPredictionUpdate(BaseModel):
    champion_team: str | None = None
    top_scorer_name: str | None = None
    top_scorer_api_id: int | None = None


class SpecialPredictionPublic(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    champion_team: str | None = None
    top_scorer_name: str | None = None
    champion_points: int | None = None
    scorer_points: int | None = None


class ScorerResultRequest(BaseModel):
    player_api_id: int
    player_name: str


class LeaderResultRequest(BaseModel):
    # Команда-победитель спецпрогноза «лидер лиги» (РПЛ и т.п.).
    team: str


class PlayerSearchItem(BaseModel):
    api_id: int
    name: str
    team: str | None = None
    photo: str | None = None
