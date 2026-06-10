import uuid

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    is_new_user: bool = False


class TelegramVerifyRequest(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class MeResponse(BaseModel):
    id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    system_role: str
    # Whether the user belongs to at least one room (drives onboarding routing).
    has_rooms: bool = False
    # Superadmin or admin of at least one room — may perform global match ops.
    is_any_admin: bool = False


class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=24)
