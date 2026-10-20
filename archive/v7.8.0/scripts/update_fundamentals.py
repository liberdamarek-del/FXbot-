"""Update fundamental data (rates, yields, risk, positioning, calendar).

    python scripts/update_fundamentals.py              # last 60 days + calendar
    python scripts/update_fundamentals.py --years 12   # first run: long history
    python scripts/update_fundamentals.py --status     # only show what is stored

All sources are public and keyless (see src/fundamental/catalog.py). Every
payload is archived with its SHA-256; every value is stored with the time
it became publicly known, so backtests cannot see the future. A failing
source is reported, never replaced by an estimate.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fundamental.adapters import update_all  # noqa: E402  (loads .env first)
from src.fundamental.calendar import update_calendar  # noqa: E402
from src.fundamental.store import FUND_DB, series_summary  # noqa: E402

UTC = timezone.utc


def print_status(now: datetime) -> None:
    print("=" * 72)
    print("FUNDAMENTALNI DATA - STAV")
    print("=" * 72)

    for row in series_summary():
        age_days = (now.timestamp() - row["last_available"]) / 86400
        print(
            f"{row['series_id']:<24} {row['n']:>6} hodnot  {row['first']} .. {row['last']}"
            f"  (verejne znamo pred {age_days:.1f} d)"
        )

    print("=" * 72)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Update fundamental data.")
    parser.add_argument("--years", type=float, default=None, help="history to (re)load")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    now = datetime.now(UTC)

    if args.status:
        print_status(now)
        return 0

    start = (now - timedelta(days=365.25 * args.years)).date() if args.years else (now - timedelta(days=args.days)).date()

    print("=" * 72)
    print("FXBOT - AKTUALIZACE FUNDAMENTALNICH DAT")
    print("=" * 72)
    print(f"od: {start} | databaze: {FUND_DB}")
    failures = 0

    for result in update_all(start):
        state = "OK" if result.ok else "CHYBA"
        print(f"{result.source:<6} {state}")

        for series_id, (inserted, revised, last) in sorted(result.series.items()):
            note = f" | revize {revised}" if revised else ""
            print(f"   {series_id:<24} nove {inserted:>6} | posledni {last}{note}")

        if not result.ok:
            failures += 1
            print(f"   duvod: {result.detail[:200]}")

    calendar = update_calendar(now)

    if calendar.get("ok"):
        print(f"KALENDAR OK: {calendar['events']} udalosti (nove {calendar['new']}, zmenene {calendar['changed']})")
    else:
        failures += 1
        print(f"KALENDAR CHYBA: {calendar.get('detail')}")

    print("VYSLEDEK:", "OK" if not failures else f"{failures} zdroj(u) selhalo - ostatni data jsou ulozena")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
