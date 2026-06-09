"""Async client for API-Football (api-sports.io v3).

Only fields used by the MVP are mapped. Extra time / penalties are ignored —
we store the main-time (FT) score only.
"""
import re
from datetime import datetime, timezone

import httpx

from app.config import settings

# Настоящая группа в /standings называется "Group A".."Group L". Кроме них там
# бывают служебные таблицы вроде "Ranking of third-placed teams" — их игнорируем.
_GROUP_RE = re.compile(r"^group\s+([a-z0-9]{1,3})$", re.IGNORECASE)

_STATUS_MAP = {
    "TBD": "scheduled",
    "NS": "scheduled",
    "1H": "live",
    "HT": "live",
    "2H": "live",
    "ET": "live",
    "P": "live",
    "BT": "live",
    "LIVE": "live",
    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
    "PST": "cancelled",
    "CANC": "cancelled",
    "ABD": "cancelled",
    "AWD": "finished",
    "WO": "finished",
}


def _headers() -> dict:
    return {"x-apisports-key": settings.API_FOOTBALL_KEY}


async def _get(path: str, params: dict) -> dict:
    async with httpx.AsyncClient(
        base_url=settings.API_FOOTBALL_BASE, timeout=20
    ) as client:
        resp = await client.get(path, params=params, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        # api-sports returns HTTP 200 with a non-empty `errors` field on
        # auth/quota/parameter problems. Surface it instead of returning [].
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-Football error: {errors}")
        return data


def _normalize_fixture(fx: dict, groups: dict[str, str] | None = None) -> dict:
    fixture = fx["fixture"]
    teams = fx["teams"]
    goals = fx["goals"]
    league = fx.get("league", {})
    kickoff = datetime.fromisoformat(fixture["date"]).astimezone(timezone.utc)
    raw_status = fixture.get("status", {}).get("short", "NS")
    stage = (league.get("round") or "group").lower().replace(" ", "_")[:40]
    home = teams["home"]["name"]
    away = teams["away"]["name"]
    # Буква группы есть только у матчей группового этапа — берём из таблицы групп
    # (раунд из API содержит лишь номер тура, напр. "group_stage_-_1").
    group_name = None
    if groups and "group" in stage:
        group_name = groups.get(home) or groups.get(away)
    return {
        "api_football_id": fixture["id"],
        "kickoff_at": kickoff,
        "match_date": kickoff.date(),
        "stage": stage,
        "group_name": group_name,
        "home_team": home,
        "away_team": away,
        "home_score_ft": goals.get("home"),
        "away_score_ft": goals.get("away"),
        "status": _STATUS_MAP.get(raw_status, "scheduled"),
    }


async def fetch_groups() -> dict[str, str]:
    """Сопоставление «название сборной → буква группы» из /standings.

    Раунд матча в API содержит только номер тура, без буквы группы, поэтому
    группу берём из турнирной таблицы. Возвращает {} при недоступности данных
    (например, до жеребьёвки) — тогда матчи останутся без group_name.
    """
    try:
        data = await _get(
            "/standings",
            {
                "league": settings.API_FOOTBALL_LEAGUE_ID,
                "season": settings.API_FOOTBALL_SEASON,
            },
        )
    except Exception:
        return {}
    out: dict[str, str] = {}
    for league in data.get("response", []):
        for group in league.get("league", {}).get("standings", []) or []:
            for row in group:
                m = _GROUP_RE.match((row.get("group") or "").strip())
                if not m:
                    continue
                team = (row.get("team") or {}).get("name")
                if team:
                    out[team] = m.group(1).upper()
    return out


async def fetch_fixtures() -> list[dict]:
    """All fixtures for the configured league + season."""
    data = await _get(
        "/fixtures",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    groups = await fetch_groups()
    return [_normalize_fixture(fx, groups) for fx in data.get("response", [])]


# Бомбардир — это почти всегда нападающий, реже полузащитник. Поднимаем таких
# кандидатов наверх списка, чтобы не тонуть в защитниках/вратарях.
_POSITION_RANK = {"Attacker": 0, "Midfielder": 1, "Defender": 2, "Goalkeeper": 3}
_SEARCH_LIMIT = 20


async def search_players(query: str) -> list[dict]:
    """Player autocomplete for the top-scorer special prediction.

    Uses the name-based `/players/profiles` endpoint instead of
    `/players?league=&season=`: before the tournament the WC league/season has
    no squads loaded, so a league/season-scoped search returns nothing. Profile
    search works by surname across all of API-Football's player database.

    Результат сортируется по позиции (нападающие выше) и обрезается до
    _SEARCH_LIMIT, иначе кандидатов слишком много.
    """
    data = await _get("/players/profiles", {"search": query})
    ranked: list[tuple] = []
    seen: set[int] = set()
    for item in data.get("response", []):
        player = item.get("player", {})
        pid = player.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        name = player.get("name") or " ".join(
            filter(None, [player.get("firstname"), player.get("lastname")])
        )
        rank = _POSITION_RANK.get(player.get("position"), 4)
        ranked.append(
            (
                rank,
                (name or "").lower(),
                {
                    "api_id": pid,
                    "name": name,
                    "team": player.get("nationality"),
                    "photo": player.get("photo"),
                },
            )
        )
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [d for _, _, d in ranked[:_SEARCH_LIMIT]]
