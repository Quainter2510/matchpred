import csv
import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_superadmin
from app.models import AuditLog, OAuthAccount, User
from app.schemas.admin import (
    AdminUserOut,
    AuditLogOut,
    LoginLinkOut,
    SyncLeagueRequest,
    TransferRequest,
    VkLinkCodeOut,
)
from app.services import audit
from app.services.bot.state import create_link_code
from app.services.login_links import LOGIN_LINK_TTL, create_login_token
from app.services.logos import download_missing_logos
from app.services.recalc import recalculate_all
from app.services.sync import fetch_and_apply_all, sync_league
from app.services.top_scorers import refresh_all_top_scorers

router = APIRouter(tags=["admin"])

# Русские названия событий для выгрузки журнала (синхронно с фронтом).
EVENT_LABELS_RU = {
    "user_registered": "Регистрация",
    "superadmin_assigned": "Назначен суперадмин",
    "superadmin_transferred": "Передана роль суперадмина",
    "role_changed": "Изменена роль",
    "member_removed": "Удалён участник",
    "match_result_set": "Добавлен счёт",
    "match_result_updated": "Изменён счёт",
    "multiplier_changed": "Изменён коэффициент",
    "prediction_set": "Сделан прогноз",
    "prediction_updated": "Изменён прогноз",
    "scores_recalculated": "Пересчёт очков",
    "scorer_result_set": "Итоговый бомбардир (начисление)",
    "leader_result_set": "Итоговый лидер лиги (начисление)",
    "champion_selected": "Выбран чемпион",
    "top_scorer_selected": "Выбран бомбардир",
    "tournament_password_changed": "Смена пароля турнира",
    "room_created": "Создана комната",
    "room_deleted": "Удалена комната",
    "room_joined": "Вход в комнату",
    "room_password_changed": "Смена пароля комнаты",
    "room_rules_changed": "Изменён регламент",
    "api_sync": "Синхронизация с API",
    "nickname_changed": "Смена никнейма",
    "account_linked": "Привязан аккаунт",
    "login_link_issued": "Выдана ссылка входа",
    "login_link_used": "Вход по одноразовой ссылке",
    "vk_link_code_issued": "Выдан код привязки VK",
}

# Код привязки VK, выданный суперадмином, передаётся лично — живёт дольше
# обычного (10 минут из профиля).
ADMIN_VK_CODE_TTL = 3600


# ---------------- Sync & recalc (global; superadmin only) ----------------
@router.post("/admin/sync")
async def sync_api(
    user: User = Depends(require_superadmin), db: AsyncSession = Depends(get_db)
):
    try:
        stats = await fetch_and_apply_all(db, with_groups=True)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"API-Football error: {exc}")

    await audit.log_event(
        db,
        "api_sync",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details=stats,
    )
    await db.commit()
    summary = await recalculate_all(db)
    await db.commit()
    # Логотипы всех новых команд.
    try:
        logos = await download_missing_logos(db)
        await db.commit()
    except Exception:
        logos = 0
    # Обновляем снимки бомбардиров (не критично для синка — глушим ошибки).
    try:
        scorers = await refresh_all_top_scorers()
    except Exception:
        scorers = 0
    return {**stats, **summary, "logos": logos, "top_scorers": scorers}


