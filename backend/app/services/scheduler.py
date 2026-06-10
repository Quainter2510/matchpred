"""APScheduler: poll API-Football and recalc finished matches.

On match days it polls every 5 minutes; otherwise once per day. Each tick is
gated by a cheap DB check so off-days don't hammer the external API.
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, or_, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Match
from app.services import audit, football_api
from app.services.recalc import recalculate_all
from app.services.sync import apply_fixtures

log = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler(timezone="UTC")


async def _should_poll() -> bool:
    """True if there is anything worth polling for: a match today (UTC), a
    match still marked live, or a recently kicked-off match that hasn't been
    seen finishing yet (covers games crossing UTC midnight)."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        row = await db.scalar(
            select(Match.id)
            .where(
                or_(
                    Match.match_date == now.date(),
                    Match.status == "live",
                    and_(
                        Match.status == "scheduled",
                        Match.kickoff_at <= now,
                        Match.kickoff_at >= now - timedelta(hours=4),
                    ),
                )
            )
            .limit(1)
        )
        return row is not None


async def sync_tick(force: bool = False) -> None:
    if not settings.API_FOOTBALL_KEY:
        return
    if not force and not await _should_poll():
        return
    try:
        # Буквы групп (/standings) тянем только в ежедневном полном синке —
        # live-тик обходится одним запросом к API.
        fixtures = await football_api.fetch_fixtures(with_groups=force)
    except Exception as exc:  # network errors must not crash the scheduler
        log.warning("API-Football sync failed: %s", exc)
        return

    async with AsyncSessionLocal() as db:
        stats = await apply_fixtures(db, fixtures)
        if stats["created"] or stats["updated"]:
            await audit.log_event(db, "api_sync", details={**stats, "auto": True})
        await db.commit()
        await recalculate_all(db)
        await db.commit()
    log.info("sync_tick done: %s", stats)


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
