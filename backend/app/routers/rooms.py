import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    RoomContext,
    get_current_user,
    require_room_admin,
    require_room_member,
    require_superadmin,
)
from app.models import Match, Room, RoomMember, User
from app.redis_client import invalidate_leaderboard_cache
from app.schemas.room import (
    ParticipationUpdate,
    RoomArchiveUpdate,
    RoomCreate,
    RoomDetail,
    RoomJoinRequest,
    RoomMemberOut,
    RoomPasswordUpdate,
    RoomRoleUpdate,
    RoomRulesTextUpdate,
    RoomScoring,
    RoomSummary,
)
from app.security import hash_password, verify_password
from app.services import audit

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _member_count(db: AsyncSession, room_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count()).select_from(RoomMember).where(RoomMember.room_id == room_id)
    ) or 0


async def _my_role(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    member = await db.get(RoomMember, (room_id, user_id))
    return member.room_role if member else None


def _scoring(room: Room) -> RoomScoring:
    return RoomScoring(
        points_exact=room.points_exact,
        points_diff=room.points_diff,
        points_outcome=room.points_outcome,
        points_champion=room.points_champion,
        points_scorer=room.points_scorer,
    )


# ---------------- Create / delete (superadmin) ----------------
@router.post("", response_model=RoomDetail, status_code=201)
async def create_room(
    payload: RoomCreate,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    first_match_at = payload.first_match_at
    if first_match_at is None:
        first_match_at = await db.scalar(select(func.min(Match.kickoff_at)))
    if first_match_at is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No matches loaded yet — pass first_match_at explicitly.",
        )

    room = Room(
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        first_match_at=first_match_at,
        created_by=user.id,
    )
    db.add(room)
    await db.flush()
    # The creator is the room's first admin.
    db.add(RoomMember(room_id=room.id, user_id=user.id, room_role="admin"))
    await audit.log_event(
        db,
        "room_created",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=room.id,
        details={"name": room.name},
    )
    await db.commit()
    await db.refresh(room)
    return RoomDetail(
        id=room.id,
        name=room.name,
        member_count=1,
        is_member=True,
        is_active=room.is_active,
        my_role="admin",
        first_match_at=room.first_match_at,
        scoring=_scoring(room),
        rules_text=room.rules_text,
    )


@router.delete("/{room_id}")
async def delete_room(
    room_id: uuid.UUID,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    await db.delete(room)  # cascades to members/predictions/special_predictions
    await audit.log_event(
        db,
        "room_deleted",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=room_id,
        details={"name": room.name},
    )
    await db.commit()
    await invalidate_leaderboard_cache()
    return {"ok": True}


# ---------------- Browse / join ----------------
@router.get("", response_model=list[RoomSummary])
async def list_rooms(
    q: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All active rooms, optionally filtered by name. Used to find and join."""
    stmt = select(Room).where(Room.is_active.is_(True)).order_by(Room.name)
    if q:
        stmt = stmt.where(Room.name.ilike(f"%{q.strip()}%"))
    rooms = (await db.execute(stmt)).scalars().all()
    my = {
        m.room_id: m.room_role
        for m in (
            await db.execute(select(RoomMember).where(RoomMember.user_id == user.id))
        ).scalars().all()
    }
    out = []
    for r in rooms:
        out.append(
            RoomSummary(
                id=r.id,
                name=r.name,
                member_count=await _member_count(db, r.id),
                is_member=r.id in my,
                is_active=r.is_active,
                my_role=my.get(r.id),
            )
        )
    return out


@router.get("/my", response_model=list[RoomSummary])
async def my_rooms(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Room, RoomMember)
            .join(RoomMember, RoomMember.room_id == Room.id)
            .where(RoomMember.user_id == user.id)
            .order_by(Room.name)
        )
    ).all()
    out = []
    for room, member in rows:
        out.append(
            RoomSummary(
                id=room.id,
                name=room.name,
                member_count=await _member_count(db, room.id),
                is_member=True,
                is_active=room.is_active,
                my_role=member.room_role,
            )
        )
    return out


@router.post("/{room_id}/join", response_model=RoomSummary)
async def join_room(
    room_id: uuid.UUID,
    payload: RoomJoinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    room = await db.get(Room, room_id)
    if not room or not room.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")

    existing = await db.get(RoomMember, (room_id, user.id))
    if existing:
        return RoomSummary(
            id=room.id,
            name=room.name,
            member_count=await _member_count(db, room.id),
            is_member=True,
            is_active=room.is_active,
            my_role=existing.room_role,
        )

    # Superadmin joins any room without a password (as admin); others need it.
    if user.system_role == "superadmin":
        role = "admin"
    else:
        if not verify_password(payload.password, room.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")
        role = "player"

    db.add(RoomMember(room_id=room_id, user_id=user.id, room_role=role))
    await audit.log_event(
        db,
        "room_joined",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=room_id,
        details={"room": room.name},
    )
    await db.commit()
    await invalidate_leaderboard_cache(room_id)
    return RoomSummary(
        id=room.id,
        name=room.name,
        member_count=await _member_count(db, room.id),
        is_member=True,
        is_active=room.is_active,
        my_role=role,
    )


@router.get("/{room_id}", response_model=RoomDetail)
async def room_detail(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    room = ctx.room
    return RoomDetail(
        id=room.id,
        name=room.name,
        member_count=await _member_count(db, room.id),
        is_member=ctx.member is not None,
        is_active=room.is_active,
        my_role=ctx.member.room_role if ctx.member else None,
        first_match_at=room.first_match_at,
        total_points=ctx.member.total_points if ctx.member else None,
        scoring=_scoring(room),
        rules_text=room.rules_text,
    )


@router.patch("/{room_id}/archive")
async def archive_room(
    room_id: uuid.UUID,
    payload: RoomArchiveUpdate,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Archive (read-only, not scored) or restore a room. Superadmin only."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    room.is_active = not payload.archived
    await db.commit()
    return {"ok": True, "is_active": room.is_active}


@router.patch("/{room_id}/rules", response_model=RoomScoring)
async def update_rules(
    room_id: uuid.UUID,
    payload: RoomScoring,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Change a room's point values. Superadmin only. Applies to predictions
    scored after the change (already-scored predictions keep their points until
    a full recalculation, which the MVP does not reset)."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    room.points_exact = payload.points_exact
    room.points_diff = payload.points_diff
    room.points_outcome = payload.points_outcome
    room.points_champion = payload.points_champion
    room.points_scorer = payload.points_scorer
    await db.commit()
    return _scoring(room)


@router.patch("/{room_id}/rules-text")
async def update_rules_text(
    payload: RoomRulesTextUpdate,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    """Регламент соревнования (кнопка «i» у заголовка). Пустая строка
    сбрасывает к стандартному описанию очков."""
    text = payload.rules_text.strip() or None
    ctx.room.rules_text = text
    await audit.log_event(
        db,
        "room_rules_changed",
        actor_id=ctx.user.id,
        actor_nickname=ctx.user.nickname,
        target_id=ctx.room.id,
        details={"room": ctx.room.name, "length": len(text or "")},
    )
    await db.commit()
    return {"ok": True, "rules_text": text}


# ---------------- Members (room admin) ----------------
@router.get("/{room_id}/members", response_model=list[RoomMemberOut])
async def room_members(
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(RoomMember, User)
            .join(User, User.id == RoomMember.user_id)
            .where(RoomMember.room_id == ctx.room.id)
            .order_by(RoomMember.total_points.desc())
        )
    ).all()
    return [
        RoomMemberOut(
            user_id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            system_role=u.system_role,
            room_role=m.room_role,
            total_points=m.total_points,
            exact_scores_count=m.exact_scores_count,
            participation_confirmed=m.participation_confirmed,
        )
        for m, u in rows
    ]


@router.patch("/{room_id}/members/{uid}/role")
async def change_member_role(
    uid: uuid.UUID,
    payload: RoomRoleUpdate,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    member = await db.get(RoomMember, (ctx.room.id, uid))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    member.room_role = payload.role
    await audit.log_event(
        db,
        "role_changed",
        actor_id=ctx.user.id,
        actor_nickname=ctx.user.nickname,
        target_id=uid,
        details={"room_id": str(ctx.room.id), "role": payload.role},
    )
    await db.commit()
    return {"ok": True}


@router.patch("/{room_id}/members/{uid}/participation")
async def set_participation(
    uid: uuid.UUID,
    payload: ParticipationUpdate,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    member = await db.get(RoomMember, (ctx.room.id, uid))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    member.participation_confirmed = payload.confirmed
    await db.commit()
    return {"ok": True}


@router.delete("/{room_id}/members/{uid}")
async def remove_member(
    uid: uuid.UUID,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    member = await db.get(RoomMember, (ctx.room.id, uid))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    await db.delete(member)
    await audit.log_event(
        db,
        "member_removed",
        actor_id=ctx.user.id,
        actor_nickname=ctx.user.nickname,
        target_id=uid,
        details={"room_id": str(ctx.room.id)},
    )
    await db.commit()
    await invalidate_leaderboard_cache()
    return {"ok": True}


@router.patch("/{room_id}/password")
async def change_room_password(
    payload: RoomPasswordUpdate,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    ctx.room.password_hash = hash_password(payload.new_password)
    await audit.log_event(
        db,
        "room_password_changed",
        actor_id=ctx.user.id,
        actor_nickname=ctx.user.nickname,
        target_id=ctx.room.id,
    )
    await db.commit()
    return {"ok": True}
