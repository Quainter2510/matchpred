"""Снимок бомбардиров турнира.

Данные у API-Football обновляются нечасто и стоят запроса (квота), поэтому
храним снимок в Redis и обновляем его раз в день (крон, 10:00 МСК) или вручную
по кнопке «Синхронизировать» суперадмина (/admin/sync). Эндпоинт-читатель снимок
не запрашивает у API — только отдаёт из Redis.

Топ-лист API ограничен (~20 строк), поэтому при обновлении снимок дополняется
статистикой игроков, которых участники выбрали бомбардиром, но которых в
топ-листе нет — иначе у них в «Выборе участников» всегда 0 голов. Для игроков
кураторского каталога без заполненного real_id реальный ID разрешается по
имени через /players/profiles и кэшируется в Redis навсегда; карта
canonical_id → real_id кладётся в снимок для эндпоинта-читателя.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import SpecialPrediction
from app.redis_client import redis_client
from app.services import football_api
from app.services.players_catalog import resolve_player

log = logging.getLogger("top_scorers")

SNAPSHOT_KEY = "top_scorers:snapshot"
# Разрешённый по имени реальный ID кураторского игрока (без TTL — ID стабилен).
REAL_ID_KEY = "top_scorers:real_id:{}"


async def _cached_real_id(canonical_id: int) -> int | None:
    try:
        raw = await redis_client.get(REAL_ID_KEY.format(canonical_id))
        return int(raw) if raw else None
    except Exception:
        return None


async def _cache_real_id(canonical_id: int, real_id: int) -> None:
    try:
        await redis_client.set(REAL_ID_KEY.format(canonical_id), str(real_id))
    except Exception:
        pass


async def _picked_players() -> list[tuple[int, str | None]]:
    """Уникальные выборы бомбардира по всем комнатам: [(api_id, name)]."""
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    SpecialPrediction.top_scorer_api_id,
                    SpecialPrediction.top_scorer_name,
                ).where(SpecialPrediction.top_scorer_api_id.is_not(None))
            )
        ).all()
    seen: dict[int, str | None] = {}
    for api_id, name in rows:
        seen.setdefault(api_id, name)
    return list(seen.items())


async def refresh_top_scorers() -> int:
    """Подтянуть бомбардиров из API-Football и сохранить снимок в Redis.
    Без ключа API — ничего не делает. Возвращает число игроков в снимке."""
    if not settings.API_FOOTBALL_KEY:
        return 0
    scorers = await football_api.fetch_top_scorers()
    known_ids = {s["api_id"] for s in scorers}
    resolved: dict[int, int] = {}  # canonical (кураторский) id → реальный id

    for api_id, name in await _picked_players():
        rec = resolve_player(api_id)
        real_id = rec["real_id"] if rec else api_id

        # Кураторская запись без real_id: разрешаем реальный ID по имени
        # (один раз — дальше из Redis-кэша).
        if real_id is None and rec:
            real_id = await _cached_real_id(rec["canonical_id"])
            if real_id is None:
                try:
                    real_id = await football_api.resolve_player_id(
                        rec["name"], rec.get("team")
                    )
                except Exception as exc:
                    log.warning("resolve_player_id(%s) failed: %s", rec["name"], exc)
                    real_id = None
                if real_id:
                    await _cache_real_id(rec["canonical_id"], real_id)
        if rec and real_id:
            resolved[rec["canonical_id"]] = real_id

        # Игрока нет в топ-листе — догружаем его статистику отдельно.
        if not real_id or real_id < 0 or real_id in known_ids:
            continue
        try:
            entry = await football_api.fetch_player_goals(real_id)
        except Exception as exc:
            log.warning("fetch_player_goals(%s) failed: %s", real_id, exc)
            entry = None
        if entry:
            scorers.append(entry)
            known_ids.add(entry["api_id"])

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scorers": scorers,
        # str-ключи: JSON не умеет int-ключи, читатель приводит обратно.
        "resolved": {str(k): v for k, v in resolved.items()},
    }
    try:
        await redis_client.set(SNAPSHOT_KEY, json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Кэш не должен ронять синхронизацию.
        pass
    return len(scorers)


async def get_snapshot() -> dict | None:
    """Снимок {updated_at, scorers:[{api_id,name,photo,team,goals}],
    resolved:{canonical_id→real_id}} или None."""
    try:
        raw = await redis_client.get(SNAPSHOT_KEY)
    except Exception:
        return None
    return json.loads(raw) if raw else None
