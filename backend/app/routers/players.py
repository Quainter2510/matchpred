import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import Match, Prediction, RoomMember, SpecialPrediction, User
from app.schemas.player import PlayerProfile, PlayerProfileMatch
from app.services.recalc import room_multipliers_map
from app.services.simulation import (
    SimContext,
    effective_result,
    get_sim,
    points_for,
    room_sim_totals,
)
from app.services.tournament import tournament_match_conditions

router = APIRouter(prefix="/rooms/{room_id}/players", tags=["players"])


@router.get("/{uid}", response_model=PlayerProfile)
async def player_profile(
    uid: uuid.UUID,
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    room_id = ctx.room.id
    member = await db.get(RoomMember, (room_id, uid))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Player not in this room")
    target = await db.get(User, uid)

    sim_totals = await room_sim_totals(db, ctx.room, sim) if sim.active else None
    mults = await room_multipliers_map(db, room_id) if sim.active else {}

    # Place in the room standings (same ordering as the leaderboard).
    rows_order = (
        await db.execute(
            select(RoomMember, User.nickname)
            .join(User, User.id == RoomMember.user_id)
            .where(RoomMember.room_id == room_id)
            .order_by(
                RoomMember.total_points.desc(),
                RoomMember.exact_scores_count.desc(),
                User.nickname.asc(),
            )
        )
    ).all()
    if sim_totals is not None:
        rows_order = sorted(
            rows_order,
            key=lambda row: (
                -sim_totals.get(row[0].user_id, (0, 0))[0],
                -sim_totals.get(row[0].user_id, (0, 0))[1],
                row[1],
            ),
        )
    ordered = [m.user_id for m, _ in rows_order]
    place = ordered.index(uid) + 1 if uid in ordered else None

    # Reveal predictions only for started matches, unless it's the viewer's own
    # profile or the viewer is the superadmin. A room admin no longer sees
    # others' predictions before kickoff.
    is_self = uid == ctx.user.id
    reveal = is_self or ctx.is_superadmin
    now = sim.effective_now() if sim.active else datetime.now(timezone.utc)

    # Special predictions (champion / top scorer): shown only after the
    # tournament starts; the superadmin always.
    specials_revealed = ctx.is_superadmin or now >= ctx.room.first_match_at
    sp = await db.scalar(
        select(SpecialPrediction).where(
            SpecialPrediction.room_id == room_id,
            SpecialPrediction.user_id == uid,
        )
    )
    champion_team = sp.champion_team if (sp and specials_revealed) else None
    top_scorer_name = sp.top_scorer_name if (sp and specials_revealed) else None

    rows = (
        await db.execute(
            select(Match, Prediction)
            .outerjoin(
                Prediction,
                and_(
                    Prediction.match_id == Match.id,
                    Prediction.room_id == room_id,
                    Prediction.user_id == uid,
                ),
            )
            .where(*tournament_match_conditions(ctx.room))
            .order_by(Match.kickoff_at)
        )
    ).all()

    matches: list[PlayerProfileMatch] = []
    exact_count = diff_count = outcome_count = 0
    for m, pred in rows:
        started = now >= m.kickoff_at
        # In simulation the match state and points come from the overlay;
        # otherwise straight from the DB.
        if sim.active:
            eff_status, eff_home, eff_away = effective_result(m, sim)
            points, is_exact = (
                points_for(
                    pred.predicted_home, pred.predicted_away, m, ctx.room, sim,
                    mults.get(m.id, 1),
                )
                if pred is not None
                else (None, None)
            )
        else:
            eff_status, eff_home, eff_away = m.status, m.home_score_ft, m.away_score_ft
            points, is_exact = (
                (pred.points_awarded, pred.is_exact) if pred is not None else (None, None)
            )
        # Tally hit categories on finished, scored matches (room rules already
        # baked into points; here we just classify the prediction vs the result).
        if (
            pred is not None
            and points is not None
            and eff_home is not None
            and eff_away is not None
        ):
            pred_diff = pred.predicted_home - pred.predicted_away
            real_diff = eff_home - eff_away
            if is_exact:
                exact_count += 1
            elif pred_diff == real_diff:
                diff_count += 1
            elif (pred_diff > 0) == (real_diff > 0) and (pred_diff < 0) == (real_diff < 0):
                outcome_count += 1
        show = pred is not None and (started or reveal)
        matches.append(
            PlayerProfileMatch(
                match_id=m.id,
                match_date=m.match_date,
                kickoff_at=m.kickoff_at,
                stage=m.stage,
                group_name=m.group_name,
                home_team=m.home_team,
                away_team=m.away_team,
                status=eff_status,
                home_score_ft=eff_home,
                away_score_ft=eff_away,
                started=started,
                predicted_home=pred.predicted_home if show else None,
                predicted_away=pred.predicted_away if show else None,
                points_awarded=points,
                is_exact=is_exact,
            )
        )

    sim_total = sim_totals.get(uid, (0, 0)) if sim_totals is not None else None
    return PlayerProfile(
        user_id=target.id,
        nickname=target.nickname,
        avatar_url=target.avatar_url,
        place=place,
        total_points=sim_total[0] if sim_total is not None else member.total_points,
        exact_scores_count=(
            sim_total[1] if sim_total is not None else member.exact_scores_count
        ),
        diff_count=diff_count,
        outcome_count=outcome_count,
        is_self=is_self,
        specials_revealed=specials_revealed,
        first_match_at=ctx.room.first_match_at,
        champion_team=champion_team,
        top_scorer_name=top_scorer_name,
        matches=matches,
    )
