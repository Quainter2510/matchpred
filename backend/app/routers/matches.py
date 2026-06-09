import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import is_admin_or_super, require_admin, require_player
from app.models import Match, Prediction, User
from app.schemas.match import (
    MatchCreate,
    MatchDay,
    MatchOut,
    MatchResult,
    MatchUpdate,
    MyPrediction,
    PlayerPredictionOut,
)
from app.services import audit
from app.services.recalc import score_match

router = APIRouter(tags=["matches"])


async def _my_preds_map(db: AsyncSession, user_id: uuid.UUID, match_ids: list[uuid.UUID]) -> dict:
    if not match_ids:
        return {}
    rows = (
        await db.execute(
            select(Prediction).where(
                Prediction.user_id == user_id,
                Prediction.match_id.in_(match_ids),
            )
        )
    ).scalars().all()
    return {p.match_id: p for p in rows}


def _to_out(match: Match, pred: Prediction | None) -> MatchOut:
    out = MatchOut.model_validate(match)
    if pred:
        out.my_prediction = MyPrediction(
            predicted_home=pred.predicted_home,
            predicted_away=pred.predicted_away,
            points_awarded=pred.points_awarded,
            is_exact=pred.is_exact,
        )
    return out


@router.get("/matches/days", response_model=list[MatchDay])
async def match_days(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    counts = (
        await db.execute(
            select(Match.match_date, func.count(), func.min(Match.kickoff_at))
            .group_by(Match.match_date)
            .order_by(Match.match_date)
        )
    ).all()

    my = dict(
        (
            await db.execute(
                select(Match.match_date, func.count())
                .join(Prediction, Prediction.match_id == Match.id)
                .where(Prediction.user_id == user.id)
                .group_by(Match.match_date)
            )
        ).all()
    )
    return [
        MatchDay(
            date=d,
            match_count=c,
            my_predictions_count=my.get(d, 0),
            first_kickoff_at=first_kickoff,
        )
        for d, c, first_kickoff in counts
    ]


@router.get("/matches", response_model=list[MatchOut])
async def matches_by_date(
    date: date,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    matches = (
        await db.execute(
            select(Match).where(Match.match_date == date).order_by(Match.kickoff_at)
        )
    ).scalars().all()
    preds = await _my_preds_map(db, user.id, [m.id for m in matches])
    return [_to_out(m, preds.get(m.id)) for m in matches]


@router.get("/matches/{match_id}", response_model=MatchOut)
async def match_detail(
    match_id: uuid.UUID,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    preds = await _my_preds_map(db, user.id, [match.id])
    return _to_out(match, preds.get(match.id))


@router.get("/matches/{match_id}/predictions", response_model=list[PlayerPredictionOut])
async def match_predictions(
    match_id: uuid.UUID,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    now = datetime.now(timezone.utc)
    if now < match.kickoff_at and not await is_admin_or_super(db, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Predictions hidden until kickoff"
        )

    rows = (
        await db.execute(
            select(Prediction, User)
            .join(User, User.id == Prediction.user_id)
            .where(Prediction.match_id == match_id)
        )
    ).all()
    return [
        PlayerPredictionOut(
            user_id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            predicted_home=p.predicted_home,
            predicted_away=p.predicted_away,
            points_awarded=p.points_awarded,
            is_exact=p.is_exact,
        )
        for p, u in rows
    ]


# ---------------- Admin ----------------
@router.post("/matches", response_model=MatchOut, status_code=201)
async def create_match(
    payload: MatchCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    match = Match(**payload.model_dump())
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return _to_out(match, None)


@router.patch("/matches/{match_id}", response_model=MatchOut)
async def update_match(
    match_id: uuid.UUID,
    payload: MatchUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    await db.commit()
    await db.refresh(match)
    return _to_out(match, None)


@router.post("/matches/{match_id}/result", response_model=MatchOut)
async def set_result(
    match_id: uuid.UUID,
    payload: MatchResult,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    had_result = match.home_score_ft is not None and match.away_score_ft is not None
    prev = {"home": match.home_score_ft, "away": match.away_score_ft}

    match.home_score_ft = payload.home_score_ft
    match.away_score_ft = payload.away_score_ft
    match.status = "finished"

    scored = await score_match(db, match)
    details = {
        "match": f"{match.home_team} — {match.away_team}",
        "home": payload.home_score_ft,
        "away": payload.away_score_ft,
        "scored": scored,
    }
    if had_result:
        details["previous"] = prev
    await audit.log_event(
        db,
        "match_result_updated" if had_result else "match_result_set",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=match.id,
        details=details,
    )
    await db.commit()
    await db.refresh(match)
    return _to_out(match, None)
