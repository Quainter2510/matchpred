import secrets
import uuid
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, is_any_admin
from app.models import OAuthAccount, RoomMember, User
from app.redis_client import redis_client
from app.schemas.auth import (
    MeResponse,
    TelegramVerifyRequest,
    TokenResponse,
    UpdateNicknameRequest,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_token,
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


async def _has_rooms(db: AsyncSession, user_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(RoomMember.room_id).where(RoomMember.user_id == user_id).limit(1)
    )
    return found is not None


async def _issue_access(db: AsyncSession, user: User) -> str:
    return create_access_token(str(user.id), user.nickname, user.system_role)


async def _vk_linked(db: AsyncSession, user_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(OAuthAccount.id).where(
            OAuthAccount.user_id == user_id, OAuthAccount.provider == "vk"
        )
    )
    return found is not None


async def _me_full(db: AsyncSession, user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        system_role=user.system_role,
        has_rooms=await _has_rooms(db, user.id),
        is_any_admin=await is_any_admin(db, user),
        vk_linked=await _vk_linked(db, user.id),
    )


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
    return {
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "method": "Render Telegram Login Widget, then POST /auth/telegram/verify",
    }


@router.get("/telegram/oauth-redirect")
async def telegram_oauth_redirect():
    """Redirect to oauth.telegram.org — works in all browsers including mobile."""
    bot_id = settings.TELEGRAM_BOT_TOKEN.split(":")[0]
    origin = settings.FRONTEND_URL.rstrip("/")
    callback = f"{origin}/api/v1/auth/telegram/callback"
    # return_to must be a frontend page — Telegram appends #tgAuthResult=BASE64
    # as a URL fragment, which the server never receives; JS reads it instead.
    frontend_callback = f"{origin}/telegram-auth"
    params = urlencode({
        "bot_id": bot_id,
        "origin": origin,
        "embed": "0",
        "request_access": "write",
        "return_to": frontend_callback,
    })
    return RedirectResponse(f"https://oauth.telegram.org/auth?{params}")


@router.get("/telegram/callback")
async def telegram_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Redirect-mode handler for Telegram Login Widget (data-auth-url).
    Used by mobile browsers where the popup-based widget doesn't render.
    Telegram passes auth data as query params; we verify, upsert the user,
    set the refresh cookie and redirect to the frontend.
    """
    data = dict(request.query_params)
    print(f"[TG CALLBACK] received keys: {sorted(data.keys())}")
    print(f"[TG CALLBACK] auth_date={data.get('auth_date')} id={data.get('id')} hash_present={bool(data.get('hash'))}")
    ok = telegram.verify_telegram_auth(data)
    print(f"[TG CALLBACK] verify_result={ok} bot_token_prefix={settings.TELEGRAM_BOT_TOKEN[:10] if settings.TELEGRAM_BOT_TOKEN else 'EMPTY'}")
    if not ok:
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        return RedirectResponse(f"{frontend_url}/login?error=telegram_auth_failed")

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
    redirect_response = RedirectResponse(
        f"{settings.FRONTEND_URL.rstrip('/')}/telegram-auth"
        f"?token={access}&is_new={'1' if is_new else '0'}"
    )
    _set_refresh_cookie(redirect_response, user.id)
    return redirect_response


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
    return await _me_full(db, user)


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
    return await _me_full(db, user)


@router.post("/vk/link-code")
async def vk_link_code(user: User = Depends(get_current_user)):
    """Issue a one-time code the user sends to the VK bot to link the account.
    The profile UI button calls this; the code is valid for 10 minutes."""
    from app.services.bot.state import create_link_code

    code = await create_link_code(user.id)
    bot_url = (
        f"https://vk.me/club{settings.VK_GROUP_ID}" if settings.VK_GROUP_ID else None
    )
    return {"code": code, "bot_url": bot_url}


@router.post("/me/avatar", response_model=MeResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and set a custom avatar (center-cropped to a 256×256 JPEG)."""
    import io
    import os
    import time

    from PIL import Image

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл не является изображением")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл больше 5 МБ")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = img.size
        m = min(w, h)
        left, top = (w - m) // 2, (h - m) // 2
        img = img.crop((left, top, left + m, top + m)).resize((256, 256))
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Не удалось обработать изображение")

    os.makedirs("media/avatars", exist_ok=True)
    img.save(f"media/avatars/{user.id}.jpg", "JPEG", quality=85)
    # Absolute URL on the public domain (Caddy already proxies /api → backend).
    # The ?v= cache-buster forces clients to reload the new image.
    base = settings.FRONTEND_URL.rstrip("/")
    user.avatar_url = f"{base}/api/v1/media/avatars/{user.id}.jpg?v={int(time.time())}"
    await db.commit()
    return await _me_full(db, user)
