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
        return resp.json()


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
    """Player autocomplete for the top-scorer special prediction."""
    data = await _get(
        "/players",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
            "search": query,
        },
    )
    out: list[dict] = []
    for item in data.get("response", []):
        player = item.get("player", {})
        stats = item.get("statistics", [{}])
        team = stats[0].get("team", {}).get("name") if stats else None
        out.append(
            {
                "api_id": player.get("id"),
                "name": player.get("name"),
                "team": team,
                "photo": player.get("photo"),
            }
        )
    return out
