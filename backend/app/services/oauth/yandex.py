from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"
USERINFO_URL = "https://login.yandex.ru/info"


def build_authorize_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.YANDEX_CLIENT_ID,
        "redirect_uri": settings.YANDEX_REDIRECT_URI,
        "scope": "login:info login:email login:avatar",
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_CLIENT_ID,
                "client_secret": settings.YANDEX_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_profile(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            USERINFO_URL,
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    avatar_id = data.get("default_avatar_id")
    avatar_url = (
        f"https://avatars.mds.yandex.net/get-yapic/{avatar_id}/islands-200"
        if avatar_id
        else None
    )
    return {
        "provider_user_id": str(data["id"]),
        "display_name": data.get("display_name") or data.get("login", ""),
        "login": data.get("login"),
        "avatar_url": avatar_url,
    }
