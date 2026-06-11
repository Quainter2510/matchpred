from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, get_current_user, require_room_member
from app.models import SpecialPrediction, User
from app.schemas.special import (
    PlayerSearchItem,
    SpecialPredictionOut,
    SpecialPredictionPublic,
    SpecialPredictionUpdate,
)
from app.services import audit, football_api
from app.services.simulation import SimContext, get_sim

router = APIRouter(prefix="/rooms/{room_id}/special-prediction", tags=["special"])
players_router = APIRouter(tags=["players"])


def _locked(room, sim: SimContext | None = None) -> bool:
    now = sim.effective_now() if sim and sim.active else datetime.now(timezone.utc)
    return bool(room.first_match_at and now >= room.first_match_at)


@router.get("/my", response_model=SpecialPredictionOut)
async def my_special(
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    sp = await db.scalar(
        select(SpecialPrediction).where(
            SpecialPrediction.room_id == ctx.room.id,
            SpecialPrediction.user_id == ctx.user.id,
        )
    )
    locked = _locked(ctx.room, sim)
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


@router.put("", response_model=SpecialPredictionOut)
async def update_special(
    payload: SpecialPredictionUpdate,
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    if not ctx.room.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Room is archived")
    if _locked(ctx.room):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Special predictions locked")

    sp = await db.scalar(
        select(SpecialPrediction).where(
            SpecialPrediction.room_id == ctx.room.id,
            SpecialPrediction.user_id == ctx.user.id,
        )
    )
    prev_champion = sp.champion_team if sp else None
    prev_scorer = sp.top_scorer_api_id if sp else None
    if not sp:
        sp = SpecialPrediction(
            room_id=ctx.room.id, user_id=ctx.user.id, locked_at=ctx.room.first_match_at
        )
        db.add(sp)
    sp.champion_team = payload.champion_team
    sp.top_scorer_name = payload.top_scorer_name
    sp.top_scorer_api_id = payload.top_scorer_api_id
    sp.locked_at = ctx.room.first_match_at

    # Журнал: пишем только при реальном изменении выбора.
    if payload.champion_team and payload.champion_team != prev_champion:
        await audit.log_event(
            db,
            "champion_selected",
            actor_id=ctx.user.id,
            actor_nickname=ctx.user.nickname,
            target_id=ctx.user.id,
            details={"room_id": str(ctx.room.id), "champion": payload.champion_team},
        )
    if payload.top_scorer_api_id and payload.top_scorer_api_id != prev_scorer:
        await audit.log_event(
            db,
            "top_scorer_selected",
            actor_id=ctx.user.id,
            actor_nickname=ctx.user.nickname,
            target_id=ctx.user.id,
            details={
                "room_id": str(ctx.room.id),
                "player_api_id": payload.top_scorer_api_id,
                "player_name": payload.top_scorer_name,
            },
        )
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


@router.get("/all", response_model=list[SpecialPredictionPublic])
async def all_special(
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    if not _locked(ctx.room, sim) and not ctx.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Special predictions hidden until deadline"
        )
    rows = (
        await db.execute(
            select(SpecialPrediction, User)
            .join(User, User.id == SpecialPrediction.user_id)
            .where(SpecialPrediction.room_id == ctx.room.id)
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


@players_router.get("/players/search", response_model=list[PlayerSearchItem])
async def players_search(
    q: str = Query(min_length=3),
    user: User = Depends(get_current_user),
):
    try:
        results = await football_api.search_players(q)
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Player search unavailable")
    return [PlayerSearchItem(**r) for r in results if r.get("api_id")]
