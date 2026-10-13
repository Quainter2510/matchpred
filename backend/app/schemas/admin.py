import uuid
from datetime import datetime

from pydantic import BaseModel


class TransferRequest(BaseModel):
    target_user_id: uuid.UUID


class SyncLeagueRequest(BaseModel):
    league_id: int
    season: int


class AdminUserOut(BaseModel):
    id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    system_role: str
    is_active: bool
    created_at: datetime | None = None
    providers: list[str] = []


class LoginLinkOut(BaseModel):
    url: str
    expires_in: int  # секунд


class VkLinkCodeOut(BaseModel):
    code: str
    bot_url: str | None = None
    expires_in: int  # секунд
    already_linked: bool = False


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: uuid.UUID | None = None
    actor_nickname: str | None = None
    event_type: str
    target_id: uuid.UUID | None = None
    details: dict | None = None
