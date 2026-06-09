import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemberOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    system_role: str
    tournament_role: str
    total_points: int
    exact_scores_count: int


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(admin|player)$")


class PasswordUpdate(BaseModel):
    new_password: str = Field(min_length=4, max_length=128)


class TransferRequest(BaseModel):
    target_user_id: uuid.UUID


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: uuid.UUID | None = None
    actor_nickname: str | None = None
    event_type: str
    target_id: uuid.UUID | None = None
    details: dict | None = None