@router.post("/admin/sync-league")
async def sync_league_endpoint(
    payload: SyncLeagueRequest,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Синхронизировать одну лигу/сезон в БД — для панели выбора матчей
    кастомного турнира (подтянуть фикстуры до выбора)."""
    try:
        stats = await sync_league(db, payload.league_id, payload.season)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"API-Football error: {exc}")
    await audit.log_event(
        db,
        "api_sync",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details={**stats, "league_id": payload.league_id, "season": payload.season},
    )
    await db.commit()
    summary = await recalculate_all(db)
    await db.commit()
    return {**stats, **summary}


@router.post("/admin/recalculate")
async def recalculate(
    user: User = Depends(require_superadmin), db: AsyncSession = Depends(get_db)
):
    summary = await recalculate_all(db)
    await audit.log_event(
        db,
        "scores_recalculated",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details=summary,
    )
    await db.commit()
    return summary


# ---------------- Superadmin ----------------
@router.post("/admin/superadmin/transfer")
async def transfer_superadmin(
    payload: TransferRequest,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, payload.target_user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already superadmin")

    user.system_role = "user"
    target.system_role = "superadmin"
    await audit.log_event(
        db,
        "superadmin_transferred",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=target.id,
        details={"to_nickname": target.nickname},
    )
    await db.commit()
    return {"ok": True}


# ---------------- Users: запасной вход и привязка VK (superadmin) ----------------
@router.get("/admin/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    limit: int = Query(200, le=500),
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Все пользователи (поиск по никнейму) с привязанными провайдерами."""
    stmt = select(User).order_by(User.nickname).limit(limit)
    if q and q.strip():
        stmt = stmt.where(User.nickname.ilike(f"%{q.strip()}%"))
    users = (await db.execute(stmt)).scalars().all()
    providers: dict[uuid.UUID, set[str]] = {}
    if users:
        rows = (
            await db.execute(
                select(OAuthAccount.user_id, OAuthAccount.provider).where(
                    OAuthAccount.user_id.in_([u.id for u in users])
                )
            )
        ).all()
        for uid, provider in rows:
            providers.setdefault(uid, set()).add(provider)
    return [
        AdminUserOut(
            id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            system_role=u.system_role,
            is_active=u.is_active,
            created_at=u.created_at,
            providers=sorted(providers.get(u.id, ())),
        )
        for u in users
    ]


async def _target_user(db: AsyncSession, uid: uuid.UUID) -> User:
    target = await db.get(User, uid)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not target.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пользователь отключён")
    return target


@router.post("/admin/users/{uid}/login-link", response_model=LoginLinkOut)
async def issue_login_link(
    uid: uuid.UUID,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Одноразовая ссылка входа в аккаунт пользователя — суперадмин передаёт
    её лично. Действует час, гасится при первом входе."""
    target = await _target_user(db, uid)
    token = await create_login_token(target.id)
    await audit.log_event(
        db,
        "login_link_issued",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=target.id,
        details={"for_nickname": target.nickname},
    )
    await db.commit()
    frontend = settings.FRONTEND_URL.rstrip("/")
    return LoginLinkOut(
        url=f"{frontend}/auth/one-time#token={token}", expires_in=LOGIN_LINK_TTL
    )


@router.post("/admin/users/{uid}/vk-link-code", response_model=VkLinkCodeOut)
async def issue_vk_link_code(
    uid: uuid.UUID,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Код привязки VK-бота для пользователя — суперадмин передаёт его лично,
    пользователь отправляет код боту. Действует час (обычный код из профиля —
    10 минут), одноразовый."""
    target = await _target_user(db, uid)
    already = await db.scalar(
        select(OAuthAccount.id).where(
            OAuthAccount.user_id == target.id, OAuthAccount.provider == "vk"
        )
    )
    code = await create_link_code(target.id, ttl=ADMIN_VK_CODE_TTL)
    await audit.log_event(
        db,
        "vk_link_code_issued",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=target.id,
        details={"for_nickname": target.nickname},
    )
    await db.commit()
    return VkLinkCodeOut(
        code=code,
        bot_url=f"https://vk.me/club{settings.VK_GROUP_ID}" if settings.VK_GROUP_ID else None,
        expires_in=ADMIN_VK_CODE_TTL,
        already_linked=already is not None,
    )


@router.get("/admin/audit-log", response_model=list[AuditLogOut])
async def audit_log(
    event_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    stmt = stmt.limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [AuditLogOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/admin/audit-log/export")
async def export_audit_log(
    event_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Выгрузка всего журнала (с учётом фильтров) в CSV-файл."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    rows = (await db.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Время (UTC)", "Инициатор", "Событие", "Код", "Объект", "Детали"])
    for r in rows:
        writer.writerow(
            [
                r.created_at.isoformat() if r.created_at else "",
                r.actor_nickname or "система",
                EVENT_LABELS_RU.get(r.event_type, r.event_type),
                r.event_type,
                str(r.target_id) if r.target_id else "",
                json.dumps(r.details, ensure_ascii=False) if r.details else "",
            ]
        )

    # BOM, чтобы Excel корректно прочитал кириллицу в UTF-8.
    content = chr(0xFEFF) + buf.getvalue()
    filename = f"audit-log-{datetime.now(timezone.utc):%Y%m%d-%H%M}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
