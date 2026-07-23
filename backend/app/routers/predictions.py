import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import Match, Prediction, RoomMember, User
from app.schemas.prediction import (
    AdminPredictionSet,
    MyPredictionOut,
    PredictionBatchRequest,
    PredictionBatchResponse,
    PredictionResult,
    TourPlayerMatch,
    TourPlayerOut,
    TourPointsOut,
)
from app.services.predictions import admin_set_prediction, set_prediction
from app.services.recalc import room_multipliers_map, score_match
from app.services.simulation import SimContext, effective_result, get_sim, points_for
from app.services.tournament import match_belongs, tournament_match_conditions

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
        # Матч должен входить в этот турнир — иначе прогноз на чужую лигу.
        if not match or not match_belongs(ctx.room, match):
            results.append(PredictionResult(match_id=item.match_id, accepted=False, reason="match_not_found"))
            continue
        accepted, reason = await set_prediction(
            db, room=ctx.room, user=ctx.user, match=match, home=item.home, away=item.away
        )
        results.append(PredictionResult(match_id=item.match_id, accepted=accepted, reason=reason))

    await db.commit()
    return PredictionBatchResponse(results=results)


@router.put("/{match_id}/users/{user_id}")
async def admin_set_user_prediction(
    match_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: AdminPredictionSet,
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    """Суперадмин задаёт/правит прогноз участника даже после дедлайна —
    если участник не успел проставить счёт вовремя. Работает и после
    завершения матча: очки снимаются и начисляются заново по новому прогнозу."""
    if not ctx.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superadmin access required")

    match = await db.get(Match, match_id)
    if not match or not match_belongs(ctx.room, match):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    member = await db.get(RoomMember, (ctx.room.id, user_id))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a room member")
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    accepted, reason = await admin_set_prediction(
        db,
        room=ctx.room,
        actor=ctx.user,
        target=target,
        match=match,
        home=payload.home,
        away=payload.away,
    )
    if not accepted:
        raise HTTPException(status.HTTP_409_CONFLICT, reason)
    # Матч уже завершён — сразу начисляем очки по новому прогнозу (старые
    # сняты внутри admin_set_prediction).
    if match.status == "finished":
        await score_match(db, match)
    await db.commit()
    return {"ok": True}


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
    mults = await room_multipliers_map(db, ctx.room.id) if sim.active else {}
    out = []
    for p, m in rows:
        if sim.active:
            points, is_exact = points_for(
                p.predicted_home, p.predicted_away, m, ctx.room, sim, mults.get(m.id, 1)
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
        mults = await room_multipliers_map(db, ctx.room.id)
        points = exact = 0
        for p, m in rows:
            pts, is_exact = points_for(
                p.predicted_home, p.predicted_away, m, ctx.room, sim, mults.get(m.id, 1)
            )
            points += pts or 0
            exact += 1 if is_exact else 0
    else:
        points = sum(p.points_awarded or 0 for p, _ in rows)
        exact = sum(1 for p, _ in rows if p.is_exact)
    return TourPointsOut(date=tour_date, points=points, exact_count=exact)


@router.get("/tour/{tour_date}/all", response_model=list[TourPlayerOut])
async def tour_leaderboard(
    tour_date: date_type,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    """Итоги тура: все участники комнаты с очками за завершённые матчи дня
    (пропущенный прогноз = 0 очков) и раскрывающимся списком матчей.
    Чужие прогнозы на не начавшиеся матчи скрыты (predicted_* = null);
    свои — видны всегда, чужие раскрывает только суперадмин. Сортировка: очки → точные → ник."""
    matches = (
        await db.execute(
            select(Match)
            .where(Match.match_date == tour_date, *tournament_match_conditions(ctx.room))
            .order_by(Match.kickoff_at)
        )
    ).scalars().all()

    preds: dict = {}  # (user_id, match_id) -> Prediction
    if matches:
        rows = (
            await db.execute(
                select(Prediction).where(
                    Prediction.room_id == ctx.room.id,
                    Prediction.match_id.in_([m.id for m in matches]),
                )
            )
        ).scalars().all()
        preds = {(p.user_id, p.match_id): p for p in rows}

    members = (
        await db.execute(
            select(RoomMember, User)
            .join(User, User.id == RoomMember.user_id)
            .where(RoomMember.room_id == ctx.room.id)
        )
    ).all()

    mults = await room_multipliers_map(db, ctx.room.id) if sim.active else {}
    now = sim.effective_now()
    out = []
    for member, user in members:
        points = exact = predicted = 0
        items: list[TourPlayerMatch] = []
        for m in matches:
            p = preds.get((user.id, m.id))
            if p is not None:
                predicted += 1
            if sim.active:
                status_, home, away = effective_result(m, sim)
            else:
                status_, home, away = m.status, m.home_score_ft, m.away_score_ft
            started = m.kickoff_at <= now
            # Чужой прогноз до начала матча скрыт. Раскрывает только суперадмин;
            # админ комнаты такой привилегии больше не имеет.
            visible = p is not None and (
                started or user.id == ctx.user.id or ctx.is_superadmin
            )
            pts = is_exact = None
            if p is not None:
                if sim.active:
                    pts, is_exact = points_for(
                        p.predicted_home, p.predicted_away, m, ctx.room, sim,
                        mults.get(m.id, 1),
                    )
                else:
                    pts, is_exact = p.points_awarded, p.is_exact
                points += pts or 0
                exact += 1 if is_exact else 0
            items.append(
                TourPlayerMatch(
                    match_id=m.id,
                    kickoff_at=m.kickoff_at,
                    home_team=m.home_team,
                    away_team=m.away_team,
                    status=status_,
                    home_score=home,
                    away_score=away,
                    started=started,
                    predicted_home=p.predicted_home if visible else None,
                    predicted_away=p.predicted_away if visible else None,
                    points_awarded=pts if visible else None,
                    is_exact=is_exact if visible else None,
                )
            )
        out.append(
            TourPlayerOut(
                user_id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
                points=points,
                exact_count=exact,
                predictions_count=predicted,
                match_count=len(matches),
                matches=items,
            )
        )
    out.sort(key=lambda t: (-t.points, -t.exact_count, t.nickname.lower()))
    return out
