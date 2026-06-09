"""Pure-function auth tests (no DB required).

Covers the Telegram Login Widget HMAC verification, which is security-critical.
Integration tests for /auth/* (DB-backed) run against a Postgres instance in CI;
see tests/README for that setup.
"""
import hashlib
import hmac
import time

import pytest

from app.config import settings
from app.services.oauth import telegram


def _sign(data: dict, bot_token: str) -> str:
    pairs = [f"{k}={v}" for k, v in sorted(data.items()) if k != "hash"]
    dcs = "\n".join(pairs)
    secret = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def _bot_token(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-bot-token")


def test_valid_signature():
    data = {"id": 42, "first_name": "Ivan", "auth_date": int(time.time())}
    data["hash"] = _sign(data, "test-bot-token")
    assert telegram.verify_telegram_auth(data) is True


def test_tampered_payload_rejected():
    data = {"id": 42, "first_name": "Ivan", "auth_date": int(time.time())}
    data["hash"] = _sign(data, "test-bot-token")
    data["id"] = 999  # tamper after signing
    assert telegram.verify_telegram_auth(data) is False


def test_wrong_bot_token_rejected():
    data = {"id": 42, "first_name": "Ivan", "auth_date": int(time.time())}
    data["hash"] = _sign(data, "other-token")
    assert telegram.verify_telegram_auth(data) is False


def test_expired_auth_date_rejected():
    data = {"id": 42, "first_name": "Ivan", "auth_date": int(time.time()) - 90000}
    data["hash"] = _sign(data, "test-bot-token")
    assert telegram.verify_telegram_auth(data) is False


def test_missing_hash_rejected():
    assert telegram.verify_telegram_auth({"id": 1, "auth_date": int(time.time())}) is False
