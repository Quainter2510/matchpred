import csv
import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_superadmin
from app.models import AuditLog, User
from app.schemas.admin import AuditLogOut, TransferRequest
from app.services import audit, football_api
from app.services.recalc import recalculate_all
from app.services.sync import apply_fixtures

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
}


# ---------------- Sync & recalc (global; superadmin only) ----------------
@router.post("/admin/sync")
async def sync_api(
    user: User = Depends(require_superadmin), db: AsyncSession = Depends(get_db)
):
    try:
        fixtures = await football_api.fetch_fixtures()
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"API-Football error: {exc}")

    stats = await apply_fixtures(db, fixtures)
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
