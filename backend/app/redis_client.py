import uuid

import redis.asyncio as redis

from app.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL, encoding="utf-8", decode_responses=True
)

LEADERBOARD_CACHE_PREFIX = "leaderboard:v2:"
LEADERBOARD_CACHE_TTL = 60


def leaderboard_cache_key(room_id: uuid.UUID) -> str:
    return f"{LEADERBOARD_CACHE_PREFIX}{room_id}"


async def invalidate_leaderboard_cache(room_id: uuid.UUID | None = None) -> None:
    """Invalidate one room's cache, or every room's cache when room_id is None.

    A match result scores all rooms, so the global form is used after scoring."""
    try:
        if room_id is not None:
            await redis_client.delete(leaderboard_cache_key(room_id))
            return
        keys = [k async for k in redis_client.scan_iter(f"{LEADERBOARD_CACHE_PREFIX}*")]
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        # Cache invalidation must never break the request path.
        pass
