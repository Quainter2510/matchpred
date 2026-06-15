"""Турнирное положение ЧМ-2026: таблицы групп и сетка плей-офф.

Считается из глобальных матчей (общие для всех комнат), поэтому ответ одинаков
в любой комнате; room-scoped путь нужен только для единообразия доступа.
Уважает режим симуляции: в нём результаты берутся из оверлея (фейковые счета),
а очки/разница считаются только по завершённым (в т.ч. симулированно) матчам.
"""
import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RoomContext, require_room_member
from app.models import Match, SpecialPrediction
from app.schemas.standings import (
    GroupStanding,
    GroupTeamRow,
    PlayoffStage,
    PredictedScorer,
    StandingsMatch,
    StandingsOut,
    TopScorer,
    TopScorersOut,
)
from app.services.simulation import SimContext, effective_result, get_sim
from app.services.top_scorers import get_snapshot

router = APIRouter(prefix="/rooms/{room_id}/standings", tags=["standings"])

GROUP_RE = re.compile(r"group", re.I)
# Буква группы из кода стадии: "group_a_-_1" → "a".
LETTER_FROM_STAGE = re.compile(r"group[_\s-]*([a-l])\b", re.I)


def _group_letter(match: Match) -> str | None:
    raw = (match.group_name or "").strip()
    if re.fullmatch(r"[A-Za-z0-9]{1,3}", raw):
        return raw.upper()
    found = LETTER_FROM_STAGE.search(match.stage or "")
    return found.group(1).upper() if found else None


def _blank_stats() -> dict:
    return {"played": 0, "goals_for": 0, "goals_against": 0, "points": 0}


@router.get("", response_model=StandingsOut)
async def standings(
    ctx: RoomContext = Depends(require_room_member),
    sim: SimContext = Depends(get_sim),
    db: AsyncSession = Depends(get_db),
):
    matches = (
        await db.execute(select(Match).order_by(Match.kickoff_at))
    ).scalars().all()

    groups: dict[str, dict] = {}  # буква -> {"teams": {...}, "matches": [...]}
    playoff: dict[str, list[StandingsMatch]] = {}  # код стадии -> матчи

    for m in matches:
        status, home, away = effective_result(m, sim)
        brief = StandingsMatch(
            id=m.id,
            home_team=m.home_team,
            away_team=m.away_team,
            home_score=home,
            away_score=away,
            status=status,
            kickoff_at=m.kickoff_at,
        )

        if not GROUP_RE.search(m.stage or ""):
            # Плей-офф: матчи уже идут в порядке kickoff, стадии — в порядке
            # первого матча стадии (dict сохраняет порядок вставки).
            playoff.setdefault(m.stage, []).append(brief)
            continue

        letter = _group_letter(m)
        if not letter:
            continue  # групповой матч без буквы — в таблицу не положить
        group = groups.setdefault(letter, {"teams": {}, "matches": []})
        group["matches"].append(brief)
        for team in (m.home_team, m.away_team):
            group["teams"].setdefault(team, _blank_stats())

        # Очки и разница — только по завершённым матчам.
        if status != "finished" or home is None or away is None:
            continue
        ht, at = group["teams"][m.home_team], group["teams"][m.away_team]
        ht["played"] += 1
        at["played"] += 1
        ht["goals_for"] += home
        ht["goals_against"] += away
        at["goals_for"] += away
        at["goals_against"] += home
        if home > away:
            ht["points"] += 3
        elif away > home:
            at["points"] += 3
        else:
            ht["points"] += 1
            at["points"] += 1

    group_out = []
    for letter in sorted(groups):
        teams = [
            GroupTeamRow(
                team=name,
                played=s["played"],
                goals_for=s["goals_for"],
                goals_against=s["goals_against"],
                goal_diff=s["goals_for"] - s["goals_against"],
                points=s["points"],
            )
            for name, s in groups[letter]["teams"].items()
        ]
        # Место в группе: очки → разница → забитые → алфавит.
        teams.sort(key=lambda t: (-t.points, -t.goal_diff, -t.goals_for, t.team))
        group_out.append(
            GroupStanding(name=letter, teams=teams, matches=groups[letter]["matches"])
        )

    playoff_out = [
        PlayoffStage(stage=stage, matches=items) for stage, items in playoff.items()
    ]
    return StandingsOut(groups=group_out, playoff=playoff_out)


@router.get("/top-scorers", response_model=TopScorersOut)
async def top_scorers(
    ctx: RoomContext = Depends(require_room_member),
    db: AsyncSession = Depends(get_db),
):
    """Топ-5 бомбардиров турнира + все игроки, которых участники этой комнаты
    выбрали лучшим бомбардиром (с их голами). Данные — из снимка (Redis),
    обновляется ежедневно/по кнопке суперадмина."""
    snap = await get_snapshot()
    scorers = snap.get("scorers", []) if snap else []
    by_id = {s["api_id"]: s for s in scorers}

    top = [
        TopScorer(
            name=s["name"], photo=s.get("photo"), team=s.get("team"), goals=s["goals"]
        )
        for s in scorers[:5]
    ]

    rows = (
        await db.execute(
            select(
                SpecialPrediction.top_scorer_api_id, SpecialPrediction.top_scorer_name
            ).where(
                SpecialPrediction.room_id == ctx.room.id,
                SpecialPrediction.top_scorer_name.is_not(None),
            )
        )
    ).all()
    agg: dict = {}  # ключ (api_id или имя) -> {name, api_id, backers}
    for api_id, name in rows:
        key = api_id if api_id is not None else f"name:{(name or '').lower()}"
        e = agg.setdefault(key, {"name": name, "api_id": api_id, "backers": 0})
        e["backers"] += 1
        if name and not e["name"]:
            e["name"] = name

    predicted = []
    for e in agg.values():
        s = by_id.get(e["api_id"]) if e["api_id"] is not None else None
        predicted.append(
            PredictedScorer(
                name=(s["name"] if s else e["name"]) or "—",
                photo=s.get("photo") if s else None,
                goals=s["goals"] if s else 0,
                backers=e["backers"],
            )
        )
    predicted.sort(key=lambda p: (-p.goals, -p.backers, p.name.lower()))

    return TopScorersOut(
        updated_at=snap.get("updated_at") if snap else None,
        top=top,
        predicted=predicted,
    )
