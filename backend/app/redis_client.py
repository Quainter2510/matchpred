import redis.asyncio as redis

from app.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL, encoding="utf-8", decode_responses=True
)

LEADERBOARD_CACHE_KEY = "leaderboard:v1"
LEADERBOARD_CACHE_TTL = 60


async def invalidate_leaderboard_cache() -> None:
    try:
        await redis_client.delete(LEADERBOARD_CACHE_KEY)
    except Exception:
        # Cache invalidation must never break the request path.
        pass
