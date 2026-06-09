import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_superadmin
from app.models import (
    AuditLog,
    Match,
    Tournament,
    TournamentMember,
    User,
)
from app.redis_client import invalidate_leaderboard_cache
from app.schemas.admin import (
    AuditLogOut,
    MemberOut,
    PasswordUpdate,
    RoleUpdate,
    TransferRequest,
)
from app.schemas.special import ScorerResultRequest
from app.security import hash_password
from app.services import audit, football_api
from app.services.recalc import recalculate_all, score_top_scorer

router = APIRouter(tags=["admin"])


# ---------------- Sync & recalc ----------------
@router.post("/admin/sync")
async def sync_api(
    user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    try:
        fixtures = await football_api.fetch_fixtures()
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"API-Football error: {exc}")

    created, updated = 0, 0
    for fx in fixtures:
        existing = await db.scalar(
            select(Match).where(Match.api_football_id == fx["api_football_id"])
        )
        if existing:
            existing.kickoff_at = fx["kickoff_at"]
            existing.match_date = fx["match_date"]
            existing.stage = fx["stage"]
            existing.group_name = fx["group_name"]
            existing.home_team = fx["home_team"]
            existing.away_team = fx["away_team"]
            existing.status = fx["status"]
            if fx["status"] == "finished":
                existing.home_score_ft = fx["home_score_ft"]
                existing.away_score_ft = fx["away_score_ft"]
            updated += 1
        else:
            db.add(Match(**fx))
            created += 1

    await audit.log_event(
        db,
        "api_sync",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details={"created": created, "updated": updated},
    )
    await db.commit()
    # Recalculate after a sync may have brought finished results.
    summary = await recalculate_all(db)
    await db.commit()
    return {"created": created, "updated": updated, **summary}


@router.post("/admin/recalculate")
async def recalculate(
    user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    summary = await recalculate_all(db)
    await audit.log_event(
        db,
        "scores_recalculated",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details=summary,
    )
    await db.commit()
    return summary


@router.post("/admin/scorer-result")
async def scorer_result(
    payload: ScorerResultRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    awarded = await score_top_scorer(db, payload.player_api_id)
    await audit.log_event(
        db,
        "scorer_result_set",
        actor_id=user.id,
        actor_nickname=user.nickname,
        details={"player_api_id": payload.player_api_id, "player_name": payload.player_name, "awarded": awarded},
    )
    await db.commit()
    return {"awarded": awarded}


# ---------------- Members ----------------
@router.get("/admin/members", response_model=list[MemberOut])
async def members(
    user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(TournamentMember, User).join(User, User.id == TournamentMember.user_id)
        )
    ).all()
    return [
        MemberOut(
            user_id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            system_role=u.system_role,
            tournament_role=m.tournament_role,
            total_points=m.total_points,
            exact_scores_count=m.exact_scores_count,
        )
        for m, u in rows
    ]


@router.patch("/admin/members/{uid}/role")
async def change_role(
    uid: uuid.UUID,
    payload: RoleUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    member = await db.get(TournamentMember, uid)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    member.tournament_role = payload.role
    await audit.log_event(
        db,
        "role_changed",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=uid,
        details={"role": payload.role},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/admin/members/{uid}")
async def remove_member(
    uid: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    member = await db.get(TournamentMember, uid)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    await db.delete(member)
    await audit.log_event(
        db,
        "member_removed",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=uid,
    )
    await db.commit()
    await invalidate_leaderboard_cache()
    return {"ok": True}


# ---------------- Tournament password ----------------
@router.patch("/tournament/password")
async def change_password(
    payload: PasswordUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    tournament = await db.scalar(select(Tournament).limit(1))
    if not tournament:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tournament not configured")
    tournament.password_hash = hash_password(payload.new_password)
    await audit.log_event(
        db,
        "tournament_password_changed",
        actor_id=user.id,
        actor_nickname=user.nickname,
    )
    await db.commit()
    return {"ok": True}


# ---------------- Superadmin ----------------
@router.post("/admin/superadmin/transfer")
async def transfer_superadmin(
    payload: TransferRequest,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, payload.target_user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already superadmin")

    user.system_role = "user"
    target.system_role = "superadmin"
    await audit.log_event(
        db,
        "superadmin_transferred",
        actor_id=user.id,
        actor_nickname=user.nickname,
        target_id=target.id,
        details={"to_nickname": target.nickname},
    )
    await db.commit()
    return {"ok": True}


@router.get("/admin/audit-log", response_model=list[AuditLogOut])
async def audit_log(
    event_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    stmt = stmt.limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [AuditLogOut.model_validate(r, from_attributes=True) for r in rows]
