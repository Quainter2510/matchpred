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
