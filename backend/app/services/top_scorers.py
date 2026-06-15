"""Снимок бомбардиров турнира.

Данные у API-Football обновляются нечасто и стоят запроса (квота), поэтому
храним снимок в Redis и обновляем его раз в день (крон, 10:00 МСК) или вручную
по кнопке «Синхронизировать» суперадмина (/admin/sync). Эндпоинт-читатель снимок
не запрашивает у API — только отдаёт из Redis.
"""
import json
from datetime import datetime, timezone

from app.config import settings
from app.redis_client import redis_client
from app.services import football_api

SNAPSHOT_KEY = "top_scorers:snapshot"


async def refresh_top_scorers() -> int:
    """Подтянуть бомбардиров из API-Football и сохранить снимок в Redis.
    Без ключа API — ничего не делает. Возвращает число игроков в снимке."""
    if not settings.API_FOOTBALL_KEY:
        return 0
    scorers = await football_api.fetch_top_scorers()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scorers": scorers,
    }
    try:
        await redis_client.set(SNAPSHOT_KEY, json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Кэш не должен ронять синхронизацию.
        pass
    return len(scorers)


async def get_snapshot() -> dict | None:
    """Снимок {updated_at, scorers:[{api_id,name,photo,team,goals}]} или None."""
    try:
        raw = await redis_client.get(SNAPSHOT_KEY)
    except Exception:
        return None
    return json.loads(raw) if raw else None
