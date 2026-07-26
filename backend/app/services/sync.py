"""Применение фикстур API-Football к БД.

Общая логика для планировщика (каждые 5 минут) и ручного «Синхронизировать»
в админке:

- live-матчи получают текущий счёт в home_score_ft/away_score_ft и статус
  ``live`` — фронт показывает его с меткой LIVE; очки по ним не начисляются,
  пока статус не станет ``finished`` (см. recalc.score_match);
- если итоговый счёт уже завершённого матча изменился (поздняя коррекция
  API) — ранее начисленные очки снимаются и начисляются заново.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, Room, Team, TournamentMatch
from app.services import audit, football_api
from app.services.recalc import rescore_match
from app.services.tournament import WORLD_CUP_LEAGUE_ID


async def upsert_team(db: AsyncSession, info: dict, league_id: int | None) -> None:
    """Апсерт справочника команд (id/имя/logo) из данных фикстуры."""
    tid = info.get("id")
    if not tid:
        return
    existing = await db.get(Team, tid)
    if existing:
        existing.name_en = info.get("name") or existing.name_en
        if league_id is not None:
            existing.league_id = league_id
        if info.get("logo"):
            existing.logo_url = info["logo"]
    else:
        db.add(
            Team(
                api_football_id=tid,
                name_en=info.get("name") or "",
                league_id=league_id,
                logo_url=info.get("logo"),
            )
        )


async def active_league_seasons(db: AsyncSession) -> list[tuple[int, int]]:
    """Различные (league_id, season) для синка: лиговые турниры + лиги/сезоны
    матчей, выбранных в активные кастомные турниры (чтобы их результаты тоже
    подтягивались)."""
    result: set[tuple[int, int]] = set()
    rows = (
        await db.execute(
            select(Room.league_id, Room.season)
            .where(
                Room.is_active.is_(True),
                Room.league_id.is_not(None),
                Room.season.is_not(None),
            )
            .distinct()
        )
    ).all()
    result.update((lid, season) for lid, season in rows)

    # Custom: лиги/сезоны выбранных матчей активных кастомных турниров.
    custom_rows = (
        await db.execute(
            select(Match.league_id, Match.season)
            .select_from(TournamentMatch)
            .join(Match, Match.id == TournamentMatch.match_id)
            .join(Room, Room.id == TournamentMatch.room_id)
            .where(
                Room.is_active.is_(True),
                Room.tournament_type == "custom",
                Match.league_id.is_not(None),
                Match.season.is_not(None),
            )
            .distinct()
        )
    ).all()
    result.update((lid, season) for lid, season in custom_rows)
    return list(result)


async def sync_league(db: AsyncSession, league_id: int, season: int) -> dict:
    """Синхронизировать одну лигу/сезон (для панели выбора матчей кастомного
    турнира — подтянуть фикстуры до выбора). Не коммитит."""
    fixtures = await football_api.fetch_fixtures(league_id, season, with_groups=False)
    return await apply_fixtures(db, fixtures)


async def fetch_and_apply_all(db: AsyncSession, *, with_groups: bool = True) -> dict:
    """Синхронизировать матчи по всем активным (league_id, season). Буквы групп
    (/standings) тянутся только для ЧМ. Устойчиво к сбоям: ошибка одной лиги
    (неверный сезон/недоступная лига/лимит/токен) не прерывает остальные —
    собирается в `errors`. Каждая лига обрабатывается в SAVEPOINT (begin_nested):
    сбой откатывает только её, не «отравляя» общую транзакцию и не сбрасывая
    (expire) объекты вызывающего. КОММИТ делает вызывающий."""
    total: dict = {"created": 0, "updated": 0, "rescored": 0, "errors": []}
    league_seasons = await active_league_seasons(db)
    for league_id, season in league_seasons:
        use_groups = with_groups and league_id == WORLD_CUP_LEAGUE_ID
        try:
            async with db.begin_nested():
                fixtures = await football_api.fetch_fixtures(
                    league_id, season, with_groups=use_groups
                )
                stats = await apply_fixtures(db, fixtures)
            for k in ("created", "updated", "rescored"):
                total[k] += stats[k]
        except Exception as exc:
            total["errors"].append(f"лига {league_id}/{season}: {exc}")
    return total


async def apply_fixtures(db: AsyncSession, fixtures: list[dict]) -> dict:
    """Upsert fixtures into the matches table. Returns counters for the
    audit log / admin UI. Does not commit."""
    created, updated, rescored = 0, 0, 0
    for fx in fixtures:
        # Инфо о командах — в справочник teams, из dict матча убираем.
        teams_info = fx.pop("_teams", None) or []
        for t in teams_info:
            await upsert_team(db, t, fx.get("league_id"))

        existing = await db.scalar(
            select(Match).where(Match.api_football_id == fx["api_football_id"])
        )
        if not existing:
            match = Match(**fx)
            db.add(match)
            created += 1
            if fx["status"] == "finished":
                await db.flush()
                await audit.log_match_result(
                    db,
                    match_id=match.id,
                    home_team=match.home_team,
                    away_team=match.away_team,
                    new_home=fx["home_score_ft"],
                    new_away=fx["away_score_ft"],
                    prev_home=None,
                    prev_away=None,
                )
            continue

        prev_status = existing.status
        prev_home, prev_away = existing.home_score_ft, existing.away_score_ft

        existing.kickoff_at = fx["kickoff_at"]
        existing.match_date = fx["match_date"]
        existing.league_id = fx["league_id"]
        existing.season = fx["season"]
        existing.round = fx["round"]
        existing.stage = fx["stage"]
        if fx.get("group_name"):
            existing.group_name = fx["group_name"]
        existing.home_team = fx["home_team"]
        existing.away_team = fx["away_team"]
        existing.status = fx["status"]
        if fx["status"] in ("live", "finished"):
            existing.home_score_ft = fx["home_score_ft"]
            existing.away_score_ft = fx["away_score_ft"]
        # Победитель (для чемпиона при ничьей в финале) появляется только у
        # завершённого матча — не затираем его live-обновлениями.
        if fx["status"] == "finished" and fx.get("winner_team"):
            existing.winner_team = fx["winner_team"]

        if (existing.status, existing.home_score_ft, existing.away_score_ft) != (
            prev_status,
            prev_home,
            prev_away,
        ):
            updated += 1

        if fx["status"] == "finished":
            was_finished = prev_status == "finished"
            # До завершения в prev лежал live-счёт — для журнала это не
            # «предыдущий результат», поэтому передаём его только если матч
            # уже был завершён.
            await audit.log_match_result(
                db,
                match_id=existing.id,
                home_team=existing.home_team,
                away_team=existing.away_team,
                new_home=fx["home_score_ft"],
                new_away=fx["away_score_ft"],
                prev_home=prev_home if was_finished else None,
                prev_away=prev_away if was_finished else None,
            )
            if was_finished and (prev_home, prev_away) != (
                fx["home_score_ft"],
                fx["away_score_ft"],
            ):
                await rescore_match(db, existing)
                rescored += 1

    return {"created": created, "updated": updated, "rescored": rescored}
