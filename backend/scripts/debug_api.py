"""Диагностика данных API-Football, по которым выводится буква группы.

Запуск:
    cd backend && python -m scripts.debug_api
    # или в Docker:
    docker compose exec backend python -m scripts.debug_api

Скопируйте весь вывод — по нему видно, почему не подставляется буква группы:
есть ли standings вообще, как там называются группы и совпадают ли названия
команд между /standings и /fixtures.
"""
import asyncio

from app.config import settings
from app.services import football_api


async def main() -> None:
    print(
        f"BASE={settings.API_FOOTBALL_BASE} "
        f"LEAGUE={settings.API_FOOTBALL_LEAGUE_ID} "
        f"SEASON={settings.API_FOOTBALL_SEASON}"
    )
    print(f"API key set: {bool(settings.API_FOOTBALL_KEY)}")
    print("-" * 60)

    # 1) Сырые standings: сколько вернулось, какие метки групп, какие команды.
    try:
        data = await football_api._get(
            "/standings",
            {
                "league": settings.API_FOOTBALL_LEAGUE_ID,
                "season": settings.API_FOOTBALL_SEASON,
            },
        )
    except Exception as exc:
        print(f"standings request FAILED: {exc}")
        data = {}
    print("standings.results:", data.get("results"))
    print("standings.errors:", data.get("errors"))

    labels: set[str] = set()
    sample: list[tuple] = []
    for league in data.get("response", []):
        for group in league.get("league", {}).get("standings", []) or []:
            for row in group:
                if row.get("group"):
                    labels.add(row["group"])
                if len(sample) < 12:
                    sample.append((row.get("group"), (row.get("team") or {}).get("name")))
    print("distinct group labels:", sorted(labels))
    print("sample (group :: team):")
    for g, t in sample:
        print("   ", repr(g), "::", t)
    print("-" * 60)

    # 2) Что строит наш парсер.
    groups = await football_api.fetch_groups()
    print(f"fetch_groups() -> {len(groups)} teams")
    for i, (team, letter) in enumerate(groups.items()):
        if i >= 12:
            break
        print("   ", team, "=>", letter)
    print("-" * 60)

    # 3) Названия команд и round в /fixtures — сверить с standings.
    try:
        fx = await football_api._get(
            "/fixtures",
            {
                "league": settings.API_FOOTBALL_LEAGUE_ID,
                "season": settings.API_FOOTBALL_SEASON,
            },
        )
        print("fixtures.results:", fx.get("results"))
        for item in fx.get("response", [])[:6]:
            lg = item.get("league", {})
            tm = item.get("teams", {})
            print(
                "fixture:",
                repr(lg.get("round")),
                "|",
                (tm.get("home") or {}).get("name"),
                "vs",
                (tm.get("away") or {}).get("name"),
            )
    except Exception as exc:
        print(f"fixtures request FAILED: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
