"""Read queries used by the bot core. Transport-agnostic."""
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, Prediction, Room, RoomMember, User


async def active_rooms(db: AsyncSession, user_id) -> list[Room]:
    return list(
        (
            await db.execute(
                select(Room)
                .join(RoomMember, RoomMember.room_id == Room.id)
                .where(RoomMember.user_id == user_id, Room.is_active.is_(True))
                .order_by(Room.name)
            )
        ).scalars().all()
    )


async def leaderboard(db: AsyncSession, room_id) -> list[tuple[str, int]]:
    rows = (
        await db.execute(
            select(User.nickname, RoomMember.total_points)
            .join(User, User.id == RoomMember.user_id)
            .where(RoomMember.room_id == room_id)
            .order_by(
                RoomMember.total_points.desc(),
                RoomMember.exact_scores_count.desc(),
                User.nickname.asc(),
            )
        )
    ).all()
    return [(n, p) for n, p in rows]


async def days_with_matches(db: AsyncSession, start: date, end: date) -> list[date]:
    rows = (
        await db.execute(
            select(Match.match_date)
            .where(Match.match_date >= start, Match.match_date <= end)
            .group_by(Match.match_date)
            .order_by(Match.match_date)
        )
    ).all()
    return [r[0] for r in rows]


async def tour_player_points(
    db: AsyncSession, room_id, day: date
) -> list[tuple[str, int]]:
    """Per-player total points for a single match-day, all room members."""
    match_ids = select(Match.id).where(Match.match_date == day).scalar_subquery()
    total = func.coalesce(func.sum(Prediction.points_awarded), 0)
    rows = (
        await db.execute(
            select(User.nickname, total)
            .select_from(RoomMember)
            .join(User, User.id == RoomMember.user_id)
            .outerjoin(
                Prediction,
                and_(
                    Prediction.user_id == User.id,
                    Prediction.room_id == room_id,
                    Prediction.match_id.in_(match_ids),
                ),
            )
            .where(RoomMember.room_id == room_id)
            .group_by(User.id, User.nickname)
            .order_by(total.desc(), User.nickname.asc())
        )
    ).all()
    return [(n, int(p)) for n, p in rows]


async def tour_matches_for_user(
    db: AsyncSession, room_id, user_id, day: date
) -> list[tuple[Match, Prediction | None]]:
    rows = (
        await db.execute(
            select(Match, Prediction)
            .outerjoin(
                Prediction,
                and_(
                    Prediction.match_id == Match.id,
                    Prediction.room_id == room_id,
                    Prediction.user_id == user_id,
                ),
            )
            .where(Match.match_date == day)
            .order_by(Match.kickoff_at)
        )
    ).all()
    return [(m, p) for m, p in rows]


async def matches_of_day(db: AsyncSession, day: date) -> list[Match]:
    return list(
        (
            await db.execute(
                select(Match).where(Match.match_date == day).order_by(Match.kickoff_at)
            )
        ).scalars().all()
    )
