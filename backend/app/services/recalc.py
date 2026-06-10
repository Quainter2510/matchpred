"""Score recalculation across all rooms.

A match result is a shared global fact, so scoring a finished match updates the
predictions and member totals in every (active) room at once. Each room applies
its own point values. Archived rooms (is_active=False) are skipped — their
standings stay frozen. Pure scoring logic lives in scoring.py; this module is
the side-effecting orchestration. Idempotent: already-scored rows are skipped.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, Prediction, Room, RoomMember, SpecialPrediction
from app.redis_client import invalidate_leaderboard_cache
from app.services.scoring import determine_winner, score_prediction


async def _rooms_map(db: AsyncSession) -> dict[uuid.UUID, Room]:
    rooms = (await db.execute(select(Room))).scalars().all()
    return {r.id: r for r in rooms}


async def _bump_member(
    db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID, points: int, exact: int
) -> None:
    member = await db.get(RoomMember, (room_id, user_id))
    if member:
        member.total_points += points
        member.exact_scores_count += exact


async def score_match(db: AsyncSession, match: Match) -> int:
    """Score all unscored predictions for a finished match, in every active
    room, using that room's point rules. Returns the number scored."""
    if match.home_score_ft is None or match.away_score_ft is None:
        return 0

    rooms = await _rooms_map(db)
    rows = (
        await db.execute(
            select(Prediction).where(
                Prediction.match_id == match.id,
                Prediction.points_awarded.is_(None),
            )
        )
    ).scalars().all()

    scored = 0
    for pred in rows:
        room = rooms.get(pred.room_id)
        if not room or not room.is_active:
            continue  # archived/orphan rooms are not updated
        points, is_exact = score_prediction(
            pred.predicted_home,
            pred.predicted_away,
            match.home_score_ft,
            match.away_score_ft,
            points_exact=room.points_exact,
            points_diff=room.points_diff,
            points_outcome=room.points_outcome,
        )
        pred.points_awarded = points
        pred.is_exact = is_exact
        await _bump_member(db, pred.room_id, pred.user_id, points, 1 if is_exact else 0)
        scored += 1

    if scored:
        await invalidate_leaderboard_cache()
    return scored


async def recalculate_all(db: AsyncSession) -> dict:
    finished = (
        await db.execute(
            select(Match).where(
                Match.home_score_ft.is_not(None),
                Match.away_score_ft.is_not(None),
            )
        )
    ).scalars().all()

    total_predictions = 0
    for match in finished:
        total_predictions += await score_match(db, match)

    champions = await _score_champion(db, finished)

    return {
        "predictions_scored": total_predictions,
        "champion_awarded": champions,
    }


async def _score_champion(db: AsyncSession, finished: list[Match]) -> int:
    final = next((m for m in finished if "final" == (m.stage or "").lower()), None)
    if not final or final.home_score_ft is None or final.away_score_ft is None:
        return 0
    winner = determine_winner(
        final.home_team, final.away_team, final.home_score_ft, final.away_score_ft
    )
    if not winner:
        return 0

    rooms = await _rooms_map(db)
    rows = (
        await db.execute(
            select(SpecialPrediction).where(SpecialPrediction.champion_points.is_(None))
        )
    ).scalars().all()

    awarded = 0
    for sp in rows:
        room = rooms.get(sp.room_id)
        if not room or not room.is_active:
            continue
        pts = room.points_champion if sp.champion_team == winner else 0
        sp.champion_points = pts
        if pts:
            await _bump_member(db, sp.room_id, sp.user_id, pts, 0)
            awarded += 1
    if awarded:
        await invalidate_leaderboard_cache()
    return awarded


async def score_top_scorer(db: AsyncSession, player_api_id: int) -> int:
    """Award each active room's scorer points to whoever picked the top scorer."""
    rooms = await _rooms_map(db)
    rows = (
        await db.execute(
            select(SpecialPrediction).where(SpecialPrediction.scorer_points.is_(None))
        )
    ).scalars().all()
    awarded = 0
    for sp in rows:
        room = rooms.get(sp.room_id)
        if not room or not room.is_active:
            continue
        pts = room.points_scorer if sp.top_scorer_api_id == player_api_id else 0
        sp.scorer_points = pts
        if pts:
            await _bump_member(db, sp.room_id, sp.user_id, pts, 0)
            awarded += 1
    if awarded:
        await invalidate_leaderboard_cache()
    return awarded
