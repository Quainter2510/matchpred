"""Score recalculation. Side-effecting orchestration around the pure
scoring functions in scoring.py. Idempotent: already-scored rows are skipped.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Match,
    Prediction,
    SpecialPrediction,
    TournamentMember,
)
from app.redis_client import invalidate_leaderboard_cache
from app.services.scoring import (
    POINTS_CHAMPION,
    POINTS_TOP_SCORER,
    determine_winner,
    score_prediction,
)


async def _bump_member(db: AsyncSession, user_id: uuid.UUID, points: int, exact: int) -> None:
    member = await db.get(TournamentMember, user_id)
    if member:
        member.total_points += points
        member.exact_scores_count += exact


async def score_match(db: AsyncSession, match: Match) -> int:
    """Score all unscored predictions for a finished match. Returns count scored.
    Does NOT commit — caller owns the transaction."""
    if match.home_score_ft is None or match.away_score_ft is None:
        return 0

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
        points, is_exact = score_prediction(
            pred.predicted_home,
            pred.predicted_away,
            match.home_score_ft,
            match.away_score_ft,
        )
        pred.points_awarded = points
        pred.is_exact = is_exact
        await _bump_member(db, pred.user_id, points, 1 if is_exact else 0)
        scored += 1

    if scored:
        await invalidate_leaderboard_cache()
    return scored


async def recalculate_all(db: AsyncSession) -> dict:
    """Score every finished match with unscored predictions, plus champion
    points if the final is finished. Returns a summary dict."""
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
    final = next(
        (m for m in finished if m.stage == "final" or "final" == m.stage.lower()),
        None,
    )
    if not final or final.home_score_ft is None or final.away_score_ft is None:
        return 0
    winner = determine_winner(
        final.home_team, final.away_team, final.home_score_ft, final.away_score_ft
    )
    if not winner:
        return 0

    rows = (
        await db.execute(
            select(SpecialPrediction).where(
                SpecialPrediction.champion_points.is_(None)
            )
        )
    ).scalars().all()

    awarded = 0
    for sp in rows:
        pts = POINTS_CHAMPION if sp.champion_team == winner else 0
        sp.champion_points = pts
        if pts:
            await _bump_member(db, sp.user_id, pts, 0)
            awarded += 1
    if awarded:
        await invalidate_leaderboard_cache()
    return awarded


async def score_top_scorer(db: AsyncSession, player_api_id: int) -> int:
    """Award 10 points to everyone who picked the given top scorer."""
    rows = (
        await db.execute(
            select(SpecialPrediction).where(
                SpecialPrediction.scorer_points.is_(None)
            )
        )
    ).scalars().all()
    awarded = 0
    for sp in rows:
        pts = POINTS_TOP_SCORER if sp.top_scorer_api_id == player_api_id else 0
        sp.scorer_points = pts
        if pts:
            await _bump_member(db, sp.user_id, pts, 0)
            awarded += 1
    if awarded:
        await invalidate_leaderboard_cache()
    return awarded
