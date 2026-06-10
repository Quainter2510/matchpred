import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import Match, Prediction, RoomMember, SpecialPrediction, User
from app.schemas.player import PlayerProfile, PlayerProfileMatch

router = APIRouter(prefix="/rooms/{room_id}/players", tags=["players"])


@router.get("/{uid}", response_model=PlayerProfile)
async def player_profile(
    uid: uuid.UUID,
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    room_id = ctx.room.id
    member = await db.get(RoomMember, (room_id, uid))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Player not in this room")
    target = await db.get(User, uid)

    # Place in the room standings (same ordering as the leaderboard).
    ordered = (
        await db.execute(
            select(RoomMember.user_id)
            .join(User, User.id == RoomMember.user_id)
            .where(RoomMember.room_id == room_id)
            .order_by(
                RoomMember.total_points.desc(),
                RoomMember.exact_scores_count.desc(),
                User.nickname.asc(),
            )
        )
    ).scalars().all()
    place = ordered.index(uid) + 1 if uid in ordered else None

    # Reveal predictions only for started matches, unless it's the viewer's own
    # profile or the viewer is a room admin.
    is_self = uid == ctx.user.id
    reveal = is_self or ctx.is_admin
    now = datetime.now(timezone.utc)

    # Special predictions (champion / top scorer): shown only after the
    # tournament starts; admins always.
    specials_revealed = ctx.is_admin or now >= ctx.room.first_match_at
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
            .order_by(Match.kickoff_at)
        )
    ).all()

    matches: list[PlayerProfileMatch] = []
    for m, pred in rows:
        started = now >= m.kickoff_at
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
                status=m.status,
                home_score_ft=m.home_score_ft,
                away_score_ft=m.away_score_ft,
                started=started,
                predicted_home=pred.predicted_home if show else None,
                predicted_away=pred.predicted_away if show else None,
                points_awarded=pred.points_awarded if pred else None,
                is_exact=pred.is_exact if pred else None,
            )
        )

    return PlayerProfile(
        user_id=target.id,
        nickname=target.nickname,
        avatar_url=target.avatar_url,
        place=place,
        total_points=member.total_points,
        exact_scores_count=member.exact_scores_count,
        is_self=is_self,
        specials_revealed=specials_revealed,
        first_match_at=ctx.room.first_match_at,
        champion_team=champion_team,
        top_scorer_name=top_scorer_name,
        matches=matches,
    )
