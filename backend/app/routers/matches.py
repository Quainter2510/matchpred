import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    RoomContext,
    require_any_admin,
    require_room_member,
)
from app.models import Match, Prediction, Room, RoomMember, User
from app.schemas.match import (
    MatchCreate,
    MatchDay,
    MatchOut,
    MatchResult,
    MatchUpdate,
    MultiplierUpdate,
    MyPrediction,
    PlayerPredictionOut,
)
from app.services import audit
from app.services.recalc import rescore_match, score_match
from app.services.simulation import SimContext, effective_result, get_sim, points_for

# Room-scoped match reads (attach the caller's prediction in this room).
room_router = APIRouter(prefix="/rooms/{room_id}/matches", tags=["matches"])
# Global match administration (results are shared across all rooms).
admin_router = APIRouter(prefix="/matches", tags=["matches-admin"])


async def _my_preds_map(
    db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID, match_ids: list[uuid.UUID]
) -> dict:
    if not match_ids:
        return {}
    rows = (
        await db.execute(
            select(Prediction).where(
                Prediction.room_id == room_id,
                Prediction.user_id == user_id,
                Prediction.match_id.in_(match_ids),
            )
        )
    ).scalars().all()
    return {p.match_id: p for p in rows}


def _to_out(
    match: Match,
    pred: Prediction | None,
    *,
    room: Room | None = None,
    sim: SimContext | None = None,
) -> MatchOut:
    out = MatchOut.model_validate(match)
    sim_active = sim is not None and sim.active
    if sim_active:
        out.status, out.home_score_ft, out.away_score_ft = effective_result(match, sim)
    if pred:
        if sim_active and room is not None:
            points, is_exact = points_for(
                pred.predicted_home, pred.predicted_away, match, room, sim
            )
        else:
            points, is_exact = pred.points_awarded, pred.is_exact
        out.my_prediction = MyPrediction(
            predicted_home=pred.predicted_home,
            predicted_away=pred.predicted_away,
            points_awarded=points,
            is_exact=is_exact,
        )
    return out


@room_router.get("/days", response_model=list[MatchDay])
async def match_days(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Match.match_date,
                func.count(),
                func.min(Match.kickoff_at),
                func.min(Match.points_multiplier),
                func.max(Match.points_multiplier),
            )
            .group_by(Match.match_date)
            .order_by(Match.match_date)
        )
    ).all()
    my = dict(
        (
            await db.execute(
                select(Match.match_date, func.count())
                .join(Prediction, Prediction.match_id == Match.id)
                .where(
                    Prediction.user_id == ctx.user.id,
                    Prediction.room_id == ctx.room.id,
                )
                .group_by(Match.match_date)
            )
        ).all()
    )
    return [
        MatchDay(
            date=d,
            match_count=c,
            my_predictions_count=my.get(d, 0),
            first_kickoff_at=first,
            multiplier=mn if mn == mx else None,
        )
        for d, c, first, mn, mx in rows
    ]


