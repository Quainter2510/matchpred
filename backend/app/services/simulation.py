"""Superadmin-only, read-only simulation ("what-if") mode.

Activated per request by the `X-Sim-Now` header (ISO-8601 datetime). Only a
superadmin gets an active context — for everyone else the header is silently
ignored. With simulation active, read endpoints present the system as it
would look at the simulated moment:

- a match that has kicked off by sim_now but has no real final score gets a
  deterministic fake one (derived from the match id, stable across requests);
- points are recomputed in memory with the room's rules and the match
  multiplier — nothing is written to the database, the audit log or the
  leaderboard cache;
- write requests carrying the header are rejected by middleware (main.py),
  so a superadmin browsing the simulated world cannot mutate real data.

Champion/top-scorer points are NOT simulated (bracket teams are unknown in
advance) — already-awarded special points from the DB are kept as-is.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.models import Match, Prediction, Room, SpecialPrediction, User
from app.services.scoring import score_prediction

SIM_HEADER = "X-Sim-Now"


@dataclass(frozen=True)
class SimContext:
    now: datetime | None = None

    @property
    def active(self) -> bool:
        return self.now is not None

    def effective_now(self) -> datetime:
        return self.now or datetime.now(timezone.utc)


def parse_sim_now(raw: str | None) -> datetime | None:
    """ISO-8601 → aware UTC datetime; garbage silently deactivates the mode."""
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def get_sim(
    request: Request, user: User = Depends(get_current_user)
) -> SimContext:
    if user.system_role != "superadmin":
        return SimContext()
    return SimContext(now=parse_sim_now(request.headers.get(SIM_HEADER)))


def fake_score(match_id: uuid.UUID) -> tuple[int, int]:
    """Deterministic pseudo-random final score for a match without a real
    result, so the simulated world is stable between requests."""
    n = match_id.int
    return (n >> 8) % 4, (n >> 16) % 4


def effective_result(match: Match, sim: SimContext) -> tuple[str, int | None, int | None]:
    """(status, home_ft, away_ft) at the simulated moment.

    A real final score always wins. A match that has kicked off by sim_now
    becomes 'finished': a live match's current score is taken as final, a
    scheduled one gets a fake score. Matches kicking off after sim_now are
    returned unchanged.
    """
    if not sim.active or match.kickoff_at > sim.now:
        return match.status, match.home_score_ft, match.away_score_ft
    if match.home_score_ft is not None and match.away_score_ft is not None:
        return "finished", match.home_score_ft, match.away_score_ft
    home, away = fake_score(match.id)
    return "finished", home, away


def points_for(
    predicted_home: int,
    predicted_away: int,
    match: Match,
    room: Room,
    sim: SimContext,
) -> tuple[int | None, bool | None]:
    """Points a prediction earns at the simulated moment (None while the match
    is unfinished in the simulated world). Mirrors recalc.score_match: room
    rules, then the match multiplier; ×0 voids the exact-score tiebreak."""
    status, home, away = effective_result(match, sim)
    if status != "finished" or home is None or away is None:
        return None, None
    points, is_exact = score_prediction(
        predicted_home,
        predicted_away,
        home,
        away,
        points_exact=room.points_exact,
        points_diff=room.points_diff,
        points_outcome=room.points_outcome,
    )
    points *= match.points_multiplier
    if match.points_multiplier == 0:
        is_exact = False
    return points, is_exact


async def room_sim_totals(
    db: AsyncSession, room: Room, sim: SimContext
) -> dict[uuid.UUID, tuple[int, int]]:
    """user_id → (total_points, exact_count) recomputed for the simulated
    moment: every prediction in the room is scored against effective results;
    special points already awarded in the DB are added on top."""
    matches = {
        m.id: m for m in (await db.execute(select(Match))).scalars().all()
    }
    preds = (
        await db.execute(select(Prediction).where(Prediction.room_id == room.id))
    ).scalars().all()

    totals: dict[uuid.UUID, list[int]] = {}
    for p in preds:
        match = matches.get(p.match_id)
        if not match:
            continue
        points, is_exact = points_for(
            p.predicted_home, p.predicted_away, match, room, sim
        )
        if points is None:
            continue
        acc = totals.setdefault(p.user_id, [0, 0])
        acc[0] += points
        acc[1] += 1 if is_exact else 0

    specials = (
        await db.execute(
            select(SpecialPrediction).where(SpecialPrediction.room_id == room.id)
        )
    ).scalars().all()
    for sp in specials:
        bonus = (sp.champion_points or 0) + (sp.scorer_points or 0)
        if bonus:
            acc = totals.setdefault(sp.user_id, [0, 0])
            acc[0] += bonus

    return {uid: (t[0], t[1]) for uid, t in totals.items()}
