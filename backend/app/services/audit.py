import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

# Allowed event types (kept here as the single source of truth).
EVENT_TYPES = {
    "user_registered",
    "superadmin_assigned",
    "superadmin_transferred",
    "role_changed",
    "member_removed",
    "match_result_set",
    "match_result_updated",
    "prediction_set",
    "prediction_updated",
    "scores_recalculated",
    "scorer_result_set",
    "champion_selected",
    "top_scorer_selected",
    "tournament_password_changed",
    "api_sync",
    "nickname_changed",
}


async def log_event(
    db: AsyncSession,
    event_type: str,
    *,
    actor_id: uuid.UUID | None = None,
    actor_nickname: str | None = None,
    target_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    """Append-only insert into audit_log. Never updates or deletes."""
    assert event_type in EVENT_TYPES, f"unknown event_type {event_type}"
    db.add(
        AuditLog(
            event_type=event_type,
            actor_id=actor_id,
            actor_nickname=actor_nickname,
            target_id=target_id,
            details=details,
        )
    )


async def log_match_result(
    db: AsyncSession,
    *,
    match_id: uuid.UUID,
    home_team: str,
    away_team: str,
    new_home: int | None,
    new_away: int | None,
    prev_home: int | None,
    prev_away: int | None,
    actor_id: uuid.UUID | None = None,
    actor_nickname: str | None = None,
) -> None:
    """Журнал добавления/изменения счёта при синхронизации.

    No-op, если счёта нет или он не изменился (чтобы не засорять журнал на
    каждом опросе API уже завершённых матчей).
    """
    if new_home is None or new_away is None:
        return
    had_result = prev_home is not None and prev_away is not None
    if had_result and prev_home == new_home and prev_away == new_away:
        return
    details: dict = {
        "match": f"{home_team} — {away_team}",
        "home": new_home,
        "away": new_away,
    }
    if had_result:
        details["previous"] = {"home": prev_home, "away": prev_away}
    await log_event(
        db,
        "match_result_updated" if had_result else "match_result_set",
        actor_id=actor_id,
        actor_nickname=actor_nickname,
        target_id=match_id,
        details=details,
    )
