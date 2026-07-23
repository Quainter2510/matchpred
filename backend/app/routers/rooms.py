import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import (
    RoomContext,
    get_current_user,
    get_current_user_optional,
    require_room_admin,
    require_room_member,
    require_superadmin,
)
from app.models import (
    Match,
    Prediction,
    Room,
    RoomMember,
    SpecialPrediction,
    TournamentMatch,
    User,
)
from app.redis_client import invalidate_leaderboard_cache
from app.schemas.match import MatchOut
from app.schemas.room import (
    CustomLeagueOut,
    CustomMatchAdd,
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
    RoundOut,
    TournamentTypeOut,
)
from app.security import hash_password, verify_password
from app.services import audit, football_api
from app.services.tournament import CUSTOM_LEAGUES, TYPE_CONFIG

router = APIRouter(prefix="/rooms", tags=["rooms"])


def _summary(room: Room, *, member_count: int, is_member: bool, my_role: str | None) -> RoomSummary:
    return RoomSummary(
        id=room.id,
        name=room.name,
        member_count=member_count,
        is_member=is_member,
        is_active=room.is_active,
        my_role=my_role,
        tournament_type=room.tournament_type,
        special_kind=room.special_kind,
    )


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


def _detail(room: Room, *, member_count: int, is_member: bool, my_role: str | None,
            total_points: int | None = None) -> RoomDetail:
    return RoomDetail(
        id=room.id,
        name=room.name,
        member_count=member_count,
        is_member=is_member,
        is_active=room.is_active,
        my_role=my_role,
        tournament_type=room.tournament_type,
        special_kind=room.special_kind,
        first_match_at=room.first_match_at,
        total_points=total_points,
        scoring=_scoring(room),
        rules_text=room.rules_text,
        league_id=room.league_id,
        season=room.season,
        starts_on=room.starts_on,
        ends_on=room.ends_on,
        special_result_team=room.special_result_team,
    )


# ---------------- Tournament types & rounds (superadmin, для панели создания) ----------------
# Объявлены ДО GET /{room_id}, иначе статический путь перехватит {room_id}.
@router.get("/tournament-types", response_model=list[TournamentTypeOut])
async def tournament_types(user: User = Depends(require_superadmin)):
    return [
        TournamentTypeOut(
            id=key,
            label=cfg["label"],
            special_kind=cfg["special_kind"],
            has_league=cfg["league_id"] is not None,
            # Сезон выбирает админ у лиговых типов, кроме ЧМ (там сезон один).
            needs_season=cfg["league_id"] is not None and key != "world_cup",
        )
        for key, cfg in TYPE_CONFIG.items()
    ]


@router.get("/custom-leagues", response_model=list[CustomLeagueOut])
async def custom_leagues(user: User = Depends(require_superadmin)):
    """Лиги, доступные для выбора матчей в кастомном турнире (топ-5+РПЛ+ЛЧ)."""
    return [CustomLeagueOut(id=lid, label=label) for lid, label in CUSTOM_LEAGUES]


@router.get("/available-rounds", response_model=list[RoundOut])
async def available_rounds(
    type: str,
    season: int,
    user: User = Depends(require_superadmin),
):
    """Туры реальной лиги с датами — для выбора длительности «с тура по тур».
    Данные берутся напрямую из API-Football (не из БД)."""
    cfg = TYPE_CONFIG.get(type)
    if not cfg or cfg["league_id"] is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Тип турнира не привязан к одной лиге"
        )
    try:
        rounds = await football_api.fetch_rounds(cfg["league_id"], season)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"API-Football error: {exc}")
    return [RoundOut(**r) for r in rounds]


