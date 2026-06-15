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

from app.models import (
    Match,
    Prediction,
    Room,
    RoomMatchMultiplier,
    RoomMember,
    SpecialPrediction,
)
from app.redis_client import invalidate_leaderboard_cache
from app.services.scoring import determine_winner, score_prediction


async def _rooms_map(db: AsyncSession) -> dict[uuid.UUID, Room]:
    rooms = (await db.execute(select(Room))).scalars().all()
    return {r.id: r for r in rooms}


async def match_multipliers_map(
    db: AsyncSession, match_id: uuid.UUID
) -> dict[uuid.UUID, int]:
    """room_id → коэффициент для матча (отсутствие строки = 1)."""
    rows = (
        await db.execute(
            select(RoomMatchMultiplier).where(
                RoomMatchMultiplier.match_id == match_id
            )
        )
    ).scalars().all()
    return {r.room_id: r.multiplier for r in rows}


async def room_multipliers_map(
    db: AsyncSession, room_id: uuid.UUID
) -> dict[uuid.UUID, int]:
    """match_id → коэффициент комнаты (отсутствие строки = 1)."""
    rows = (
        await db.execute(
            select(RoomMatchMultiplier).where(
                RoomMatchMultiplier.room_id == room_id
            )
        )
    ).scalars().all()
    return {r.match_id: r.multiplier for r in rows}


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
    # Live-матчи хранят текущий счёт в тех же колонках — очки начисляем
    # только когда матч завершён.
    if match.status != "finished":
        return 0
    if match.home_score_ft is None or match.away_score_ft is None:
        return 0

    rooms = await _rooms_map(db)
    mults = await match_multipliers_map(db, match.id)
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
        # Бонусный коэффициент комнаты для матча: ×2, ×3 или ×0 (аннулирование).
        # При ×0 точный счёт не идёт и в тайбрейк.
        multiplier = mults.get(pred.room_id, 1)
        points *= multiplier
        if multiplier == 0:
            is_exact = False
        pred.points_awarded = points
        pred.is_exact = is_exact
        await _bump_member(db, pred.room_id, pred.user_id, points, 1 if is_exact else 0)
        scored += 1

    if scored:
        await invalidate_leaderboard_cache()
    return scored


async def rescore_match(db: AsyncSession, match: Match) -> int:
    """Re-score a match whose final score changed after points were awarded:
    take back the previously awarded points, then score again with the new
    score. Archived rooms stay frozen (their points are neither taken back
    nor re-awarded)."""
    rooms = await _rooms_map(db)
    rows = (
        await db.execute(
            select(Prediction).where(
                Prediction.match_id == match.id,
                Prediction.points_awarded.is_not(None),
            )
        )
    ).scalars().all()

    reset = 0
    for pred in rows:
        room = rooms.get(pred.room_id)
        if not room or not room.is_active:
            continue
        await _bump_member(
            db,
            pred.room_id,
            pred.user_id,
            -(pred.points_awarded or 0),
            -1 if pred.is_exact else 0,
        )
        pred.points_awarded = None
        pred.is_exact = None
        reset += 1

    if reset:
        await invalidate_leaderboard_cache()
    return await score_match(db, match)


async def rescore_match_in_room(
    db: AsyncSession, match: Match, room_id: uuid.UUID
) -> int:
    """Пересчитать матч **только в одной комнате** — для смены коэффициента
    админом комнаты на завершённом матче. Снимает ранее начисленные очки этой
    комнаты, обнуляет их, затем `score_match` начисляет заново (он берёт только
    строки с points_awarded IS NULL, т.е. фактически лишь эту комнату).
    Архивная комната заморожена."""
    room = await db.get(Room, room_id)
    if not room or not room.is_active:
        return 0
    rows = (
        await db.execute(
            select(Prediction).where(
                Prediction.match_id == match.id,
                Prediction.room_id == room_id,
                Prediction.points_awarded.is_not(None),
            )
        )
    ).scalars().all()
    for pred in rows:
        await _bump_member(
            db,
            room_id,
            pred.user_id,
            -(pred.points_awarded or 0),
            -1 if pred.is_exact else 0,
        )
        pred.points_awarded = None
        pred.is_exact = None
    if rows:
        await invalidate_leaderboard_cache()
    return await score_match(db, match)


async def recalculate_all(db: AsyncSession) -> dict:
    finished = (
        await db.execute(
            select(Match).where(
                Match.status == "finished",
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
    # Чемпион — победитель финала при ЛЮБОМ исходе. Если основное время — ничья
    # (победа по пенальти/допвремени), берём явного победителя из winner_team
    # (из API-Football или указанного суперадмином). Прогнозы при этом по-
    # прежнему считаются по основному времени.
    winner = final.winner_team or determine_winner(
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


async def score_top_scorer(
    db: AsyncSession, room_id: uuid.UUID, player_api_id: int
) -> int:
    """Начислить очки за бомбардира **в одной комнате**: тем, кто угадал, —
    room.points_scorer, остальным 0. Идемпотентно (только scorer_points IS NULL).
    Комната определяет бомбардира самостоятельно."""
    room = await db.get(Room, room_id)
    if not room or not room.is_active:
        return 0
    rows = (
        await db.execute(
            select(SpecialPrediction).where(
                SpecialPrediction.room_id == room_id,
                SpecialPrediction.scorer_points.is_(None),
            )
        )
    ).scalars().all()
    awarded = 0
    for sp in rows:
        pts = room.points_scorer if sp.top_scorer_api_id == player_api_id else 0
        sp.scorer_points = pts
        if pts:
            await _bump_member(db, sp.room_id, sp.user_id, pts, 0)
            awarded += 1
    if awarded:
        await invalidate_leaderboard_cache()
    return awarded
