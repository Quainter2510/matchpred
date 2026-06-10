import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.bot import core, vk_client

log = logging.getLogger("bot.vk")
router = APIRouter(prefix="/bots", tags=["bots"])

PROVIDER = "vk"


def _to_vk_keyboard(buttons: list[list[core.Button]]) -> dict | None:
    if not buttons:
        return None
    return {
        "one_time": False,
        "inline": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": b.label[:40],
                        "payload": json.dumps(b.payload, ensure_ascii=False),
                    }
                }
                for b in row
            ]
            for row in buttons
        ],
    }


@router.post("/vk/callback")
async def vk_callback(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    event_type = body.get("type")

    # Step 1: server confirmation handshake.
    if event_type == "confirmation":
        return PlainTextResponse(settings.VK_CONFIRMATION)

    # Verify the shared secret (when configured) — ignore anything else.
    if settings.VK_SECRET and body.get("secret") != settings.VK_SECRET:
        log.warning("VK callback with bad secret")
        return PlainTextResponse("ok")

    if event_type == "message_new":
        try:
            message = body["object"]["message"]
            from_id = message["from_id"]
            text = message.get("text", "")
            payload = None
            raw_payload = message.get("payload")
            if raw_payload:
                try:
                    payload = json.loads(raw_payload)
                except (ValueError, TypeError):
                    payload = None

            reply = await core.handle_event(db, PROVIDER, str(from_id), text, payload)
            await vk_client.send_message(
                from_id, reply.text, _to_vk_keyboard(reply.buttons)
            )
        except Exception:  # never let VK retry-storm us
            log.exception("VK message handling failed")

    return PlainTextResponse("ok")
