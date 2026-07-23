"""Сопоставление матча его «туру».

Тур — это игровой период, обозначаемый датой начала. Схема зависит от типа
турнира:

- **суточная** (ЧМ): тур идёт с 10:00 до 10:00 следующего дня по Москве (UTC+3)
  и обозначается датой первого дня. Из-за большой разницы часовых поясов
  группировка по календарной дате UTC рвала бы единый вечер матчей на две даты.
- **недельная** (лиги — РПЛ, ЛЧ): тур = игровая неделя, обозначаемая датой
  «якорного» дня недели (для РПЛ — среда, для ЛЧ — суббота). Внутри той же
  границы 10:00 МСК: матч ночи вторника (по МСК) относится к неделе,
  начавшейся в предыдущую среду.

10:00 МСК = 07:00 UTC, поэтому «футбольный день» матча получаем сдвигом
UTC-времени начала на −7 часов и взятием календарной даты; недельный тур —
снапом этого дня назад к якорному дню недели.

Чистые функции без сайд-эффектов — юнит-тесты в tests/test_tours.py.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Граница тура: 10:00 по Москве (UTC+3).
TOUR_BOUNDARY_HOUR_MSK = 10
MSK_OFFSET_HOURS = 3
# Сдвиг UTC-времени, после которого .date() даёт «футбольный день» (10 − 3 = 7 часов).
_TOUR_SHIFT = timedelta(hours=TOUR_BOUNDARY_HOUR_MSK - MSK_OFFSET_HOURS)


def football_day(kickoff_at: datetime) -> date:
    """«Футбольный день» матча (UTC-время сдвинуто на границу 10:00 МСК).

    Матч, начинающийся в 10:00 МСК или позже, попадает в день этой даты; всё,
    что до 10:00 МСК, относится к предыдущему дню.
    """
    dt = kickoff_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.astimezone(timezone.utc) - _TOUR_SHIFT).date()


def week_start(day: date, anchor_weekday: int) -> date:
    """Дата якорного дня недели (``anchor_weekday``: Пн=0…Вс=6) на этот день
    или ближайшего предыдущего."""
    delta = (day.weekday() - anchor_weekday) % 7
    return day - timedelta(days=delta)


def tour_key(kickoff_at: datetime, anchor_weekday: int | None = None) -> date:
    """Дата тура для матча.

    ``anchor_weekday=None`` — суточная группировка (ЧМ), тождественна старому
    поведению. Иначе — недельная: «футбольный день» матча снапится назад к
    якорному дню недели.

    >>> tour_key(datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc))  # 10:00 МСК
    datetime.date(2026, 6, 12)
    >>> tour_key(datetime(2026, 6, 12, 1, 0, tzinfo=timezone.utc))  # 04:00 МСК
    datetime.date(2026, 6, 11)
    """
    day = football_day(kickoff_at)
    if anchor_weekday is None:
        return day
    return week_start(day, anchor_weekday)


def tour_date(kickoff_at: datetime) -> date:
    """Суточная дата тура (граница 10:00 МСК). Сохранена для обратной
    совместимости — эквивалентна ``tour_key(kickoff_at)``."""
    return football_day(kickoff_at)
