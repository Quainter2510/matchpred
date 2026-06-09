import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_player
from app.models import Match, Prediction, User
from app.schemas.prediction import (
    MyPredictionOut,
    PredictionBatchRequest,
    PredictionBatchResponse,
    PredictionResult,
    TourPointsOut,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/batch", response_model=PredictionBatchResponse)
async def batch(
    payload: PredictionBatchRequest,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    match_ids = [p.match_id for p in payload.predictions]
    matches = {
        m.id: m
        for m in (
            await db.execute(select(Match).where(Match.id.in_(match_ids)))
        ).scalars().all()
    }
    existing = {
        p.match_id: p
        for p in (
            await db.execute(
                select(Prediction).where(
                    Prediction.user_id == user.id,
                    Prediction.match_id.in_(match_ids),
                )
            )
        ).scalars().all()
    }

    results: list[PredictionResult] = []
    for item in payload.predictions:
        match = matches.get(item.match_id)
        if not match:
            results.append(PredictionResult(match_id=item.match_id, accepted=False, reason="match_not_found"))
            continue
        # Deadline is enforced ONLY on the backend.
        if now >= match.kickoff_at:
            results.append(PredictionResult(match_id=item.match_id, accepted=False, reason="deadline_passed"))
            continue

        pred = existing.get(item.match_id)
        if pred:
            pred.predicted_home = item.home
            pred.predicted_away = item.away
        else:
            db.add(
                Prediction(
                    user_id=user.id,
                    match_id=item.match_id,
                    predicted_home=item.home,
                    predicted_away=item.away,
                )
            )
        results.append(PredictionResult(match_id=item.match_id, accepted=True))

    await db.commit()
    return PredictionBatchResponse(results=results)


@router.get("/my", response_model=list[MyPredictionOut])
async def my_predictions(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(select(Prediction).where(Prediction.user_id == user.id))
    ).scalars().all()
    return [
        MyPredictionOut(
            match_id=p.match_id,
            predicted_home=p.predicted_home,
            predicted_away=p.predicted_away,
            points_awarded=p.points_awarded,
            is_exact=p.is_exact,
        )
        for p in rows
    ]


@router.get("/tour/{tour_date}", response_model=TourPointsOut)
async def tour_points(
    tour_date: date,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Prediction)
            .join(Match, Match.id == Prediction.match_id)
            .where(Prediction.user_id == user.id, Match.match_date == tour_date)
        )
    ).scalars().all()
    points = sum(p.points_awarded or 0 for p in rows)
    exact = sum(1 for p in rows if p.is_exact)
    return TourPointsOut(date=tour_date, points=points, exact_count=exact)
