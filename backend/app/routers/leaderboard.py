import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import RoomMember, SpecialPrediction, User
from app.redis_client import (
    LEADERBOARD_CACHE_TTL,
    leaderboard_cache_key,
    redis_client,
)
from app.schemas.leaderboard import LeaderboardEntry, MyLeaderboardEntry

router = APIRouter(prefix="/rooms/{room_id}/leaderboard", tags=["leaderboard"])


async def _compute(db: AsyncSession, room_id, started: bool) -> list[dict]:
    rows = (
        await db.execute(
            select(RoomMember, User, SpecialPrediction)
            .join(User, User.id == RoomMember.user_id)
            .outerjoin(
                SpecialPrediction,
                (SpecialPrediction.user_id == User.id)
                & (SpecialPrediction.room_id == room_id),
            )
            .where(RoomMember.room_id == room_id)
            .order_by(
                RoomMember.total_points.desc(),
                RoomMember.exact_scores_count.desc(),
                User.nickname.asc(),
            )
        )
    ).all()
    entries = []
    for place, (m, u, sp) in enumerate(rows, start=1):
        entries.append(
            {
                "place": place,
                "user_id": str(u.id),
                "nickname": u.nickname,
                "avatar_url": u.avatar_url,
                "total_points": m.total_points,
                "exact_scores_count": m.exact_scores_count,
                "has_champion": bool(sp and sp.champion_team),
                "has_scorer": bool(sp and sp.top_scorer_api_id),
                "champion_correct": bool(sp and sp.champion_points),
                "scorer_correct": bool(sp and sp.scorer_points),
                "participation_confirmed": m.participation_confirmed,
                # Actual picks revealed only after the tournament starts.
                "champion_team": sp.champion_team if (started and sp) else None,
                "top_scorer_name": sp.top_scorer_name if (started and sp) else None,
            }
        )
    return entries


async def _get_leaderboard(db: AsyncSession, room_id, started: bool) -> list[dict]:
    key = leaderboard_cache_key(room_id)
    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    entries = await _compute(db, room_id, started)
    try:
        await redis_client.setex(key, LEADERBOARD_CACHE_TTL, json.dumps(entries))
    except Exception:
        pass
    return entries


def _started(ctx: RoomContext) -> bool:
    return bool(
        ctx.room.first_match_at
        and datetime.now(timezone.utc) >= ctx.room.first_match_at
    )


@router.get("", response_model=list[LeaderboardEntry])
async def leaderboard(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    return await _get_leaderboard(db, ctx.room.id, _started(ctx))


@router.get("/me", response_model=MyLeaderboardEntry | None)
async def leaderboard_me(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    entries = await _get_leaderboard(db, ctx.room.id, _started(ctx))
    for e in entries:
        if e["user_id"] == str(ctx.user.id):
            return e
    return None
