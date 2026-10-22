"""FXBOT - on-demand data update.

    python scripts/update_data.py              # fetch what is missing, show state
    python scripts/update_data.py --status     # only show state (no API calls)
    python scripts/update_data.py --days 30    # also make sure 30 days of history exist
    python scripts/update_data.py --repair     # also try to repair gaps
    python scripts/update_data.py --symbols EUR/USD --timeframes 1min

Fetches only the 1-minute bars that are missing since the newest stored bar
(one request returns up to about 4500 bars). When the data is already
complete, no API credit is spent. The longer timeframes (5min, 15min, 1h)
are derived locally from the 1-minute bars and cost no credit.

Instruments come from COLLECTOR_SYMBOLS / COLLECTOR_TIMEFRAMES in the
environment or .env (default: 7 major pairs + 5 crosses, 1min). Derived
timeframes come from DERIVED_TIMEFRAMES (default 5min,15min,1h).

Exit code 0 = every instrument is CURRENT or CLOSED (weekend), 1 = problem.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_state import DataState, get_status  # noqa: E402  (loads .env first)
from src.data_update import (  # noqa: E402
    DEFAULT_DERIVED_TIMEFRAMES,
    DEFAULT_SYMBOLS,
    DEFAULT_TIMEFRAMES,
    format_report,
    format_status_line,
    update_all,
)
from src.database import initialize_database  # noqa: E402
from src.resample import DERIVED_SOURCE, FULL_SCAN, derive_symbol  # noqa: E402
from src.twelve_data import TwelveDataFeed  # noqa: E402

GOOD_STATES = (DataState.CURRENT, DataState.CLOSED)


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _option(argv: list[str], name: str) -> str | None:
    if name in argv:
        index = argv.index(name)

        if index + 1 >= len(argv):
            raise SystemExit(f"{name} needs a value")

        return argv[index + 1]

    return None


def build_instruments(argv: list[str]) -> list[tuple[str, str]]:
    symbols = _split(
        _option(argv, "--symbols")
        or os.getenv("COLLECTOR_SYMBOLS", DEFAULT_SYMBOLS)
    )
    timeframes = _split(
        _option(argv, "--timeframes")
        or os.getenv("COLLECTOR_TIMEFRAMES", DEFAULT_TIMEFRAMES)
    )

    if not symbols or not timeframes:
        raise SystemExit("at least one symbol and one timeframe are required")

    return [(s, t) for s in symbols for t in timeframes]


def derived_timeframes() -> list[str]:
    return _split(os.getenv("DERIVED_TIMEFRAMES", DEFAULT_DERIVED_TIMEFRAMES))


def history_days(argv: list[str]) -> int | None:
    value = _option(argv, "--days")

    if value is None:
        return None

    try:
        days = int(value)
    except ValueError:
        raise SystemExit("--days needs a whole number") from None

    if not 1 <= days <= 3650:
        raise SystemExit("--days must be between 1 and 3650")

    return days


def derive_report(
    instruments: list[tuple[str, str]],
    full: bool = False,
) -> list[str]:
    targets = derived_timeframes()
    lines = []

    if not targets:
        return lines

    symbols = []

    for symbol, timeframe in instruments:
        if timeframe == "1min" and symbol not in symbols:
            symbols.append(symbol)

    if symbols:
        lines.append("ODVOZENE CASOVE RAMCE (zdarma, z 1min):")

    for symbol in symbols:
        results = derive_symbol(
            symbol, targets, since=FULL_SCAN if full else None
        )
        parts = [f"{r.timeframe} +{r.created}" for r in results]
        holes = sum(r.incomplete for r in results)
        line = f"  {symbol}: " + ", ".join(parts)

        if holes:
            line += f" | neuplna okna {holes} (diry v 1min datech - pomuze --repair)"

        lines.append(line)

    return lines


def main(argv: list[str], feed=None) -> int:
    instruments = build_instruments(argv)
    now = datetime.now(timezone.utc)

    initialize_database()

    if "--status" in argv:
        print("=" * 60)
        print("FXBOT - STAV DAT (bez volani API)")
        print("=" * 60)
        print(f"cas (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")

        bad = 0
        targets = derived_timeframes()

        for symbol, timeframe in instruments:
            status = get_status(symbol, timeframe, now=now)
            print(format_status_line(status))

            if status.state not in GOOD_STATES:
                bad += 1

            if timeframe == "1min" and targets:
                derived = [
                    f"{tf} {get_status(symbol, tf, DERIVED_SOURCE, now).state.value}"
                    for tf in targets
                ]
                print("    odvozene: " + ", ".join(derived))

        print("=" * 60)
        return 0 if bad == 0 else 1

    api_key = os.getenv("TWELVE_DATA_API_KEY", "demo")

    if api_key == "demo":
        print("POZOR: pouzivate sdileny klic 'demo'. Limity nejsou spolehlive.")
        print("       Zdarma vlastni klic: python scripts/set_api_key.py")
        print()

    if feed is None:
        feed = TwelveDataFeed(api_key=api_key, timeout=15)

    days = history_days(argv)

    results = update_all(feed, instruments, now=now, history_days=days)

    print(format_report(results, now, feed.budget.status()))

    # after older history was added, build the older windows too
    for line in derive_report(instruments, full=days is not None):
        print(line)

    if "--repair" in argv:
        from src.history_manager import check_and_repair

        print("\nOPRAVA MEZER:")

        for symbol, timeframe in instruments:
            outcome = check_and_repair(feed, symbol, timeframe)
            print(
                f"  {symbol} {timeframe}: nalezeno {outcome['missing_gaps']}, "
                f"opraveno {outcome['repaired']}, "
                f"zbyva {outcome['remaining_missing_gaps']} -> "
                f"{outcome['verification']}"
            )

    problems = [
        r for r in results
        if r.error or r.after is None or r.after.state not in GOOD_STATES
    ]

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
