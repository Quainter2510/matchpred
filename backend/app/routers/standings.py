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
from app.models import Match, RoomMember, SpecialPrediction
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
from app.services.players_catalog import normalize_name, resolve_player
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


# Латинское имя из каталожного формата «Гарри Кейн (Harry Kane)».
_LATIN_IN_PARENS = re.compile(r"\(([^)]+)\)")


def _surname_key(name: str | None) -> str | None:
    """Фамилия латиницей без диакритики — грубый ключ для сопоставления выбора
    участника со снимком бомбардиров, когда real_id игрока неизвестен (у части
    кураторского каталога он не заполнен). У API имена вида "H. Kane" — берём
    последнее слово длиной >1 (отбрасывая инициалы)."""
    if not name:
        return None
    m = _LATIN_IN_PARENS.search(name)
    if m:
        name = m.group(1)
    parts = [w for w in re.split(r"[\s.\-']+", name.strip()) if len(w) > 1]
    if not parts:
        return None
    return normalize_name(parts[-1])


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
    by_id = {s["api_id"]: s for s in scorers}  # ключи — реальные ID из API
    # Разрешённые при обновлении снимка ID кураторских игроков (real_id
    # которых в каталоге не заполнен): canonical_id → реальный ID.
    resolved: dict[int, int] = {
        int(k): v for k, v in ((snap or {}).get("resolved") or {}).items()
    }
    # Фолбэк-индекс по фамилии: для игроков каталога без real_id.
    by_surname: dict[str, list[dict]] = {}
    for s in scorers:
        k = _surname_key(s.get("name"))
        if k:
            by_surname.setdefault(k, []).append(s)

    def snapshot_entry(real_id, name, team) -> dict | None:
        """Строка снимка по real_id, иначе по фамилии (+ сборная, если фамилия
        неоднозначна). None — игрока нет среди бомбардиров (0 голов)."""
        if real_id is not None and real_id in by_id:
            return by_id[real_id]
        k = _surname_key(name)
        cands = by_surname.get(k, []) if k else []
        if len(cands) == 1:
            return cands[0]
        if team and len(cands) > 1:
            t = normalize_name(team)
            same_team = [
                c for c in cands if normalize_name(c.get("team") or "") == t
            ]
            if len(same_team) == 1:
                return same_team[0]
        return None

    top = [
        TopScorer(
            # Подменяем имя на русское, если игрок есть в каталоге.
            name=(resolve_player(s["api_id"]) or {}).get("name") or s["name"],
            photo=s.get("photo"),
            team=s.get("team"),
            goals=s["goals"],
        )
        for s in scorers[:5]
    ]

    # Только текущие участники комнаты (выбывшие в выборку не попадают).
    rows = (
        await db.execute(
            select(
                SpecialPrediction.top_scorer_api_id, SpecialPrediction.top_scorer_name
            )
            .join(
                RoomMember,
                (RoomMember.room_id == SpecialPrediction.room_id)
                & (RoomMember.user_id == SpecialPrediction.user_id),
            )
            .where(
                SpecialPrediction.room_id == ctx.room.id,
                SpecialPrediction.top_scorer_name.is_not(None),
            )
        )
    ).all()
    # Канонизируем ID: реальный и кураторский (-1 / 278) — это один игрок.
    agg: dict = {}  # ключ -> {name, real_id, team, backers}
    for api_id, name in rows:
        rec = resolve_player(api_id)
        if rec:
            key = rec["canonical_id"]
            disp_name = rec["name"]
            # real_id из каталога, иначе — разрешённый при обновлении снимка.
            real_id = rec["real_id"] or resolved.get(rec["canonical_id"])
            team = rec.get("team")
        else:
            key = api_id if api_id is not None else f"name:{(name or '').lower()}"
            disp_name = name
            real_id = api_id
            team = None
        e = agg.setdefault(
            key, {"name": disp_name, "real_id": real_id, "team": team, "backers": 0}
        )
        e["backers"] += 1
        if disp_name and not e["name"]:
            e["name"] = disp_name

    predicted = []
    for e in agg.values():
        s = snapshot_entry(e["real_id"], e["name"], e.get("team"))
        predicted.append(
            PredictedScorer(
                name=e["name"] or "—",
                photo=None,
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
