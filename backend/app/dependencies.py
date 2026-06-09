import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TournamentMember, User
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


async def get_membership(
    db: AsyncSession, user_id: uuid.UUID
) -> TournamentMember | None:
    return await db.get(TournamentMember, user_id)


async def require_player(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Player+ access. tournament_role is re-read from the DB — we don't trust
    the JWT for authorization-critical decisions. Superadmin always passes."""
    if user.system_role == "superadmin":
        return user
    member = await get_membership(db, user.id)
    if not member:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not a tournament member"
        )
    return user


async def require_admin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if user.system_role == "superadmin":
        return user
    member = await get_membership(db, user.id)
    if not member or member.tournament_role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


async def require_superadmin(
    user: User = Depends(get_current_user),
) -> User:
    if user.system_role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superadmin access required")
    return user


async def is_admin_or_super(db: AsyncSession, user: User) -> bool:
    if user.system_role == "superadmin":
        return True
    member = await get_membership(db, user.id)
    return bool(member and member.tournament_role == "admin")