# ---------------- Create / delete (superadmin) ----------------
@router.post("", response_model=RoomDetail, status_code=201)
async def create_room(
    payload: RoomCreate,
    user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    cfg = TYPE_CONFIG.get(payload.tournament_type)
    if not cfg:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неизвестный тип турнира")
    league_id = cfg["league_id"]

    season = payload.season
    if payload.tournament_type == "world_cup" and season is None:
        season = settings.API_FOOTBALL_SEASON
    if league_id is not None and season is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Для этого типа турнира требуется сезон"
        )

    # Дедлайн спецпрогноза = первый матч окна турнира. Если фронт не передал —
    # берём минимальный kickoff среди уже загруженных матчей этого турнира.
    first_match_at = payload.first_match_at
    if first_match_at is None and league_id is not None:
        stmt = select(func.min(Match.kickoff_at)).where(Match.league_id == league_id)
        if season is not None:
            stmt = stmt.where(Match.season == season)
        if payload.starts_on is not None:
            stmt = stmt.where(Match.match_date >= payload.starts_on)
        if payload.ends_on is not None:
            stmt = stmt.where(Match.match_date <= payload.ends_on)
        first_match_at = await db.scalar(stmt)
    # Custom: матчи выбираются позже вручную; дедлайна спецпрогноза нет
    # (special_kind='none'). Ставим плейсхолдер, пересчитываемый при добавлении
    # матчей (см. _recompute_first_match_at).
    if first_match_at is None and payload.tournament_type == "custom":
        first_match_at = datetime(2100, 1, 1, tzinfo=timezone.utc)
    if first_match_at is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Матчи турнира ещё не загружены — синхронизируйте лигу или передайте "
            "first_match_at явно.",
        )

    room = Room(
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        first_match_at=first_match_at,
        created_by=user.id,
        tournament_type=payload.tournament_type,
        league_id=league_id,
        season=season,
        tour_anchor=cfg["tour_anchor"],
        special_kind=cfg["special_kind"],
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
    )
    if payload.scoring:
        room.points_exact = payload.scoring.points_exact
        room.points_diff = payload.scoring.points_diff
        room.points_outcome = payload.scoring.points_outcome
        room.points_champion = payload.scoring.points_champion
        room.points_scorer = payload.scoring.points_scorer
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
        details={"name": room.name, "type": room.tournament_type, "season": season},
    )
    await db.commit()
    await db.refresh(room)
    return _detail(room, member_count=1, is_member=True, my_role="admin")


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
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """All active rooms, optionally filtered by name. Public: the lobby is
    visible without login; joining requires auth."""
    stmt = select(Room).where(Room.is_active.is_(True)).order_by(Room.name)
    if q:
        stmt = stmt.where(Room.name.ilike(f"%{q.strip()}%"))
    rooms = (await db.execute(stmt)).scalars().all()
    my: dict = {}
    if user:
        my = {
            m.room_id: m.room_role
            for m in (
                await db.execute(select(RoomMember).where(RoomMember.user_id == user.id))
            ).scalars().all()
        }
    out = []
    for r in rooms:
        out.append(
            _summary(
                r,
                member_count=await _member_count(db, r.id),
                is_member=r.id in my,
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
            _summary(
                room,
                member_count=await _member_count(db, room.id),
                is_member=True,
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
        return _summary(
            room,
            member_count=await _member_count(db, room.id),
            is_member=True,
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
    return _summary(
        room,
        member_count=await _member_count(db, room.id),
        is_member=True,
        my_role=role,
    )


@router.get("/{room_id}", response_model=RoomDetail)
async def room_detail(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    room = ctx.room
    return _detail(
        room,
        member_count=await _member_count(db, room.id),
        is_member=ctx.member is not None,
        my_role=ctx.member.room_role if ctx.member else None,
        total_points=ctx.member.total_points if ctx.member else None,
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
    # Прогнозы и спецпрогноз выбывшего в этой комнате тоже удаляем — иначе они
    # остаются «осиротевшими» в БД и продолжают всплывать в списках.
    await db.execute(
        delete(Prediction).where(
            Prediction.room_id == ctx.room.id, Prediction.user_id == uid
        )
    )
    await db.execute(
        delete(SpecialPrediction).where(
            SpecialPrediction.room_id == ctx.room.id, SpecialPrediction.user_id == uid
        )
    )
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


# ---------------- Custom tournament: match selection (room admin) ----------------
_FAR_FUTURE = datetime(2100, 1, 1, tzinfo=timezone.utc)


async def _recompute_first_match_at(db: AsyncSession, room: Room) -> None:
    """Дедлайн/старт кастомного турнира = первый матч из выбранных (плейсхолдер,
    если матчей ещё нет)."""
    earliest = await db.scalar(
        select(func.min(Match.kickoff_at))
        .select_from(TournamentMatch)
        .join(Match, Match.id == TournamentMatch.match_id)
        .where(TournamentMatch.room_id == room.id)
    )
    room.first_match_at = earliest or _FAR_FUTURE


@router.get("/{room_id}/custom-candidates", response_model=list[MatchOut])
async def custom_candidates(
    league_id: int,
    season: int,
    start: date | None = None,
    end: date | None = None,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    """Матчи лиги/сезона в окне дат — кандидаты для добавления в кастомный
    турнир. Матчи должны быть предварительно синхронизированы (POST
    /admin/sync-league)."""
    if ctx.room.tournament_type != "custom":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Только для кастомного турнира")
    stmt = (
        select(Match)
        .where(Match.league_id == league_id, Match.season == season)
        .order_by(Match.kickoff_at)
    )
    if start is not None:
        stmt = stmt.where(Match.match_date >= start)
    if end is not None:
        stmt = stmt.where(Match.match_date <= end)
    matches = (await db.execute(stmt)).scalars().all()
    return [MatchOut.model_validate(m) for m in matches]


@router.get("/{room_id}/custom-matches", response_model=list[MatchOut])
async def custom_matches(
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    """Матчи, уже включённые в кастомный турнир."""
    matches = (
        await db.execute(
            select(Match)
            .join(TournamentMatch, TournamentMatch.match_id == Match.id)
            .where(TournamentMatch.room_id == ctx.room.id)
            .order_by(Match.kickoff_at)
        )
    ).scalars().all()
    return [MatchOut.model_validate(m) for m in matches]


@router.post("/{room_id}/custom-matches")
async def add_custom_match(
    payload: CustomMatchAdd,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.room.tournament_type != "custom":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Только для кастомного турнира")
    match = await db.get(Match, payload.match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    existing = await db.get(TournamentMatch, (ctx.room.id, match.id))
    if not existing:
        db.add(TournamentMatch(room_id=ctx.room.id, match_id=match.id))
        await _recompute_first_match_at(db, ctx.room)
    await db.commit()
    return {"ok": True}


@router.delete("/{room_id}/custom-matches/{match_id}")
async def remove_custom_match(
    match_id: uuid.UUID,
    ctx: RoomContext = Depends(require_room_admin),
    db: AsyncSession = Depends(get_db),
):
    if ctx.room.tournament_type != "custom":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Только для кастомного турнира")
    row = await db.get(TournamentMatch, (ctx.room.id, match_id))
    if row:
        await db.delete(row)
    # Удаляем прогнозы этого матча в комнате; уже начисленные очки снимаем с
    # участников — иначе останутся «осиротевшие» очки за исключённый матч.
    preds = (
        await db.execute(
            select(Prediction).where(
                Prediction.room_id == ctx.room.id, Prediction.match_id == match_id
            )
        )
    ).scalars().all()
    for p in preds:
        if p.points_awarded is not None:
            member = await db.get(RoomMember, (ctx.room.id, p.user_id))
            if member:
                member.total_points -= p.points_awarded or 0
                if p.is_exact:
                    member.exact_scores_count -= 1
        await db.delete(p)
    await _recompute_first_match_at(db, ctx.room)
    await db.commit()
    await invalidate_leaderboard_cache(ctx.room.id)
    return {"ok": True}
