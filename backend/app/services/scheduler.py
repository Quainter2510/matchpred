"""APScheduler: poll API-Football and recalc finished matches.

On match days it polls every 5 minutes; otherwise once per day. Each tick is
gated by a cheap DB check so off-days don't hammer the external API.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Match
from app.services import audit, football_api
from app.services.recalc import recalculate_all

log = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler(timezone="UTC")


async def _has_match_today() -> bool:
    today = datetime.now(timezone.utc).date()
    async with AsyncSessionLocal() as db:
        match = await db.scalar(select(Match.id).where(Match.match_date == today))
        return match is not None


async def sync_tick(force: bool = False) -> None:
    if not settings.API_FOOTBALL_KEY:
        return
    if not force and not await _has_match_today():
        return
    try:
        fixtures = await football_api.fetch_fixtures()
    except Exception as exc:  # network errors must not crash the scheduler
        log.warning("API-Football sync failed: %s", exc)
        return

    async with AsyncSessionLocal() as db:
        created, updated = 0, 0
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
                if fx["status"] == "finished":
                    prev_home, prev_away = existing.home_score_ft, existing.away_score_ft
                    existing.home_score_ft = fx["home_score_ft"]
                    existing.away_score_ft = fx["away_score_ft"]
                    await audit.log_match_result(
                        db,
                        match_id=existing.id,
                        home_team=existing.home_team,
                        away_team=existing.away_team,
                        new_home=fx["home_score_ft"],
                        new_away=fx["away_score_ft"],
                        prev_home=prev_home,
                        prev_away=prev_away,
                    )
                updated += 1
            else:
                match = Match(**fx)
                db.add(match)
                if fx["status"] == "finished":
                    await db.flush()
                    await audit.log_match_result(
                        db,
                        match_id=match.id,
                        home_team=match.home_team,
                        away_team=match.away_team,
                        new_home=fx["home_score_ft"],
                        new_away=fx["away_score_ft"],
                        prev_home=None,
                        prev_away=None,
                    )
                created += 1
        await audit.log_event(
            db, "api_sync", details={"created": created, "updated": updated, "auto": True}
        )
        await db.commit()
        await recalculate_all(db)
        await db.commit()
    log.info("sync_tick done: created=%s updated=%s", created, updated)


def start_scheduler() -> None:
    if not settings.API_FOOTBALL_KEY:
        log.info("API_FOOTBALL_KEY not set — scheduler disabled")
        return
    # Every 5 minutes; the gate inside sync_tick skips work on non-match days.
    scheduler.add_job(sync_tick, "interval", minutes=5, id="sync_5m", replace_existing=True)
    # Daily safety net to pick up newly added fixtures.
    scheduler.add_job(
        sync_tick, "cron", hour=3, kwargs={"force": True}, id="sync_daily", replace_existing=True
    )
    scheduler.start()
    log.info("scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
