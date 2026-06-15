import uuid
from datetime import datetime

from pydantic import BaseModel


class StandingsMatch(BaseModel):
    id: uuid.UUID
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    status: str
    kickoff_at: datetime


class GroupTeamRow(BaseModel):
    team: str
    played: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


class GroupStanding(BaseModel):
    name: str  # буква группы (A…L)
    teams: list[GroupTeamRow]  # отсортированы по месту
    matches: list[StandingsMatch]


class PlayoffStage(BaseModel):
    stage: str  # технический код стадии; подпись формирует фронт (utils/stage.ts)
    matches: list[StandingsMatch]


class StandingsOut(BaseModel):
    groups: list[GroupStanding]
    playoff: list[PlayoffStage]


class TopScorer(BaseModel):
    name: str
    photo: str | None = None
    team: str | None = None
    goals: int


class PredictedScorer(BaseModel):
    name: str
    photo: str | None = None
    goals: int
    backers: int  # сколько участников комнаты выбрали этого бомбардира


class TopScorersOut(BaseModel):
    updated_at: str | None = None  # ISO момент последнего обновления снимка
    top: list[TopScorer]  # топ-5 бомбардиров турнира
    predicted: list[PredictedScorer]  # все, кого выбрали участники комнаты
