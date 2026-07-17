"""Prediction write logic, shared by the REST API and the bots.

Keeping it here means the same deadline / archive / audit rules apply no matter
whether a prediction comes from the web app or a chat bot.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, Prediction, Room, RoomMember, User
from app.redis_client import invalidate_leaderboard_cache
from app.services import audit


async def admin_set_prediction(
    db: AsyncSession,
    *,
    room: Room,
    actor: User,
    target: User,
    match: Match,
    home: int,
    away: int,
) -> tuple[bool, str | None]:
    """Суперадмин задаёт/правит прогноз другого участника БЕЗ проверки
    дедлайна — на случай, когда участник не успел проставить счёт вовремя.

    Работает и после завершения матча: ранее начисленные очки снимаются с
    участника, и прогноз начисляется заново по новому счёту (score_match ниже
    по вызову — в роутере). Does NOT commit.
    Reasons: room_archived | invalid_score.
    """
    if not room.is_active:
        return False, "room_archived"
    if not (0 <= home <= 20 and 0 <= away <= 20):
        return False, "invalid_score"

    pred = await db.scalar(
        select(Prediction).where(
            Prediction.room_id == room.id,
            Prediction.user_id == target.id,
            Prediction.match_id == match.id,
        )
    )

    # Прогноз уже был начислен (матч завершён) — снимаем старые очки, чтобы
    # score_match начислил заново по новому прогнозу.
    if pred is not None and pred.points_awarded is not None:
        member = await db.get(RoomMember, (room.id, target.id))
        if member:
            member.total_points -= pred.points_awarded or 0
            if pred.is_exact:
                member.exact_scores_count -= 1
        pred.points_awarded = None
        pred.is_exact = None
        await invalidate_leaderboard_cache()

    match_label = f"{match.home_team} — {match.away_team}"
    details = {
        "room_id": str(room.id),
        "match": match_label,
        "home": home,
        "away": away,
        "admin_override": True,
        "for_user": str(target.id),
        "for_nickname": target.nickname,
    }
    if pred is not None:
        if pred.predicted_home != home or pred.predicted_away != away:
            details["previous"] = {
                "home": pred.predicted_home,
                "away": pred.predicted_away,
            }
            await audit.log_event(
                db,
                "prediction_updated",
                actor_id=actor.id,
                actor_nickname=actor.nickname,
                target_id=match.id,
                details=details,
            )
        pred.predicted_home = home
        pred.predicted_away = away
    else:
        db.add(
            Prediction(
                room_id=room.id,
                user_id=target.id,
                match_id=match.id,
                predicted_home=home,
                predicted_away=away,
            )
        )
        await audit.log_event(
            db,
            "prediction_set",
            actor_id=actor.id,
            actor_nickname=actor.nickname,
            target_id=match.id,
            details=details,
        )
    return True, None


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
