import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Room, RoomMember, User
from app.security import decode_token


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = auth[7:]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """Как get_current_user, но без 401 — для публичных страниц (лобби),
    которые показывают больше деталей вошедшим пользователям."""
    if not request.headers.get("Authorization", "").startswith("Bearer "):
        return None
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if user.system_role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superadmin access required")
    return user


async def is_any_admin(db: AsyncSession, user: User) -> bool:
    """True for superadmin or anyone who is an admin of at least one room."""
    if user.system_role == "superadmin":
        return True
    found = await db.scalar(
        select(RoomMember.user_id).where(
            RoomMember.user_id == user.id, RoomMember.room_role == "admin"
        )
    )
    return found is not None


async def require_any_admin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Gate for GLOBAL match operations (results, sync, recalculate). Match
    results are shared facts, so any room admin — or the superadmin — may set
    them; the result then scores every room."""
    if not await is_any_admin(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


# ---------------- Room-scoped access ----------------
@dataclass
class RoomContext:
    user: User
    room: Room
    member: RoomMember | None  # None when a superadmin acts without membership
    is_admin: bool


async def _load_room_ctx(
    room_id: uuid.UUID, user: User, db: AsyncSession
) -> RoomContext:
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    member = await db.get(RoomMember, (room_id, user.id))
    is_admin = user.system_role == "superadmin" or (
        member is not None and member.room_role == "admin"
    )
    return RoomContext(user=user, room=room, member=member, is_admin=is_admin)


async def require_room_member(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomContext:
    ctx = await _load_room_ctx(room_id, user, db)
    if ctx.member is None and user.system_role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this room")
    return ctx


async def require_room_admin(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomContext:
    ctx = await _load_room_ctx(room_id, user, db)
    if not ctx.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Room admin access required")
    return ctx
