"""Prediction write logic, shared by the REST API and the bots.

Keeping it here means the same deadline / archive / audit rules apply no matter
whether a prediction comes from the web app or a chat bot.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, Prediction, Room, User
from app.services import audit


async def set_prediction(
    db: AsyncSession,
    *,
    room: Room,
    user: User,
    match: Match,
    home: int,
    away: int,
) -> tuple[bool, str | None]:
    """Create or update one prediction. Returns (accepted, reason).

    Reasons: room_archived | deadline_passed | invalid_score. Does NOT commit —
    the caller owns the transaction.
    """
    if not room.is_active:
        return False, "room_archived"
    if not (0 <= home <= 20 and 0 <= away <= 20):
        return False, "invalid_score"
    # Deadline is enforced ONLY on the backend.
    if datetime.now(timezone.utc) >= match.kickoff_at:
        return False, "deadline_passed"

    pred = await db.scalar(
        select(Prediction).where(
            Prediction.room_id == room.id,
            Prediction.user_id == user.id,
            Prediction.match_id == match.id,
        )
    )
    match_label = f"{match.home_team} — {match.away_team}"
    if pred:
        if pred.predicted_home != home or pred.predicted_away != away:
            await audit.log_event(
                db,
                "prediction_updated",
                actor_id=user.id,
                actor_nickname=user.nickname,
                target_id=match.id,
                details={
                    "room_id": str(room.id),
                    "match": match_label,
                    "home": home,
                    "away": away,
                    "previous": {"home": pred.predicted_home, "away": pred.predicted_away},
                },
            )
        pred.predicted_home = home
        pred.predicted_away = away
    else:
        db.add(
            Prediction(
                room_id=room.id,
                user_id=user.id,
                match_id=match.id,
                predicted_home=home,
                predicted_away=away,
            )
        )
        await audit.log_event(
            db,
            "prediction_set",
            actor_id=user.id,
            actor_nickname=user.nickname,
            target_id=match.id,
            details={"room_id": str(room.id), "match": match_label, "home": home, "away": away},
        )
    return True, None
