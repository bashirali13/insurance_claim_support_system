"""Business-day arithmetic for follow-up promises (FR-021). Weekends only; no holidays."""

from datetime import date, timedelta

SATURDAY = 5


def _is_weekend(day: date) -> bool:
    return day.weekday() >= SATURDAY


def add_business_days(start: date, n: int) -> date:
    """`n` business days after `start`. A weekend filing counts as received on Monday."""
    day = start
    while _is_weekend(day):
        day += timedelta(days=1)
    for _ in range(n):
        day += timedelta(days=1)
        while _is_weekend(day):
            day += timedelta(days=1)
    return day
