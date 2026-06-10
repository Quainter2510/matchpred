"""Minimal VK community API client (messages.send / users.get)."""
import json
import logging
import random

import httpx

from app.config import settings

log = logging.getLogger("bot.vk")
_API = "https://api.vk.com/method"


async def _call(method: str, params: dict) -> dict:
    params = {
        **params,
        "access_token": settings.VK_GROUP_TOKEN,
        "v": settings.VK_API_VERSION,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{_API}/{method}", data=params)
        data = resp.json()
    if "error" in data:
        log.warning("VK API %s error: %s", method, data["error"])
    return data


async def send_message(
    peer_id: int, text: str, keyboard: dict | None = None
) -> None:
    params = {
        "peer_id": peer_id,
        "message": text,
        "random_id": random.randint(1, 2_000_000_000),
    }
    if keyboard is not None:
        params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    await _call("messages.send", params)


async def get_user_name(user_id: int) -> str | None:
    data = await _call("users.get", {"user_ids": user_id})
    resp = data.get("response") or []
    if resp:
        u = resp[0]
        return " ".join(filter(None, [u.get("first_name"), u.get("last_name")])) or None
    return None
