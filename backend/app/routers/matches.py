import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    RoomContext,
    require_any_admin,
    require_room_member,
)
from app.models import Match, Prediction, Room, RoomMember, TeamMatch, User
from app.schemas.match import (
    MatchCreate,
    MatchDay,
    MatchFormOut,
    MatchOut,
    MatchResult,
    MatchUpdate,
    MultiplierUpdate,
    MyPrediction,
    PlayerPredictionOut,
    TeamFormMatch,
)
from app.services import audit
from app.services.recalc import rescore_match, score_match
from app.services.simulation import SimContext, effective_result, get_sim, points_for
from app.services.tours import tour_date

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
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    """Туры (дни) с моими очками: my_points — сумма за завершённые матчи дня,
    finished_count позволяет фронту показать «тур ещё идёт». Админам комнаты
    дополнительно отдаётся, сколько участников заполнили все прогнозы дня."""
    matches = (
        await db.execute(select(Match).order_by(Match.kickoff_at))
    ).scalars().all()
    my_preds = {
        p.match_id: p
        for p in (
            await db.execute(
                select(Prediction).where(
                    Prediction.user_id == ctx.user.id,
                    Prediction.room_id == ctx.room.id,
                )
            )
        ).scalars().all()
    }

    # Заполняемость туров (только для админов): по каждому дню — сколько
    # участников комнаты дали прогноз на все матчи дня.
    members_total: int | None = None
    per_user_day: dict = {}  # (user_id, date) -> кол-во прогнозов
    if ctx.is_admin:
        member_ids = set(
            (
                await db.execute(
                    select(RoomMember.user_id).where(RoomMember.room_id == ctx.room.id)
                )
            ).scalars().all()
        )
        members_total = len(member_ids)
        match_dates = {m.id: m.match_date for m in matches}
        rows = (
            await db.execute(
                select(Prediction.user_id, Prediction.match_id).where(
                    Prediction.room_id == ctx.room.id
                )
            )
        ).all()
        for user_id, match_id in rows:
            if user_id not in member_ids:
                continue
            d = match_dates.get(match_id)
            if d is not None:
                key = (user_id, d)
                per_user_day[key] = per_user_day.get(key, 0) + 1

    days: dict = {}
    for m in matches:
        d = days.setdefault(
            m.match_date,
            {
                "count": 0,
                "mine": 0,
                "first": m.kickoff_at,  # matches идут по kickoff — первый и есть min
                "mult_min": m.points_multiplier,
                "mult_max": m.points_multiplier,
                "finished": 0,
                "points": 0,
            },
        )
        d["count"] += 1
        d["mult_min"] = min(d["mult_min"], m.points_multiplier)
        d["mult_max"] = max(d["mult_max"], m.points_multiplier)
        pred = my_preds.get(m.id)
        if pred:
            d["mine"] += 1

        if sim.active:
            status, home, away = effective_result(m, sim)
        else:
            status, home, away = m.status, m.home_score_ft, m.away_score_ft
        if status == "finished" and home is not None and away is not None:
            d["finished"] += 1
            if pred:
                if sim.active:
                    points, _ = points_for(
                        pred.predicted_home, pred.predicted_away, m, ctx.room, sim
                    )
                else:
                    points = pred.points_awarded
                d["points"] += points or 0

    out = []
    for date, d in sorted(days.items()):
        members_filled: int | None = None
        if ctx.is_admin and members_total is not None:
            members_filled = sum(
                1
                for (uid, day), n in per_user_day.items()
                if day == date and n >= d["count"]
            )
        out.append(
            MatchDay(
                date=date,
                match_count=d["count"],
                my_predictions_count=d["mine"],
                first_kickoff_at=d["first"],
                multiplier=d["mult_min"] if d["mult_min"] == d["mult_max"] else None,
                finished_count=d["finished"],
                my_points=d["points"],
                members_total=members_total,
                members_filled=members_filled,
            )
        )
    return out


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


FORM_LIMIT = 7
WC_LABEL = "ЧМ-2026"


async def _team_form(
    db: AsyncSession, team: str, exclude_match_id, sim: SimContext
) -> list[TeamFormMatch]:
    """Последние сыгранные матчи сборной: справочник team_matches (все турниры
    2026 года, собран разово скриптом) + завершённые матчи ЧМ из основной
    таблицы. Новые матчи ЧМ вытесняют старые сами собой — после турнира список
    замирает, досинхронизация не нужна."""
    out: list[TeamFormMatch] = []

    rows = (
        await db.execute(
            select(TeamMatch).where(
                (TeamMatch.home_team == team) | (TeamMatch.away_team == team)
            )
        )
    ).scalars().all()
    for tm in rows:
        if tm.status != "finished" or tm.home_score is None or tm.away_score is None:
            continue
        out.append(
            TeamFormMatch(
                kickoff_at=tm.kickoff_at,
                competition=tm.competition,
                home_team=tm.home_team,
                away_team=tm.away_team,
                home_score=tm.home_score,
                away_score=tm.away_score,
            )
        )

    wc = (
        await db.execute(
            select(Match).where((Match.home_team == team) | (Match.away_team == team))
        )
    ).scalars().all()
    for m in wc:
        if m.id == exclude_match_id:
            continue
        status_, home, away = (
            effective_result(m, sim)
            if sim.active
            else (m.status, m.home_score_ft, m.away_score_ft)
        )
        if status_ != "finished" or home is None or away is None:
            continue
        out.append(
            TeamFormMatch(
                kickoff_at=m.kickoff_at,
                competition=WC_LABEL,
                home_team=m.home_team,
                away_team=m.away_team,
                home_score=home,
                away_score=away,
            )
        )

    out.sort(key=lambda f: f.kickoff_at, reverse=True)
    return out[:FORM_LIMIT]


@room_router.get("/{match_id}/form", response_model=MatchFormOut)
async def match_form(
    match_id: uuid.UUID,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    """Форма обеих сборных для страницы прогноза (последние сыгранные матчи,
    не больше FORM_LIMIT на команду)."""
    match = await db.get(Match, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return MatchFormOut(
        home_team=match.home_team,
        away_team=match.away_team,
        home=await _team_form(db, match.home_team, match.id, sim),
        away=await _team_form(db, match.away_team, match.id, sim),
    )


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

    # Все участники комнаты: не сделавшие прогноз тоже в списке (поля null —
    # фронт показывает прочерки).
    rows = (
        await db.execute(
            select(RoomMember, User, Prediction)
            .join(User, User.id == RoomMember.user_id)
            .outerjoin(
                Prediction,
                and_(
                    Prediction.match_id == match_id,
                    Prediction.room_id == ctx.room.id,
                    Prediction.user_id == RoomMember.user_id,
                ),
            )
            .where(RoomMember.room_id == ctx.room.id)
        )
    ).all()
    out = []
    for _member, u, p in rows:
        if p is None:
            points, is_exact = None, None
        elif sim.active:
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
                predicted_home=p.predicted_home if p else None,
                predicted_away=p.predicted_away if p else None,
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
    data = payload.model_dump(exclude_unset=True)
    # Дата тура всегда производна от времени начала (тур = 10:00–10:00 МСК).
    data["match_date"] = tour_date(payload.kickoff_at)
    match = Match(**data)
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
    # Сдвиг времени начала переносит матч в тур по той же границе 10:00 МСК.
    if payload.kickoff_at is not None:
        match.match_date = tour_date(match.kickoff_at)
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
