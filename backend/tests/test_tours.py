from datetime import date, datetime, timezone

from app.services.tours import tour_date


class TestTourDate:
    def test_boundary_belongs_to_same_day(self):
        # ровно 10:00 МСК = 07:00 UTC — начало тура этого дня
        assert tour_date(datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc)) == date(
            2026, 6, 12
        )

    def test_just_before_boundary_belongs_to_previous_day(self):
        # 09:59 МСК = 06:59 UTC — ещё предыдущий тур
        assert tour_date(datetime(2026, 6, 12, 6, 59, tzinfo=timezone.utc)) == date(
            2026, 6, 11
        )

    def test_late_night_match_groups_with_previous_day(self):
        # вечерний матч в Америке: 04:00 МСК (01:00 UTC) среды — тур вторника
        assert tour_date(datetime(2026, 6, 17, 1, 0, tzinfo=timezone.utc)) == date(
            2026, 6, 16
        )

    def test_afternoon_match_same_day(self):
        # 20:00 МСК (17:00 UTC) — тур того же дня
        assert tour_date(datetime(2026, 6, 16, 17, 0, tzinfo=timezone.utc)) == date(
            2026, 6, 16
        )

    def test_naive_datetime_treated_as_utc(self):
        assert tour_date(datetime(2026, 6, 12, 7, 0)) == date(2026, 6, 12)
