import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_player
from app.models import SpecialPrediction, TournamentMember, User
from app.redis_client import (
    LEADERBOARD_CACHE_KEY,
    LEADERBOARD_CACHE_TTL,
    redis_client,
)
from app.schemas.leaderboard import LeaderboardEntry, MyLeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


async def _compute(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(TournamentMember, User, SpecialPrediction)
            .join(User, User.id == TournamentMember.user_id)
            .outerjoin(SpecialPrediction, SpecialPrediction.user_id == User.id)
            .order_by(
                TournamentMember.total_points.desc(),
                TournamentMember.exact_scores_count.desc(),
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
            }
        )
    return entries


async def _get_leaderboard(db: AsyncSession) -> list[dict]:
    try:
        cached = await redis_client.get(LEADERBOARD_CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    entries = await _compute(db)
    try:
        await redis_client.setex(
            LEADERBOARD_CACHE_KEY, LEADERBOARD_CACHE_TTL, json.dumps(entries)
        )
    except Exception:
        pass
    return entries


@router.get("", response_model=list[LeaderboardEntry])
async def leaderboard(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    return await _get_leaderboard(db)


@router.get("/me", response_model=MyLeaderboardEntry | None)
async def leaderboard_me(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    entries = await _get_leaderboard(db)
    for e in entries:
        if e["user_id"] == str(user.id):
            return e
    return None
