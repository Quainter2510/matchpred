"""Юнит-тесты пивота на турниры (без БД): недельная группировка туров и
скоуп матчей по турниру."""
from datetime import date, datetime, timezone

from app.models import Match, Room
from app.services.tournament import (
    RPL_LEAGUE_ID,
    UCL_LEAGUE_ID,
    WORLD_CUP_LEAGUE_ID,
    league_tour_anchor,
    match_belongs,
)
from app.services.tours import tour_key

WED = 2
SAT = 5


def _utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class TestWeeklyTourKey:
    def test_saturday_match_belongs_to_week_starting_wednesday(self):
        # Сб 07.03.2026 15:00 МСК (12:00 UTC) → неделя со среды 04.03.
        assert tour_key(_utc(2026, 3, 7, 12), WED) == date(2026, 3, 4)

    def test_wednesday_after_boundary_starts_new_week(self):
        # Ср 11.03 13:00 МСК (10:00 UTC) — начало новой недели.
        assert tour_key(_utc(2026, 3, 11, 10), WED) == date(2026, 3, 11)

    def test_tuesday_night_belongs_to_previous_wednesday(self):
        # Вт 10.03 22:00 МСК (19:00 UTC) → всё ещё неделя со среды 04.03.
        assert tour_key(_utc(2026, 3, 10, 19), WED) == date(2026, 3, 4)

    def test_early_wednesday_before_boundary_is_previous_week(self):
        # Ср 11.03 05:00 МСК (02:00 UTC), до 10:00 МСК → неделя со среды 04.03.
        assert tour_key(_utc(2026, 3, 11, 2), WED) == date(2026, 3, 4)

    def test_ucl_saturday_anchor(self):
        # ЛЧ, якорь суббота: Вт 17.02 22:00 МСК (19:00 UTC) → неделя с сб 14.02.
        assert tour_key(_utc(2026, 2, 17, 19), SAT) == date(2026, 2, 14)

    def test_none_anchor_is_daily(self):
        # anchor=None — суточная группировка (ЧМ), как раньше.
        assert tour_key(_utc(2026, 6, 12, 7), None) == date(2026, 6, 12)


class TestLeagueTourAnchor:
    def test_wc_is_daily(self):
        assert league_tour_anchor(WORLD_CUP_LEAGUE_ID) is None

    def test_rpl_is_wednesday(self):
        assert league_tour_anchor(RPL_LEAGUE_ID) == WED

    def test_ucl_is_saturday(self):
        assert league_tour_anchor(UCL_LEAGUE_ID) == SAT

    def test_unknown_league_is_daily(self):
        assert league_tour_anchor(99999) is None


def _room(**kw) -> Room:
    r = Room()
    r.league_id = kw.get("league_id")
    r.season = kw.get("season")
    r.starts_on = kw.get("starts_on")
    r.ends_on = kw.get("ends_on")
    r.tournament_type = kw.get("tournament_type", "rpl")
    return r


def _match(league_id, season, match_date) -> Match:
    m = Match()
    m.league_id = league_id
    m.season = season
    m.match_date = match_date
    return m


class TestMatchBelongs:
    def test_league_and_season_match(self):
        room = _room(league_id=RPL_LEAGUE_ID, season=2025)
        m = _match(RPL_LEAGUE_ID, 2025, date(2026, 3, 4))
        assert match_belongs(room, m)

    def test_wrong_league_excluded(self):
        room = _room(league_id=RPL_LEAGUE_ID, season=2025)
        m = _match(UCL_LEAGUE_ID, 2025, date(2026, 3, 4))
        assert not match_belongs(room, m)

    def test_wrong_season_excluded(self):
        room = _room(league_id=RPL_LEAGUE_ID, season=2025)
        m = _match(RPL_LEAGUE_ID, 2024, date(2026, 3, 4))
        assert not match_belongs(room, m)

    def test_before_window_excluded(self):
        room = _room(league_id=RPL_LEAGUE_ID, season=2025, starts_on=date(2026, 3, 4))
        m = _match(RPL_LEAGUE_ID, 2025, date(2026, 2, 25))
        assert not match_belongs(room, m)

    def test_after_window_excluded(self):
        room = _room(league_id=RPL_LEAGUE_ID, season=2025, ends_on=date(2026, 3, 4))
        m = _match(RPL_LEAGUE_ID, 2025, date(2026, 3, 11))
        assert not match_belongs(room, m)

    def test_inside_window_included(self):
        room = _room(
            league_id=RPL_LEAGUE_ID,
            season=2025,
            starts_on=date(2026, 3, 4),
            ends_on=date(2026, 4, 1),
        )
        m = _match(RPL_LEAGUE_ID, 2025, date(2026, 3, 18))
        assert match_belongs(room, m)

    def test_custom_without_league_excluded(self):
        # custom (league_id None) — join-таблица (фаза 3); пока пустой набор.
        room = _room(league_id=None, season=None, tournament_type="custom")
        m = _match(RPL_LEAGUE_ID, 2025, date(2026, 3, 4))
        assert not match_belongs(room, m)
