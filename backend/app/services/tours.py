"""Сопоставление матча его «туру».

Тур — это «футбольный день», идущий с 10:00 до 10:00 следующего дня по Москве
(UTC+3), и обозначаемый датой первого дня. Из-за большой разницы часовых поясов
с площадками ЧМ-2026 группировка по календарной дате UTC рвала бы единый вечер
матчей на две даты — поэтому дату тура считаем по этой границе.

10:00 МСК = 07:00 UTC, поэтому дату тура получаем сдвигом UTC-времени начала
матча на −7 часов и взятием календарной даты.

Чистая функция без сайд-эффектов — юнит-тесты в tests/test_tours.py.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Граница тура: 10:00 по Москве (UTC+3).
TOUR_BOUNDARY_HOUR_MSK = 10
MSK_OFFSET_HOURS = 3
# Сдвиг UTC-времени, после которого .date() даёт дату тура (10 − 3 = 7 часов).
_TOUR_SHIFT = timedelta(hours=TOUR_BOUNDARY_HOUR_MSK - MSK_OFFSET_HOURS)


def tour_date(kickoff_at: datetime) -> date:
    """Дата тура для матча с началом ``kickoff_at`` (UTC).

    Матч, начинающийся в 10:00 МСК или позже, попадает в тур этого дня; всё, что
    до 10:00 МСК, относится к туру предыдущего дня.

    >>> tour_date(datetime(2026, 6, 12, 7, 0, tzinfo=timezone.utc))  # 10:00 МСК
    datetime.date(2026, 6, 12)
    >>> tour_date(datetime(2026, 6, 12, 1, 0, tzinfo=timezone.utc))  # 04:00 МСК
    datetime.date(2026, 6, 11)
    """
    dt = kickoff_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.astimezone(timezone.utc) - _TOUR_SHIFT).date()
