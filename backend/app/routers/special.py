from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import is_admin_or_super, require_player
from app.models import SpecialPrediction, Tournament, User
from app.schemas.special import (
    PlayerSearchItem,
    SpecialPredictionOut,
    SpecialPredictionPublic,
    SpecialPredictionUpdate,
)
from app.services import football_api

router = APIRouter(tags=["special"])


async def _deadline(db: AsyncSession) -> datetime | None:
    t = await db.scalar(select(Tournament).limit(1))
    return t.first_match_at if t else None


@router.get("/special-prediction/my", response_model=SpecialPredictionOut)
async def my_special(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    sp = await db.scalar(
        select(SpecialPrediction).where(SpecialPrediction.user_id == user.id)
    )
    deadline = await _deadline(db)
    locked = bool(deadline and datetime.now(timezone.utc) >= deadline)
    if not sp:
        return SpecialPredictionOut(locked=locked)
    return SpecialPredictionOut(
        champion_team=sp.champion_team,
        top_scorer_name=sp.top_scorer_name,
        top_scorer_api_id=sp.top_scorer_api_id,
        champion_points=sp.champion_points,
        scorer_points=sp.scorer_points,
        locked=locked,
    )


@router.put("/special-prediction", response_model=SpecialPredictionOut)
async def update_special(
    payload: SpecialPredictionUpdate,
    user: User = Depends(require_player),
    db: AsyncSession = Depends(get_db),
):
    deadline = await _deadline(db)
    now = datetime.now(timezone.utc)
    if deadline and now >= deadline:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Special predictions locked")

    sp = await db.scalar(
        select(SpecialPrediction).where(SpecialPrediction.user_id == user.id)
    )
    if not sp:
        sp = SpecialPrediction(user_id=user.id, locked_at=deadline)
        db.add(sp)
    sp.champion_team = payload.champion_team
    sp.top_scorer_name = payload.top_scorer_name
    sp.top_scorer_api_id = payload.top_scorer_api_id
    sp.locked_at = deadline
    await db.commit()
    await db.refresh(sp)
    return SpecialPredictionOut(
        champion_team=sp.champion_team,
        top_scorer_name=sp.top_scorer_name,
        top_scorer_api_id=sp.top_scorer_api_id,
        champion_points=sp.champion_points,
        scorer_points=sp.scorer_points,
        locked=False,
    )


@router.get("/special-prediction/all", response_model=list[SpecialPredictionPublic])
async def all_special(
    user: User = Depends(require_player), db: AsyncSession = Depends(get_db)
):
    deadline = await _deadline(db)
    now = datetime.now(timezone.utc)
    visible = (deadline and now >= deadline) or await is_admin_or_super(db, user)
    if not visible:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Special predictions hidden until deadline"
        )
    rows = (
        await db.execute(
            select(SpecialPrediction, User).join(User, User.id == SpecialPrediction.user_id)
        )
    ).all()
    return [
        SpecialPredictionPublic(
            user_id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            champion_team=sp.champion_team,
            top_scorer_name=sp.top_scorer_name,
            champion_points=sp.champion_points,
            scorer_points=sp.scorer_points,
        )
        for sp, u in rows
    ]


@router.get("/players/search", response_model=list[PlayerSearchItem])
async def players_search(
    q: str = Query(min_length=3),
    user: User = Depends(require_player),
):
    try:
        results = await football_api.search_players(q)
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Player search unavailable")
    return [PlayerSearchItem(**r) for r in results if r.get("api_id")]
