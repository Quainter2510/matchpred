"""Redis-backed conversation state and one-time account-linking codes."""
import json
import secrets

from app.redis_client import redis_client

_STATE_PREFIX = "botstate:"
_STATE_TTL = 3600  # 1 hour
_LINK_PREFIX = "botlink:"
_LINK_TTL = 600  # 10 minutes


def _state_key(provider: str, ext_id: str | int) -> str:
    return f"{_STATE_PREFIX}{provider}:{ext_id}"


async def get_state(provider: str, ext_id: str | int) -> dict:
    raw = await redis_client.get(_state_key(provider, ext_id))
    return json.loads(raw) if raw else {}


async def set_state(provider: str, ext_id: str | int, state: dict) -> None:
    await redis_client.setex(
        _state_key(provider, ext_id), _STATE_TTL, json.dumps(state)
    )


async def clear_state(provider: str, ext_id: str | int) -> None:
    await redis_client.delete(_state_key(provider, ext_id))


# ---- account linking ----
async def create_link_code(user_id) -> str:
    """A short, single-use code the user pastes into the bot to link accounts."""
    code = secrets.token_hex(3).upper()  # 6 hex chars, e.g. "A3F9C1"
    await redis_client.setex(f"{_LINK_PREFIX}{code}", _LINK_TTL, str(user_id))
    return code


async def consume_link_code(code: str) -> str | None:
    key = f"{_LINK_PREFIX}{code.strip().upper()}"
    user_id = await redis_client.get(key)
    if user_id:
        await redis_client.delete(key)
    return user_id
