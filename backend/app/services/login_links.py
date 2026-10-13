"""Одноразовые ссылки входа, которые суперадмин выдаёт пользователю лично —
запасной вход в существующий аккаунт, когда OAuth-провайдер недоступен.

Токен живёт в Redis и гасится при первом использовании. В ссылке он передаётся
во fragment (#token=…): не попадает в логи прокси и не уходит в Referer, а
обмен на сессию делает POST со страницы фронта — превью ссылок в мессенджерах
(GET без выполнения JS) токен не сжигают.
"""
import secrets

from app.redis_client import redis_client

_PREFIX = "loginlink:"
LOGIN_LINK_TTL = 3600  # 1 час


async def create_login_token(user_id) -> str:
    token = secrets.token_urlsafe(32)
    await redis_client.setex(f"{_PREFIX}{token}", LOGIN_LINK_TTL, str(user_id))
    return token


async def consume_login_token(token: str) -> str | None:
    """user_id по токену или None. GETDEL — атомарно, токен одноразовый даже
    при одновременных запросах."""
    return await redis_client.getdel(f"{_PREFIX}{token.strip()}")
