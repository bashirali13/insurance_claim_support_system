"""US3: business-day follow-up dates (FR-021). Weekends are skipped; holidays are not modeled."""

from datetime import date

from claim_intake.dates import add_business_days

THURSDAY = date(2026, 9, 24)
FRIDAY = date(2026, 9, 25)
SATURDAY = date(2026, 9, 26)
MONDAY = date(2026, 9, 28)
TUESDAY = date(2026, 9, 29)


def test_ac_3_8_friday_plus_one_business_day_is_monday():
    assert add_business_days(FRIDAY, 1) == MONDAY


def test_ac_3_8_thursday_plus_two_business_days_is_monday():
    assert add_business_days(THURSDAY, 2) == MONDAY


def test_ac_3_8_saturday_plus_one_business_day_is_tuesday():
    # A weekend filing is treated as received Monday, so one business day later is Tuesday.
    assert add_business_days(SATURDAY, 1) == TUESDAY
