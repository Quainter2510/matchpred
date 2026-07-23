import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class RoomScoring(BaseModel):
    points_exact: int = Field(ge=0, le=1000)
    points_diff: int = Field(ge=0, le=1000)
    points_outcome: int = Field(ge=0, le=1000)
    points_champion: int = Field(ge=0, le=1000)
    points_scorer: int = Field(ge=0, le=1000)


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=4, max_length=128)
    # Special-prediction deadline. Defaults to the earliest match kickoff of the
    # tournament's scope.
    first_match_at: datetime | None = None
    # Тип турнира: world_cup | rpl | ucl | custom. Задаёт лигу, схему туров и
    # вид спецпрогноза (см. services/tournament.py).
    tournament_type: str = Field(default="world_cup", max_length=20)
    # Сезон реальной лиги (обязателен для лиговых типов rpl/ucl).
    season: int | None = None
    # Окно длительности (метки туров-недель): включаются матчи в [starts_on,
    # ends_on]. None/None — весь турнир.
    starts_on: date | None = None
    ends_on: date | None = None
    # Правила начисления очков; None — значения по умолчанию.
    scoring: RoomScoring | None = None


class RoomSummary(BaseModel):
    id: uuid.UUID
    name: str
    member_count: int
    is_member: bool
    is_active: bool = True
    my_role: str | None = None  # 'admin' | 'player' | None
    tournament_type: str = "world_cup"
    special_kind: str = "wc"


class RoomDetail(RoomSummary):
    first_match_at: datetime
    total_points: int | None = None
    place: int | None = None
    scoring: RoomScoring | None = None
    rules_text: str | None = None
    league_id: int | None = None
    season: int | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    special_result_team: str | None = None


class TournamentTypeOut(BaseModel):
    id: str
    label: str
    special_kind: str
    has_league: bool  # привязан к одной реальной лиге (не custom)
    needs_season: bool  # требуется ли выбор сезона при создании


class CustomLeagueOut(BaseModel):
    id: int
    label: str


class CustomMatchAdd(BaseModel):
    match_id: uuid.UUID


class RoundOut(BaseModel):
    """Тур реальной лиги с датами — для выбора длительности «с тура по тур»."""

    round: str
    first_kickoff: datetime
    last_kickoff: datetime
    first_tour_date: date
    last_tour_date: date
    match_count: int


class RoomRulesTextUpdate(BaseModel):
    # Пустая строка = сбросить к стандартному описанию очков.
    rules_text: str = Field(max_length=10000)


class RoomArchiveUpdate(BaseModel):
    archived: bool


class RoomJoinRequest(BaseModel):
    password: str = Field(min_length=1)


class RoomPasswordUpdate(BaseModel):
    new_password: str = Field(min_length=4, max_length=128)


class RoomMemberOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    system_role: str
    room_role: str
    total_points: int
    exact_scores_count: int
    participation_confirmed: bool


class RoomRoleUpdate(BaseModel):
    role: str = Field(pattern="^(admin|player)$")


class ParticipationUpdate(BaseModel):
    confirmed: bool
