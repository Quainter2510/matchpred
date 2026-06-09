"""Async client for API-Football (api-sports.io v3).

Only fields used by the MVP are mapped. Extra time / penalties are ignored —
we store the main-time (FT) score only.
"""
from datetime import datetime, timezone

import httpx

from app.config import settings

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


def _normalize_fixture(fx: dict) -> dict:
    fixture = fx["fixture"]
    teams = fx["teams"]
    goals = fx["goals"]
    league = fx.get("league", {})
    kickoff = datetime.fromisoformat(fixture["date"]).astimezone(timezone.utc)
    raw_status = fixture.get("status", {}).get("short", "NS")
    return {
        "api_football_id": fixture["id"],
        "kickoff_at": kickoff,
        "match_date": kickoff.date(),
        "stage": (league.get("round") or "group").lower().replace(" ", "_")[:40],
        "home_team": teams["home"]["name"],
        "away_team": teams["away"]["name"],
        "home_score_ft": goals.get("home"),
        "away_score_ft": goals.get("away"),
        "status": _STATUS_MAP.get(raw_status, "scheduled"),
    }


async def fetch_fixtures() -> list[dict]:
    """All fixtures for the configured league + season."""
    data = await _get(
        "/fixtures",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    return [_normalize_fixture(fx) for fx in data.get("response", [])]


async def search_players(query: str) -> list[dict]:
    """Player autocomplete for the top-scorer special prediction.

    Uses the name-based `/players/profiles` endpoint instead of
    `/players?league=&season=`: before the tournament the WC league/season has
    no squads loaded, so a league/season-scoped search returns nothing. Profile
    search works by surname across all of API-Football's player database.
    """
    data = await _get("/players/profiles", {"search": query})
    out: list[dict] = []
    for item in data.get("response", []):
        player = item.get("player", {})
        if not player.get("id"):
            continue
        name = player.get("name") or " ".join(
            filter(None, [player.get("firstname"), player.get("lastname")])
        )
        out.append(
            {
                "api_id": player.get("id"),
                "name": name,
                "team": player.get("nationality"),
                "photo": player.get("photo"),
            }
        )
    return out
