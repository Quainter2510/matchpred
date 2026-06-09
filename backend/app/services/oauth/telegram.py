import hashlib
import hmac
import time

from app.config import settings


def verify_telegram_auth(data: dict) -> bool:
    """Verify a Telegram Login Widget payload.

    secret = SHA256(bot_token)
    check_hash = HMAC_SHA256(data_check_string, secret)
    data_check_string = "\\n".join sorted "key=value" of all fields except hash.
    Also rejects payloads older than 86400 seconds.
    """
    received_hash = data.get("hash")
    if not received_hash:
        return False

    auth_date = data.get("auth_date")
    if auth_date is None or (time.time() - int(auth_date)) > 86400:
        return False

    pairs = [
        f"{k}={v}"
        for k, v in sorted(data.items())
        if k != "hash" and v is not None
    ]
    data_check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, received_hash)


def extract_profile(data: dict) -> dict:
    return {
        "provider_user_id": str(data["id"]),
        "first_name": data.get("first_name", ""),
        "username": data.get("username"),
        "avatar_url": data.get("photo_url"),
    }
