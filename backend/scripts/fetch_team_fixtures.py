"""Разовая загрузка матчей сборных-участниц ЧМ за сезон в справочник
team_matches (блок «последние матчи» на странице прогноза).

Что делает:
  1. Берёт ID 48 сборных из фикстур ЧМ (лига из настроек).
  2. По каждой сборной запрашивает /fixtures?team=&season= — все турниры
     (товарищеские, отборочные, Лига наций и т.д.).
  3. Матчи самого ЧМ пропускаются — они живут в `matches` и подмешиваются
     при чтении, поэтому список формы сам пополняется по ходу турнира.
  4. Upsert по api_football_id — скрипт можно перезапускать (обновит счета).

~50 запросов к API. Запуск:
    docker compose exec backend python -m scripts.fetch_team_fixtures
"""
import asyncio

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import TeamMatch
from app.services import football_api

# Платный тариф щедрый, но не наглеем: маленькая пауза между запросами.
REQUEST_PAUSE_S = 0.3


async def main() -> None:
    if not settings.API_FOOTBALL_KEY:
        raise SystemExit("API_FOOTBALL_KEY is not set")

    teams = await football_api.fetch_wc_team_ids()
    print(f"WC teams with known ids: {len(teams)}")
    if not teams:
        raise SystemExit(
            "No team ids found — check that WC fixtures are available in the API."
        )

    created = updated = 0
    async with AsyncSessionLocal() as db:
        for i, (team_id, name) in enumerate(sorted(teams.items(), key=lambda t: t[1])):
            fixtures = await football_api.fetch_team_fixtures(
                team_id, settings.API_FOOTBALL_SEASON
            )
            for fx in fixtures:
                existing = await db.scalar(
                    select(TeamMatch).where(
                        TeamMatch.api_football_id == fx["api_football_id"]
                    )
                )
                if existing:
                    existing.kickoff_at = fx["kickoff_at"]
                    existing.competition = fx["competition"]
                    existing.home_team = fx["home_team"]
                    existing.away_team = fx["away_team"]
                    existing.home_score = fx["home_score"]
                    existing.away_score = fx["away_score"]
                    existing.status = fx["status"]
                    updated += 1
                else:
                    db.add(TeamMatch(**fx))
                    created += 1
            print(f"[{i + 1}/{len(teams)}] {name}: {len(fixtures)} matches")
            await asyncio.sleep(REQUEST_PAUSE_S)
        await db.commit()

    print(f"Done. Created: {created}, updated: {updated}")


if __name__ == "__main__":
    asyncio.run(main())
