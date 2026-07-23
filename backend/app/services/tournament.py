"""Конфигурация типов турниров и скоуп матчей турнира.

Пивот от «одного глобального ЧМ» к платформе турниров: теперь каждый турнир
(комната) привязан к своей реальной лиге+сезону и видит только свой пул матчей.
`matches` остаётся общей дедуплицированной таблицей (по `api_football_id`),
но каждый матч помечен `league_id`/`season`, а турнир отбирает подмножество.

Все чтения матчей в контексте комнаты ОБЯЗАНЫ проходить через
`tournament_match_conditions(room)` / `match_belongs(room, match)` — иначе в
турнир протечёт чужая лига.
"""
from __future__ import annotations

from sqlalchemy import false, select

from app.models import Match, Room, TournamentMatch

# ---- ID лиг в API-Football ----
WORLD_CUP_LEAGUE_ID = 1
RPL_LEAGUE_ID = 235
UCL_LEAGUE_ID = 2

# Топ-5 европейских лиг.
EPL_LEAGUE_ID = 39
LALIGA_LEAGUE_ID = 140
SERIEA_LEAGUE_ID = 135
BUNDESLIGA_LEAGUE_ID = 78
LIGUE1_LEAGUE_ID = 61

# Лиги, доступные для выбора матчей в кастомном турнире (топ-5 + РПЛ + ЛЧ).
CUSTOM_LEAGUES: list[tuple[int, str]] = [
    (EPL_LEAGUE_ID, "Англия — АПЛ"),
    (LALIGA_LEAGUE_ID, "Испания — Ла Лига"),
    (SERIEA_LEAGUE_ID, "Италия — Серия A"),
    (BUNDESLIGA_LEAGUE_ID, "Германия — Бундеслига"),
    (LIGUE1_LEAGUE_ID, "Франция — Лига 1"),
    (RPL_LEAGUE_ID, "Россия — РПЛ"),
    (UCL_LEAGUE_ID, "Лига чемпионов"),
]

# Дни недели-якоря для недельной группировки туров (Пн=0…Вс=6).
_TUE = 1
_WED = 2
_SAT = 5

# Конфиг типа турнира. league_id/tour_anchor зашиты в коде (тип задаёт лигу),
# сезон и окно длительности задаёт админ при создании.
#   league_id    — лига API-Football (None у custom — матчи из разных лиг);
#   tour_anchor   — якорный день недели для туров (None = суточная группировка);
#   special_kind  — вид спецпрогноза: wc (чемпион+бомбардир) | leader (лидер
#                   лиги) | stage_or_champion (ЛЧ) | none;
#   label         — человекочитаемое название типа.
TYPE_CONFIG: dict[str, dict] = {
    "world_cup": {
        "league_id": WORLD_CUP_LEAGUE_ID,
        "tour_anchor": None,
        "special_kind": "wc",
        "label": "Чемпионат мира",
    },
    "rpl": {
        "league_id": RPL_LEAGUE_ID,
        "tour_anchor": _WED,
        "special_kind": "leader",
        "label": "Российская Премьер-лига",
    },
    "ucl": {
        "league_id": UCL_LEAGUE_ID,
        "tour_anchor": _SAT,
        "special_kind": "stage_or_champion",
        "label": "Лига чемпионов",
    },
    "custom": {
        "league_id": None,
        "tour_anchor": _SAT,
        "special_kind": "none",
        "label": "Свой турнир",
    },
}

DEFAULT_TYPE = "world_cup"


def type_config(tournament_type: str | None) -> dict:
    return TYPE_CONFIG.get(tournament_type or DEFAULT_TYPE, TYPE_CONFIG[DEFAULT_TYPE])


# league_id → якорный день недели тура (для вычисления match_date при синке).
# Схема — свойство лиги: матч принадлежит одной лиге, а все турниры над этой
# лигой используют одну и ту же схему туров.
_LEAGUE_TOUR_ANCHOR: dict[int, int | None] = {
    WORLD_CUP_LEAGUE_ID: None,  # суточная (ЧМ)
    RPL_LEAGUE_ID: _WED,
    UCL_LEAGUE_ID: _SAT,
    # Топ-5 — недельная группировка (для кастомных турниров), якорь вторник:
    # матчвик Вт→Пн покрывает уик-энд + понедельник одним туром.
    EPL_LEAGUE_ID: _TUE,
    LALIGA_LEAGUE_ID: _TUE,
    SERIEA_LEAGUE_ID: _TUE,
    BUNDESLIGA_LEAGUE_ID: _TUE,
    LIGUE1_LEAGUE_ID: _TUE,
}


def league_tour_anchor(league_id: int | None) -> int | None:
    """Якорный день недели тура для лиги; None — суточная группировка
    (и для неизвестных лиг, чтобы не менять поведение неожиданно)."""
    return _LEAGUE_TOUR_ANCHOR.get(league_id)


def tournament_match_conditions(room: Room) -> list:
    """SQLAlchemy-условия, отбирающие матчи, входящие в турнир (комнату).

    Применять как ``select(Match).where(*tournament_match_conditions(room))``
    (или после join к Match). Лиговые типы: лига+сезон (+окно дат по `match_date`,
    где match_date — метка тура). Custom — явный набор матчей из join-таблицы
    `tournament_matches`.
    """
    if room.tournament_type == "custom":
        return [
            Match.id.in_(
                select(TournamentMatch.match_id).where(
                    TournamentMatch.room_id == room.id
                )
            )
        ]
    if room.league_id is None:
        return [false()]
    conds = [Match.league_id == room.league_id]
    if room.season is not None:
        conds.append(Match.season == room.season)
    if room.starts_on is not None:
        conds.append(Match.match_date >= room.starts_on)
    if room.ends_on is not None:
        conds.append(Match.match_date <= room.ends_on)
    return conds


def match_belongs(room: Room, match: Match) -> bool:
    """Входит ли конкретный матч в турнир — для проверок после ``db.get(Match)``
    (иначе участник одного турнира мог бы прочитать матч чужой лиги по id)."""
    if room.league_id is None:
        return False
    if match.league_id != room.league_id:
        return False
    if room.season is not None and match.season != room.season:
        return False
    if room.starts_on is not None and match.match_date < room.starts_on:
        return False
    if room.ends_on is not None and match.match_date > room.ends_on:
        return False
    return True
