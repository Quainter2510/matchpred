"""Async client for API-Football (api-sports.io v3).

Only fields used by the MVP are mapped. Extra time / penalties are ignored —
we store the main-time (FT) score only.
"""
import re
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services import players_catalog
from app.services.tours import tour_date

# Настоящая группа в /standings называется "Group A".."Group L". Кроме них там
# бывают служебные таблицы вроде "Ranking of third-placed teams" — их игнорируем.
_GROUP_RE = re.compile(r"^group\s+([a-z0-9]{1,3})$", re.IGNORECASE)

_STATUS_MAP = {
    "TBD": "scheduled",
    "NS": "scheduled",
    "1H": "live",
    "HT": "live",
    "2H": "live",
    "ET": "live",
    "P": "live",
    "BT": "live",
    "LIVE": "live",
    "FT": "finished",
    "AET": "finished",
    "PEN": "finished",
    "PST": "cancelled",
    "CANC": "cancelled",
    "ABD": "cancelled",
    "AWD": "finished",
    "WO": "finished",
}


def _headers() -> dict:
    return {"x-apisports-key": settings.API_FOOTBALL_KEY}


async def _get(path: str, params: dict) -> dict:
    async with httpx.AsyncClient(
        base_url=settings.API_FOOTBALL_BASE, timeout=20
    ) as client:
        resp = await client.get(path, params=params, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        # api-sports returns HTTP 200 with a non-empty `errors` field on
        # auth/quota/parameter problems. Surface it instead of returning [].
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-Football error: {errors}")
        return data


def _normalize_fixture(fx: dict, groups: dict[str, str] | None = None) -> dict:
    fixture = fx["fixture"]
    teams = fx["teams"]
    league = fx.get("league", {})

    # `goals` у API-Football включает дополнительное время (AET/PEN) — нам нужен
    # счёт только основного времени (90 мин), он лежит в score.fulltime.
    # Fallback на goals: до конца матча (1H/2H) и для технических результатов
    # (AWD/WO) fulltime может быть пустым.
    goals = fx.get("goals") or {}
    fulltime = (fx.get("score") or {}).get("fulltime") or {}
    if fulltime.get("home") is not None and fulltime.get("away") is not None:
        home_score, away_score = fulltime["home"], fulltime["away"]
    else:
        home_score, away_score = goals.get("home"), goals.get("away")
    kickoff = datetime.fromisoformat(fixture["date"]).astimezone(timezone.utc)
    raw_status = fixture.get("status", {}).get("short", "NS")
    stage = (league.get("round") or "group").lower().replace(" ", "_")[:40]
    home = teams["home"]["name"]
    away = teams["away"]["name"]
    # Буква группы есть только у матчей группового этапа — берём из таблицы групп
    # (раунд из API содержит лишь номер тура, напр. "group_stage_-_1").
    group_name = None
    if groups and "group" in stage:
        group_name = groups.get(home) or groups.get(away)
    # Победитель матча (флаг teams.*.winner учитывает пенальти/допвремя). Нужен
    # для начисления чемпиона по финалу при ничьей в основное время. У ничьих
    # без серии пенальти (группы) оба флага false/null — победителя нет.
    if teams["home"].get("winner"):
        winner_team = home
    elif teams["away"].get("winner"):
        winner_team = away
    else:
        winner_team = None
    return {
        "api_football_id": fixture["id"],
        "kickoff_at": kickoff,
        "match_date": tour_date(kickoff),
        "stage": stage,
        "group_name": group_name,
        "home_team": home,
        "away_team": away,
        "home_score_ft": home_score,
        "away_score_ft": away_score,
        "winner_team": winner_team,
        "status": _STATUS_MAP.get(raw_status, "scheduled"),
    }


async def fetch_groups() -> dict[str, str]:
    """Сопоставление «название сборной → буква группы» из /standings.

    Раунд матча в API содержит только номер тура, без буквы группы, поэтому
    группу берём из турнирной таблицы. Возвращает {} при недоступности данных
    (например, до жеребьёвки) — тогда матчи останутся без group_name.
    """
    try:
        data = await _get(
            "/standings",
            {
                "league": settings.API_FOOTBALL_LEAGUE_ID,
                "season": settings.API_FOOTBALL_SEASON,
            },
        )
    except Exception:
        return {}
    out: dict[str, str] = {}
    for league in data.get("response", []):
        for group in league.get("league", {}).get("standings", []) or []:
            for row in group:
                m = _GROUP_RE.match((row.get("group") or "").strip())
                if not m:
                    continue
                team = (row.get("team") or {}).get("name")
                if team:
                    out[team] = m.group(1).upper()
    return out


async def fetch_fixtures(with_groups: bool = True) -> list[dict]:
    """All fixtures for the configured league + season.

    with_groups=False пропускает запрос /standings (буквы групп) — так
    5-минутный live-опрос стоит один запрос к API вместо двух. Группы у уже
    созданных матчей при этом не затираются (apply_fixtures обновляет
    group_name только когда он есть в данных).
    """
    data = await _get(
        "/fixtures",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    groups = await fetch_groups() if with_groups else None
    return [_normalize_fixture(fx, groups) for fx in data.get("response", [])]


async def fetch_wc_team_ids() -> dict[int, str]:
    """ID сборных-участниц ЧМ → название. Берём из фикстур турнира (там есть
    teams.home.id / teams.away.id), отдельный запрос /teams не нужен."""
    data = await _get(
        "/fixtures",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    out: dict[int, str] = {}
    for fx in data.get("response", []):
        for side in ("home", "away"):
            team = fx.get("teams", {}).get(side, {})
            tid, name = team.get("id"), team.get("name")
            # Плейсхолдеры плей-офф (TBD) приходят без id.
            if tid and name:
                out[tid] = name
    return out


async def fetch_top_scorers() -> list[dict]:
    """Бомбардиры турнира (лига+сезон) по убыванию голов. До первых забитых
    мячей API может вернуть пустой список."""
    data = await _get(
        "/players/topscorers",
        {
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    out: list[dict] = []
    for item in data.get("response", []):
        player = item.get("player", {})
        pid = player.get("id")
        if not pid:
            continue
        stats = (item.get("statistics") or [{}])[0]
        goals = (stats.get("goals") or {}).get("total") or 0
        team = (stats.get("team") or {}).get("name") or player.get("nationality")
        name = player.get("name") or " ".join(
            filter(None, [player.get("firstname"), player.get("lastname")])
        )
        out.append(
            {
                "api_id": pid,
                "name": name,
                "photo": player.get("photo"),
                "team": team,
                "goals": goals,
            }
        )
    return out


async def fetch_player_goals(player_id: int) -> dict | None:
    """Статистика одного игрока в турнире (лига+сезон) в формате строки
    снимка бомбардиров: {api_id, name, photo, team, goals}. None, если у API
    нет данных по игроку в этом турнире."""
    data = await _get(
        "/players",
        {
            "id": player_id,
            "league": settings.API_FOOTBALL_LEAGUE_ID,
            "season": settings.API_FOOTBALL_SEASON,
        },
    )
    resp = data.get("response") or []
    if not resp:
        return None
    item = resp[0]
    player = item.get("player", {})
    stats = (item.get("statistics") or [{}])[0]
    goals = (stats.get("goals") or {}).get("total") or 0
    team = (stats.get("team") or {}).get("name") or player.get("nationality")
    name = player.get("name") or " ".join(
        filter(None, [player.get("firstname"), player.get("lastname")])
    )
    return {
        "api_id": player.get("id", player_id),
        "name": name,
        "photo": player.get("photo"),
        "team": team,
        "goals": goals,
    }


def _name_tokens(s: str) -> set[str]:
    return {
        players_catalog.normalize_name(w)
        for w in re.split(r"[\s.\-']+", s.strip())
        if len(w) > 1
    }


async def resolve_player_id(
    catalog_name: str, nationality: str | None
) -> int | None:
    """Реальный API-ID игрока по каталожному имени «Русское (Latin Name)».

    Ищем по последнему слову латинского имени через /players/profiles;
    кандидат подходит, если все токены латинского имени встречаются в его
    профиле (name + firstname + lastname). При нескольких кандидатах —
    фильтр по гражданству."""
    m = re.search(r"\(([^)]+)\)", catalog_name)
    latin = m.group(1) if m else catalog_name
    tokens = _name_tokens(latin)
    if not tokens:
        return None
    surname = latin.strip().split()[-1]

    data = await _get("/players/profiles", {"search": surname})
    candidates = []
    for item in data.get("response", []):
        player = item.get("player", {})
        hay = _name_tokens(
            " ".join(
                filter(
                    None,
                    [player.get("name"), player.get("firstname"), player.get("lastname")],
                )
            )
        )
        if player.get("id") and tokens <= hay:
            candidates.append(player)
    if not candidates:
        return None
    if nationality and len(candidates) > 1:
        nat = players_catalog.normalize_name(nationality)
        same_nat = [
            p
            for p in candidates
            if players_catalog.normalize_name(p.get("nationality") or "") == nat
        ]
        if same_nat:
            candidates = same_nat
    return candidates[0].get("id")


async def fetch_team_fixtures(team_id: int, season: int) -> list[dict]:
    """Все матчи команды за сезон (год) во всех турнирах — для справочника
    team_matches (форма сборных). Матчи нашего ЧМ (league = настроенная лига)
    отфильтровываются: они живут в `matches` и подмешиваются при чтении."""
    data = await _get("/fixtures", {"team": team_id, "season": season})
    out = []
    for fx in data.get("response", []):
        league = fx.get("league", {})
        if league.get("id") == settings.API_FOOTBALL_LEAGUE_ID:
            continue
        fixture = fx["fixture"]
        goals = fx.get("goals", {})
        raw_status = fixture.get("status", {}).get("short", "NS")
        out.append(
            {
                "api_football_id": fixture["id"],
                "kickoff_at": datetime.fromisoformat(fixture["date"]).astimezone(
                    timezone.utc
                ),
                "competition": league.get("name"),
                "home_team": fx["teams"]["home"]["name"],
                "away_team": fx["teams"]["away"]["name"],
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "status": _STATUS_MAP.get(raw_status, "scheduled"),
            }
        )
    return out


# Бомбардир — это почти всегда нападающий, реже полузащитник. Поднимаем таких
# кандидатов наверх списка, чтобы не тонуть в защитниках/вратарях.
_POSITION_RANK = {"Attacker": 0, "Midfielder": 1, "Defender": 2, "Goalkeeper": 3}
_SEARCH_LIMIT = 20


async def search_players(query: str) -> list[dict]:
    """Player autocomplete for the top-scorer special prediction.

    Uses the name-based `/players/profiles` endpoint instead of
    `/players?league=&season=`: before the tournament the WC league/season has
    no squads loaded, so a league/season-scoped search returns nothing. Profile
    search works by surname across all of API-Football's player database.

    Результат сортируется по позиции (нападающие выше) и обрезается до
    _SEARCH_LIMIT, иначе кандидатов слишком много.

    Сначала отдаём кураторский список фаворитов (с поиском по-русски), затем —
    живые результаты из API. До турнира у лиги ЧМ нет составов, поэтому API
    может вернуть пусто; кураторский список работает всегда.
    """
    curated = players_catalog.search_curated(query)
    seen: set[int] = {p["api_id"] for p in curated}

    try:
        data = await _get("/players/profiles", {"search": query})
    except Exception:
        # Live search is best-effort; curated favourites still come back.
        return curated[:_SEARCH_LIMIT]

    ranked: list[tuple] = []
    for item in data.get("response", []):
        player = item.get("player", {})
        pid = player.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        name = player.get("name") or " ".join(
            filter(None, [player.get("firstname"), player.get("lastname")])
        )
        rank = _POSITION_RANK.get(player.get("position"), 4)
        ranked.append(
            (
                rank,
                (name or "").lower(),
                {
                    "api_id": pid,
                    "name": name,
                    "team": player.get("nationality"),
                    "photo": player.get("photo"),
                },
            )
        )
    ranked.sort(key=lambda t: (t[0], t[1]))
    live = [d for _, _, d in ranked]
    # Curated favourites first, then live API results, capped at the limit.
    return (curated + live)[:_SEARCH_LIMIT]
