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
from app.models import Match, Tournament
from app.security import hash_password
from app.services import football_api


async def upsert_matches(db) -> int:
    if not settings.API_FOOTBALL_KEY:
        print("WARN: API_FOOTBALL_KEY is empty — skipping fixture load.")
        return 0
    try:
        fixtures = await football_api.fetch_fixtures()
    except Exception as exc:
        print(f"WARN: could not load fixtures from API-Football: {exc}")
        return 0
    print(
        f"API-Football returned {len(fixtures)} fixtures "
        f"(league={settings.API_FOOTBALL_LEAGUE_ID}, season={settings.API_FOOTBALL_SEASON})."
    )
    created = 0
    for fx in fixtures:
        existing = await db.scalar(
            select(Match).where(Match.api_football_id == fx["api_football_id"])
        )
        if existing:
            existing.kickoff_at = fx["kickoff_at"]
            existing.match_date = fx["match_date"]
            existing.stage = fx["stage"]
            existing.home_team = fx["home_team"]
            existing.away_team = fx["away_team"]
            existing.status = fx["status"]
        else:
            db.add(Match(**fx))
            created += 1
    await db.flush()
    return created


async def ensure_tournament(
    db, name: str, password: str | None, first_match_at: str | None
) -> str | None:
    existing = await db.scalar(select(Tournament).limit(1))
    if existing:
        print(f"Tournament already exists: {existing.name}")
        return None

    earliest = await db.scalar(select(func.min(Match.kickoff_at)))
    if earliest is None and first_match_at:
        earliest = datetime.fromisoformat(first_match_at)
    if earliest is None:
        raise SystemExit(
            "No matches loaded and --first-match-at not provided.\n"
            "Either fix API-Football settings and re-run, or pass the deadline "
            "manually, e.g.:\n"
            "  python -m scripts.seed --first-match-at 2026-06-11T16:00:00+00:00\n"
            "Matches can be added later via the Admin panel or /admin/sync."
        )

    password = password or secrets.token_urlsafe(8)
    db.add(
        Tournament(
            name=name,
            password_hash=hash_password(password),
            first_match_at=earliest,
        )
    )
    return password


async def main(name: str, password: str | None, first_match_at: str | None) -> None:
    async with AsyncSessionLocal() as db:
        created = await upsert_matches(db)
        generated = await ensure_tournament(db, name, password, first_match_at)
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
