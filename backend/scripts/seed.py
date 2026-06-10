"""Seed World Cup fixtures from API-Football and ensure the tournament row.

The superadmin is NOT created here — that happens on the first OAuth login.
This script:
  1. Loads all fixtures for the configured league/season and upserts matches.
  2. Creates the single tournament row if absent, with first_match_at set to
     the earliest kickoff and an initial password (override with --password).

Usage:
    python -m scripts.seed
    python -m scripts.seed --password mysecret --name "ЧМ-2026"
    # if API-Football has no fixtures yet, set the deadline manually:
    python -m scripts.seed --first-match-at 2026-06-11T16:00:00+00:00
"""
import argparse
import asyncio
import secrets
from datetime import datetime

from sqlalchemy import func, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Match, Room
from app.security import hash_password
from app.services import football_api


async def upsert_matches(db) -> tuple[int, str]:
    if not settings.API_FOOTBALL_KEY:
        msg = "API_FOOTBALL_KEY is not set in environment — fixture load skipped."
        print(f"WARN: {msg}")
        return 0, msg
    try:
        fixtures = await football_api.fetch_fixtures()
    except Exception as exc:
        msg = f"API-Football request failed: {exc}"
        print(f"WARN: {msg}")
        return 0, msg
    count = len(fixtures)
    print(
        f"API-Football returned {count} fixtures "
        f"(league={settings.API_FOOTBALL_LEAGUE_ID}, season={settings.API_FOOTBALL_SEASON})."
    )
    if count == 0:
        msg = (
            f"API-Football returned 0 fixtures for "
            f"league={settings.API_FOOTBALL_LEAGUE_ID}, season={settings.API_FOOTBALL_SEASON}. "
            "Check that the league/season values are correct."
        )
        print(f"WARN: {msg}")
        return 0, msg
    created = 0
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
        else:
            db.add(Match(**fx))
            created += 1
    await db.flush()
    return created, ""


async def ensure_room(
    db, name: str, password: str | None, first_match_at: str | None, no_matches_reason: str = ""
) -> str | None:
    """Create the default room if no rooms exist yet. The superadmin can create
    more rooms later from the UI; this just bootstraps the first one so players
    have somewhere to join right after launch."""
    existing = await db.scalar(select(Room).limit(1))
    if existing:
        print(f"Room already exists: {existing.name}")
        return None

    earliest = await db.scalar(select(func.min(Match.kickoff_at)))
    if earliest is None and first_match_at:
        earliest = datetime.fromisoformat(first_match_at)
    if earliest is None:
        reason_block = (
            f"\n\nПричина: {no_matches_reason}" if no_matches_reason else ""
        )
        raise SystemExit(
            "ERROR: нет матчей в БД и флаг --first-match-at не передан — "
            "невозможно определить дату первого матча (deadline предсказаний)."
            f"{reason_block}\n\n"
            "Варианты решения:\n"
            "  1. Проверьте API_FOOTBALL_KEY, API_FOOTBALL_LEAGUE_ID, API_FOOTBALL_SEASON\n"
            "     и перезапустите: python -m scripts.seed\n"
            "  2. Укажите дату вручную:\n"
            "     python -m scripts.seed --first-match-at 2026-06-11T16:00:00+00:00\n"
            "  Матчи можно добавить позже через Admin-панель или /admin/sync."
        )

    password = password or secrets.token_urlsafe(8)
    db.add(
        Room(
            name=name,
            password_hash=hash_password(password),
            first_match_at=earliest,
            created_by=None,  # claimed by the superadmin on first login
        )
    )
    return password


async def main(name: str, password: str | None, first_match_at: str | None) -> None:
    async with AsyncSessionLocal() as db:
        created, no_matches_reason = await upsert_matches(db)
        generated = await ensure_room(db, name, password, first_match_at, no_matches_reason)
        await db.commit()
    print(f"Matches created: {created}")
    if generated:
        print("=" * 50)
        print(f"  TOURNAMENT PASSWORD: {generated}")
        print("  Change it in the Admin panel after first login.")
        print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="ЧМ-2026")
    parser.add_argument("--password", default=None)
    parser.add_argument(
        "--first-match-at",
        default=None,
        help="ISO datetime (UTC) for the special-prediction deadline when no "
        "fixtures are loaded yet, e.g. 2026-06-11T16:00:00+00:00",
    )
    args = parser.parse_args()
    asyncio.run(main(args.name, args.password, args.first_match_at))
