"""Unit tests for the simulation overlay (no DB required)."""
import uuid
from datetime import datetime, timedelta, timezone

from app.models import Match, Room
from app.services.simulation import (
    SimContext,
    effective_result,
    fake_score,
    parse_sim_now,
    points_for,
)

NOW = datetime(2026, 6, 20, 18, 0, tzinfo=timezone.utc)


def make_match(*, kickoff_at, status="scheduled", home=None, away=None, multiplier=1):
    return Match(
        id=uuid.uuid4(),
        match_date=kickoff_at.date(),
        kickoff_at=kickoff_at,
        stage="group_stage",
        home_team="AAA",
        away_team="BBB",
        status=status,
        home_score_ft=home,
        away_score_ft=away,
        points_multiplier=multiplier,
    )


def make_room(**points):
    return Room(
        id=uuid.uuid4(),
        name="test",
        password_hash="x",
        first_match_at=NOW,
        points_exact=points.get("points_exact", 5),
        points_diff=points.get("points_diff", 2),
        points_outcome=points.get("points_outcome", 1),
        points_champion=10,
        points_scorer=10,
    )


# ---------------- parse_sim_now ----------------
def test_parse_sim_now_iso_z():
    assert parse_sim_now("2026-06-20T18:00:00Z") == NOW


def test_parse_sim_now_naive_becomes_utc():
    assert parse_sim_now("2026-06-20T18:00:00") == NOW


def test_parse_sim_now_garbage_and_empty():
    assert parse_sim_now("not-a-date") is None
    assert parse_sim_now(None) is None
    assert parse_sim_now("") is None


def test_sim_context_active():
    assert not SimContext().active
    assert SimContext(now=NOW).active


# ---------------- fake_score ----------------
def test_fake_score_deterministic_and_bounded():
    mid = uuid.uuid4()
    assert fake_score(mid) == fake_score(mid)
    home, away = fake_score(mid)
    assert 0 <= home <= 3 and 0 <= away <= 3


# ---------------- effective_result ----------------
def test_future_match_unchanged():
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW + timedelta(hours=1))
    assert effective_result(m, sim) == ("scheduled", None, None)


def test_just_kicked_off_match_is_live_from_zero():
    """В первые минуты матч идёт (live) и счёт начинается с 0:0 — очков нет."""
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW - timedelta(minutes=5))
    status, home, away = effective_result(m, sim)
    assert status == "live"
    final_home, final_away = fake_score(m.id)
    assert 0 <= home <= final_home and 0 <= away <= final_away
    # очки за live-матч не начисляются
    assert points_for(home, away, m, make_room(), sim) == (None, None)


def test_match_finishes_after_duration():
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW - timedelta(hours=3))
    status, home, away = effective_result(m, sim)
    assert status == "finished"
    assert (home, away) == fake_score(m.id)


def test_real_result_always_wins():
    sim = SimContext(now=NOW)
    m = make_match(
        kickoff_at=NOW - timedelta(days=1), status="finished", home=2, away=1
    )
    assert effective_result(m, sim) == ("finished", 2, 1)


def test_real_live_score_kept_while_playing():
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW - timedelta(minutes=30), status="live", home=1, away=0)
    assert effective_result(m, sim) == ("live", 1, 0)


def test_real_live_score_becomes_final_after_duration():
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW - timedelta(hours=3), status="live", home=1, away=0)
    assert effective_result(m, sim) == ("finished", 1, 0)


def test_inactive_sim_returns_reality():
    m = make_match(kickoff_at=NOW - timedelta(hours=1))
    assert effective_result(m, SimContext()) == ("scheduled", None, None)


# ---------------- points_for ----------------
def test_points_none_until_simulated_finish():
    sim = SimContext(now=NOW)
    # будущий матч
    m = make_match(kickoff_at=NOW + timedelta(hours=1))
    assert points_for(1, 0, m, make_room(), sim) == (None, None)
    # идущий матч (live-окно) — очков тоже ещё нет
    m_live = make_match(kickoff_at=NOW - timedelta(minutes=30))
    assert points_for(1, 0, m_live, make_room(), sim) == (None, None)


def test_points_use_room_rules_and_real_result():
    sim = SimContext(now=NOW)
    m = make_match(
        kickoff_at=NOW - timedelta(days=1), status="finished", home=2, away=1
    )
    room = make_room(points_exact=7, points_diff=3, points_outcome=2)
    assert points_for(2, 1, m, room, sim) == (7, True)   # exact
    assert points_for(3, 2, m, room, sim) == (3, False)  # diff
    assert points_for(1, 0, m, room, sim) == (3, False)  # same diff
    assert points_for(5, 1, m, room, sim) == (2, False)  # outcome
    assert points_for(0, 1, m, room, sim) == (0, False)  # miss


def test_points_apply_multiplier_and_zero_voids_exact():
    sim = SimContext(now=NOW)
    m = make_match(
        kickoff_at=NOW - timedelta(days=1),
        status="finished",
        home=2,
        away=1,
        multiplier=3,
    )
    assert points_for(2, 1, m, make_room(), sim) == (15, True)

    m.points_multiplier = 0
    assert points_for(2, 1, m, make_room(), sim) == (0, False)


def test_points_for_fake_result_consistent_with_effective():
    sim = SimContext(now=NOW)
    m = make_match(kickoff_at=NOW - timedelta(hours=3))
    _, home, away = effective_result(m, sim)
    points, is_exact = points_for(home, away, m, make_room(), sim)
    assert (points, is_exact) == (5, True)
