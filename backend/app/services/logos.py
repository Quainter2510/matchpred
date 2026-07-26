"""Скачивание логотипов команд на наш сервер.

API-Football отдаёт URL логотипа (media.api-sports.io). Мы качаем его один раз в
`media/teams/{id}.png` и раздаём из `/api/v1/media/teams/...` (тот же
StaticFiles-маунт, что и аватары). Так UI не зависит от их CDN.
"""
import logging
import os

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team

log = logging.getLogger("logos")

LOGO_DIR = "media/teams"


async def download_missing_logos(db: AsyncSession, limit: int | None = None) -> int:
    """Скачать логотипы команд, у которых есть logo_url, но нет локального файла.
    Best-effort: сетевые ошибки логируются и не роняют синхронизацию. Возвращает
    число обработанных команд. Не коммитит (это делает вызывающий)."""
    os.makedirs(LOGO_DIR, exist_ok=True)
    stmt = select(Team).where(
        Team.logo_url.is_not(None), Team.logo_local.is_(None)
    )
    if limit:
        stmt = stmt.limit(limit)
    teams = (await db.execute(stmt)).scalars().all()
    if not teams:
        return 0

    done = 0
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for t in teams:
            fname = f"{t.api_football_id}.png"
            path = os.path.join(LOGO_DIR, fname)
            try:
                if not os.path.exists(path):
                    resp = await client.get(t.logo_url)
                    resp.raise_for_status()
                    with open(path, "wb") as f:
                        f.write(resp.content)
                t.logo_local = fname
                done += 1
            except Exception as exc:  # network/HTTP errors must not crash sync
                log.warning("logo download failed for team %s: %s", t.api_football_id, exc)
    return done