@room_router.get("", response_model=list[MatchOut])
async def matches_by_date(
    date: date_type,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    matches = (
        await db.execute(
            select(Match).where(Match.match_date == date).order_by(Match.kickoff_at)
        )
    ).scalars().all()
    preds = await _my_preds_map(db, ctx.room.id, ctx.user.id, [m.id for m in matches])
    return [_to_out(m, preds.get(m.id), room=ctx.room, sim=sim) for m in matches]


@room_router.get("/{match_id}", response_model=MatchOut)
async def match_detail(
    match_id: uuid.UUID,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    preds = await _my_preds_map(db, ctx.room.id, ctx.user.id, [match.id])
    return _to_out(match, preds.get(match.id), room=ctx.room, sim=sim)


@room_router.get("/{match_id}/predictions", response_model=list[PlayerPredictionOut])
async def match_predictions(
    match_id: uuid.UUID,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    now = sim.effective_now()
    if now < match.kickoff_at and not ctx.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Predictions hidden until kickoff"
        )

    rows = (
        await db.execute(
            select(Prediction, User)
            .join(User, User.id == Prediction.user_id)
            .where(
                Prediction.match_id == match_id,
                Prediction.room_id == ctx.room.id,
            )
        )
    ).all()
    out = []
    for p, u in rows:
        if sim.active:
            points, is_exact = points_for(
                p.predicted_home, p.predicted_away, match, ctx.room, sim
            )
        else:
            points, is_exact = p.points_awarded, p.is_exact
        out.append(
            PlayerPredictionOut(
                user_id=u.id,
                nickname=u.nickname,
                avatar_url=u.avatar_url,
                predicted_home=p.predicted_home,
                predicted_away=p.predicted_away,
                points_awarded=points,
                is_exact=is_exact,
            )
        )
    return out


# ---------------- Global admin (any room admin or superadmin) ----------------
@admin_router.get("", response_model=list[MatchOut])
async def admin_list_matches(
    date: date_type | None = None,
    user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Global match list for the admin panel (no room context, no my_prediction)."""
    stmt = select(Match).order_by(Match.kickoff_at)
    if date is not None:
        stmt = stmt.where(Match.match_date == date)
    matches = (await db.execute(stmt)).scalars().all()
    return [_to_out(m, None) for m in matches]


@admin_router.post("", response_model=MatchOut, status_code=201)
async def create_match(
    payload: MatchCreate,
    user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    match = Match(**payload.model_dump())
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return _to_out(match, None)


@admin_router.patch("/{match_id}", response_model=MatchOut)
async def update_match(
    match_id: uuid.UUID,
    payload: MatchUpdate,
    user: User = Depends(require_any_admin),
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


@admin_router.patch("/tour/{tour_date}/multiplier")
async def set_tour_multiplier(
    tour_date: date_type,
    payload: MultiplierUpdate,
    user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Бонусный коэффициент на весь тур (все матчи даты). Уже начисленные
    очки пересчитываются с новым коэффициентом."""
    matches = (
        await db.execute(select(Match).where(Match.match_date == tour_date))
    ).scalars().all()
    if not matches:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matches on this date")

    rescored = 0
    for match in matches:
        if match.points_multiplier == payload.multiplier:
            continue
        match.points_multiplier = payload.multiplier
        if match.status == "finished":
            await rescore_match(db, match)
            rescored += 1
    await audit.log_event(
        db,
        "multiplier_changed",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details={
            "tour": tour_date.isoformat(),
            "multiplier": payload.multiplier,
            "matches": len(matches),
            "rescored": rescored,
        },
    )
    await db.commit()
    return {"ok": True, "matches": len(matches), "rescored": rescored}


@admin_router.patch("/{match_id}/multiplier", response_model=MatchOut)
async def set_match_multiplier(
    match_id: uuid.UUID,
    payload: MultiplierUpdate,
    user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Бонусный коэффициент на отдельный матч (×0 / ×1 / ×2 / ×3)."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    if match.points_multiplier != payload.multiplier:
        match.points_multiplier = payload.multiplier
        if match.status == "finished":
            await rescore_match(db, match)
        await audit.log_event(
            db,
            "multiplier_changed",
            actor_id=user.id,
            actor_nickname=user.nickname,
            target_id=match.id,
            details={
                "match": f"{match.home_team} — {match.away_team}",
                "multiplier": payload.multiplier,
            },
        )
    await db.commit()
    await db.refresh(match)
    return _to_out(match, None)


@admin_router.post("/{match_id}/result", response_model=MatchOut)
async def set_result(
    match_id: uuid.UUID,
    payload: MatchResult,
    user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    had_result = (
        match.status == "finished"
        and match.home_score_ft is not None
        and match.away_score_ft is not None
    )
    prev = {"home": match.home_score_ft, "away": match.away_score_ft}
    score_changed = had_result and (
        prev["home"] != payload.home_score_ft or prev["away"] != payload.away_score_ft
    )
    match.home_score_ft = payload.home_score_ft
    match.away_score_ft = payload.away_score_ft
    match.status = "finished"

    # Scores every room's predictions for this match (results are global).
    # A corrected result takes back the old points and awards them anew.
    if score_changed:
        scored = await rescore_match(db, match)
    else:
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
