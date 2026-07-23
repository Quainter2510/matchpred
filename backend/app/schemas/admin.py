import uuid
from datetime import datetime

from pydantic import BaseModel


class TransferRequest(BaseModel):
    target_user_id: uuid.UUID


class SyncLeagueRequest(BaseModel):
    league_id: int
    season: int


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: uuid.UUID | None = None
    actor_nickname: str | None = None
    event_type: str
    target_id: uuid.UUID | None = None
    details: dict | None = None
