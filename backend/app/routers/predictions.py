from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import Match, Prediction
from app.schemas.prediction import (
    MyPredictionOut,
    PredictionBatchRequest,
    PredictionBatchResponse,
    PredictionResult,
    TourPointsOut,
)
from app.services.predictions import set_prediction
from app.services.simulation import SimContext, get_sim, points_for

router = APIRouter(prefix="/rooms/{room_id}/predictions", tags=["predictions"])


@router.post("/batch", response_model=PredictionBatchResponse)
async def batch(
    payload: PredictionBatchRequest,
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    if not ctx.room.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Room is archived")
    match_ids = [p.match_id for p in payload.predictions]
    matches = {
        m.id: m
        for m in (
            await db.execute(select(Match).where(Match.id.in_(match_ids)))
        ).scalars().all()
    }

    results: list[PredictionResult] = []
    for item in payload.predictions:
        match = matches.get(item.match_id)
        if not match:
            results.append(PredictionResult(match_id=item.match_id, accepted=False, reason="match_not_found"))
            continue
        accepted, reason = await set_prediction(
            db, room=ctx.room, user=ctx.user, match=match, home=item.home, away=item.away
        )
        results.append(PredictionResult(match_id=item.match_id, accepted=accepted, reason=reason))

    await db.commit()
    return PredictionBatchResponse(results=results)


@router.get("/my", response_model=list[MyPredictionOut])
async def my_predictions(
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Prediction, Match)
            .join(Match, Match.id == Prediction.match_id)
            .where(
                Prediction.room_id == ctx.room.id,
                Prediction.user_id == ctx.user.id,
            )
        )
    ).all()
    out = []
    for p, m in rows:
        if sim.active:
            points, is_exact = points_for(
                p.predicted_home, p.predicted_away, m, ctx.room, sim
            )
        else:
            points, is_exact = p.points_awarded, p.is_exact
        out.append(
            MyPredictionOut(
                match_id=p.match_id,
                predicted_home=p.predicted_home,
                predicted_away=p.predicted_away,
                points_awarded=points,
                is_exact=is_exact,
            )
        )
    return out


@router.get("/tour/{tour_date}", response_model=TourPointsOut)
async def tour_points(
    tour_date: date_type,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Prediction, Match)
            .join(Match, Match.id == Prediction.match_id)
            .where(
                Prediction.room_id == ctx.room.id,
                Prediction.user_id == ctx.user.id,
                Match.match_date == tour_date,
            )
        )
    ).all()
    if sim.active:
        points = exact = 0
        for p, m in rows:
            pts, is_exact = points_for(
                p.predicted_home, p.predicted_away, m, ctx.room, sim
            )
            points += pts or 0
            exact += 1 if is_exact else 0
    else:
        points = sum(p.points_awarded or 0 for p, _ in rows)
        exact = sum(1 for p, _ in rows if p.is_exact)
    return TourPointsOut(date=tour_date, points=points, exact_count=exact)
