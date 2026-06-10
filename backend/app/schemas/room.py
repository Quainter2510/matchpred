import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=4, max_length=128)
    # Special-prediction deadline. Defaults to the earliest match kickoff.
    first_match_at: datetime | None = None


class RoomScoring(BaseModel):
    points_exact: int = Field(ge=0, le=1000)
    points_diff: int = Field(ge=0, le=1000)
    points_outcome: int = Field(ge=0, le=1000)
    points_champion: int = Field(ge=0, le=1000)
    points_scorer: int = Field(ge=0, le=1000)


class RoomSummary(BaseModel):
    id: uuid.UUID
    name: str
    member_count: int
    is_member: bool
    is_active: bool = True
    my_role: str | None = None  # 'admin' | 'player' | None


class RoomDetail(RoomSummary):
    first_match_at: datetime
    total_points: int | None = None
    place: int | None = None
    scoring: RoomScoring | None = None


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
