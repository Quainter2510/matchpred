import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_membership
from app.models import OAuthAccount, TournamentMember, User
from app.redis_client import redis_client
from app.schemas.auth import (
    MeResponse,
    TelegramVerifyRequest,
    TokenResponse,
    TournamentJoinRequest,
    UpdateNicknameRequest,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_token,
    verify_password,
)
from app.services import audit
from app.services.oauth import telegram, yandex

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
STATE_PREFIX = "oauth_state:"


def _set_refresh_cookie(response: Response, user_id: uuid.UUID) -> None:
    token = create_refresh_token(str(user_id))
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


async def _tournament_role(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    member = await get_membership(db, user_id)
    return member.tournament_role if member else None


async def _issue_access(db: AsyncSession, user: User) -> str:
    role = await _tournament_role(db, user.id)
    return create_access_token(str(user.id), user.nickname, user.system_role, role)


async def _generate_nickname(db: AsyncSession, base: str) -> str:
    base = "".join(c for c in (base or "user") if c.isalnum())[:18] or "user"
    if len(base) < 3:
        base = (base + "user")[:6]
    candidate = base
    while True:
        exists = await db.scalar(select(User.id).where(User.nickname == candidate))
        if not exists:
            return candidate
        candidate = f"{base}{secrets.randbelow(10000)}"[:24]


async def _upsert_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    suggested_nickname: str,
    avatar_url: str | None,
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> tuple[User, bool]:
    """Find-or-create a user for an OAuth identity.

    The superadmin is assigned atomically: we lock the users table and, if it
    is empty, the very first registered user becomes superadmin.
    Returns (user, is_new_user)."""
    acc = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    if acc:
        user = await db.get(User, acc.user_id)
        return user, False

    # Lock the users table to make the "first user => superadmin" check race-free.
    await db.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
    count = await db.scalar(select(func.count()).select_from(User))
    system_role = "superadmin" if count == 0 else "user"

    nickname = await _generate_nickname(db, suggested_nickname)
    user = User(nickname=nickname, avatar_url=avatar_url, system_role=system_role)
    db.add(user)
    await db.flush()

    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token_enc=encrypt_token(access_token),
            refresh_token_enc=encrypt_token(refresh_token),
        )
    )

    await audit.log_event(
        db,
        "user_registered",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=user.id,
        details={"provider": provider},
    )
    if system_role == "superadmin":
        # The superadmin joins the tournament without a password — give them an
        # admin membership immediately so they appear in leaderboard/members.
        db.add(TournamentMember(user_id=user.id, tournament_role="admin"))
        await audit.log_event(
            db,
            "superadmin_assigned",
            actor_id=user.id,
            actor_nickname=user.nickname,
            target_id=user.id,
        )
    return user, True


# ---------------- Yandex OAuth ----------------
@router.get("/yandex/login")
async def yandex_login():
    state = secrets.token_urlsafe(24)
    await redis_client.setex(STATE_PREFIX + state, 600, "1")
    return RedirectResponse(yandex.build_authorize_url(state))


@router.get("/yandex/callback")
async def yandex_callback(
    code: str,
    state: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Single-use CSRF state.
    if not await redis_client.get(STATE_PREFIX + state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid state")
    await redis_client.delete(STATE_PREFIX + state)

    token_data = await yandex.exchange_code(code)
    profile = await yandex.fetch_profile(token_data["access_token"])

    user, is_new = await _upsert_oauth_user(
        db,
        "yandex",
        profile["provider_user_id"],
        profile["display_name"],
        profile["avatar_url"],
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
    )
    await db.commit()
    await db.refresh(user)

    access = await _issue_access(db, user)
    # Redirect back to the SPA with the access token in the fragment.
    redirect = RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback#access_token={access}&is_new_user={str(is_new).lower()}"
    )
    _set_refresh_cookie(redirect, user.id)
    return redirect


# ---------------- Telegram Login Widget ----------------
@router.get("/telegram/login")
async def telegram_login():
    # The widget is rendered on the frontend; this endpoint documents the flow.
    return {
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "method": "Render Telegram Login Widget, then POST /auth/telegram/verify",
    }


@router.post("/telegram/verify", response_model=TokenResponse)
async def telegram_verify(
    payload: TelegramVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude_none=True)
    if not telegram.verify_telegram_auth(data):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Telegram verification failed")

    profile = telegram.extract_profile(data)
    user, is_new = await _upsert_oauth_user(
        db,
        "telegram",
        profile["provider_user_id"],
        profile["username"] or profile["first_name"],
        profile["avatar_url"],
    )
    await db.commit()
    await db.refresh(user)

    access = await _issue_access(db, user)
    _set_refresh_cookie(response, user.id)
    return TokenResponse(access_token=access, is_new_user=is_new)


# ---------------- Session ----------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")
    decoded = decode_token(token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await db.get(User, uuid.UUID(decoded["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return TokenResponse(access_token=await _issue_access(db, user))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await _tournament_role(db, user.id)
    return MeResponse(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        system_role=user.system_role,
        tournament_role=role,
    )


@router.patch("/me", response_model=MeResponse)
async def update_me(
    payload: UpdateNicknameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nick = payload.nickname.strip()
    if not (3 <= len(nick) <= 24):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nickname length 3-24")
    taken = await db.scalar(
        select(User.id).where(User.nickname == nick, User.id != user.id)
    )
    if taken:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nickname already taken")
    old = user.nickname
    user.nickname = nick
    await audit.log_event(
        db,
        "nickname_changed",
        actor_id=user.id,
        actor_nickname=nick,
        target_id=user.id,
        details={"from": old, "to": nick},
    )
    await db.commit()
    role = await _tournament_role(db, user.id)
    return MeResponse(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        system_role=user.system_role,
        tournament_role=role,
    )


@router.post("/tournament-join", response_model=MeResponse)
async def tournament_join(
    payload: TournamentJoinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import Tournament

    # Superadmin joins without a password.
    if user.system_role != "superadmin":
        tournament = await db.scalar(select(Tournament).limit(1))
        if not tournament:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tournament not configured")
        if not verify_password(payload.password, tournament.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")

    existing = await get_membership(db, user.id)
    if not existing:
        role = "admin" if user.system_role == "superadmin" else "player"
        db.add(TournamentMember(user_id=user.id, tournament_role=role))
        await db.commit()

    role = await _tournament_role(db, user.id)
    return MeResponse(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        system_role=user.system_role,
        tournament_role=role,
    )
