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
