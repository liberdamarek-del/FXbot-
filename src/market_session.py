"""FX market session detection.

The interbank FX market is open continuously from Sunday 17:00 to Friday
17:00 New York time. In UTC this is:

    summer (US DST, EDT = UTC-4): Sunday 21:00 UTC -> Friday 21:00 UTC
    winter (EST = UTC-5):         Sunday 22:00 UTC -> Friday 22:00 UTC

The previous implementation used a fixed 22:00 UTC boundary, which is wrong
for the whole summer period (about March to November) and produced false
MISSING_DATA gaps over every weekend.

US daylight saving time is implemented directly (no tz database required,
so it works in Termux without the tzdata package):

    starts: second Sunday of March, 02:00 EST  = 07:00 UTC
    ends:   first Sunday of November, 02:00 EDT = 06:00 UTC

The rule is valid for years >= 2007.

KNOWN LIMITATIONS (NEOVERENO - not verified against provider data):
- Public holidays (Christmas Day, New Year's Day) with reduced or no
  trading are not modelled.
- The exact first/last bar time around the weekend depends on the data
  provider. Use scripts/check_weekend_boundary.py after the first weekend
  of collected data to compare the rule with real bars.
"""

from datetime import datetime, timedelta, timezone


NY_CLOSE_MINUTE_OF_DAY = 17 * 60  # 17:00 New York local time


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> int:
    """Return the day of month of the n-th given weekday (Mon=0 ... Sun=6)."""
    first = datetime(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return 1 + offset + 7 * (n - 1)


def us_dst_bounds_utc(year: int) -> tuple[datetime, datetime]:
    """Return (dst_start_utc, dst_end_utc) for the given year."""
    start_day = _nth_weekday_of_month(year, 3, 6, 2)  # 2nd Sunday of March
    end_day = _nth_weekday_of_month(year, 11, 6, 1)  # 1st Sunday of November

    start = datetime(year, 3, start_day, 7, 0, tzinfo=timezone.utc)
    end = datetime(year, 11, end_day, 6, 0, tzinfo=timezone.utc)

    return start, end


def new_york_utc_offset(timestamp: datetime) -> timedelta:
    """UTC offset of New York at the given aware timestamp."""
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must contain timezone information")

    utc = timestamp.astimezone(timezone.utc)
    start, end = us_dst_bounds_utc(utc.year)

    if start <= utc < end:
        return timedelta(hours=-4)

    return timedelta(hours=-5)


def is_fx_market_open(timestamp: datetime) -> bool:
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must contain timezone information")

    utc = timestamp.astimezone(timezone.utc)
    local = utc + new_york_utc_offset(utc)

    weekday = local.weekday()
    minute_of_day = local.hour * 60 + local.minute

    if weekday == 5:  # Saturday (New York)
        return False

    if weekday == 6 and minute_of_day < NY_CLOSE_MINUTE_OF_DAY:
        # Sunday before the weekly open
        return False

    if weekday == 4 and minute_of_day >= NY_CLOSE_MINUTE_OF_DAY:
        # Friday from the weekly close
        return False

    return True
