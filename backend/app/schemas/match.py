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
    points_multiplier: int = 1
    # Победитель (для чемпиона при ничьей в финале); прогнозы — по основному времени.
    winner_team: str | None = None
    my_prediction: MyPrediction | None = None


class MatchDay(BaseModel):
    date: date
    match_count: int
    my_predictions_count: int
    first_kickoff_at: datetime
    # Коэффициент тура: значение, если у всех матчей дня он одинаковый,
    # иначе None (смешанный — бейджи только на отдельных матчах).
    multiplier: int | None = 1
    # Сколько матчей дня завершено и мои очки за них (тур идёт, пока
    # finished_count < match_count).
    finished_count: int = 0
    my_points: int = 0
    # Заполняемость тура (только для админов комнаты, иначе null): сколько
    # участников дали прогноз на ВСЕ матчи дня и сколько участников всего.
    members_filled: int | None = None
    members_total: int | None = None


class MultiplierUpdate(BaseModel):
    multiplier: int = Field(ge=0, le=3)


class MatchCreate(BaseModel):
    # match_date больше не передаётся: тур вычисляется из kickoff_at
    # (граница 10:00 МСК). Поле оставлено опциональным для совместимости —
    # значение всё равно пересчитывается на бэкенде.
    match_date: date | None = None
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
    # Победитель при ничьей в основное время (пенальти/допвремя) — нужен для
    # начисления чемпиона по финалу. Должен совпадать с одной из команд матча.
    winner_team: str | None = None


class TeamFormMatch(BaseModel):
    kickoff_at: datetime
    competition: str | None = None
    home_team: str
    away_team: str
    home_score: int
    away_score: int


class MatchFormOut(BaseModel):
    """Последние сыгранные матчи обеих сборных (форма) для страницы прогноза."""

    home_team: str
    away_team: str
    home: list[TeamFormMatch]
    away: list[TeamFormMatch]


class PlayerPredictionOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    # null — участник не сделал прогноз (в списке все участники комнаты).
    predicted_home: int | None = None
    predicted_away: int | None = None
    points_awarded: int | None = None
    is_exact: bool | None = None
