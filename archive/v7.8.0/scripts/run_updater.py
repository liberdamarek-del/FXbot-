"""FXBOT - budget-paced continuous updater.

    python scripts/run_updater.py
    python scripts/run_updater.py --symbols EUR/USD,USD/JPY --timeframes 1min

Keeps the stored bars up to date in the background while respecting the
API budget: at most ONE API call per 120 seconds on the free plan
(720 credits per day), never more. Stop with Ctrl+C.

Tip for Android: run `termux-wake-lock` first, otherwise the phone may
pause Termux when the screen is off (data gaps are repaired on the next run).

For a one-off refresh use scripts/update_data.py instead.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_update import (  # noqa: E402
    DEFAULT_DERIVED_TIMEFRAMES,
    DEFAULT_SYMBOLS,
    DEFAULT_TIMEFRAMES,
)
from src.database import initialize_database  # noqa: E402
from src.twelve_data import TwelveDataFeed  # noqa: E402
from src.update_service import pace_seconds, run_service  # noqa: E402


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _option(argv: list[str], name: str) -> str | None:
    if name in argv:
        index = argv.index(name)

        if index + 1 >= len(argv):
            raise SystemExit(f"{name} needs a value")

        return argv[index + 1]

    return None


def main(argv: list[str], feed=None) -> int:
    symbols = _split(
        _option(argv, "--symbols")
        or os.getenv("COLLECTOR_SYMBOLS", DEFAULT_SYMBOLS)
    )
    timeframes = _split(
        _option(argv, "--timeframes")
        or os.getenv("COLLECTOR_TIMEFRAMES", DEFAULT_TIMEFRAMES)
    )
    instruments = [(s, t) for s in symbols for t in timeframes]
    derived = _split(
        os.getenv("DERIVED_TIMEFRAMES", DEFAULT_DERIVED_TIMEFRAMES)
    )

    if not instruments:
        raise SystemExit("at least one symbol and one timeframe are required")

    initialize_database()

    api_key = os.getenv("TWELVE_DATA_API_KEY", "demo")

    if api_key == "demo":
        print("POZOR: pouzivate sdileny klic 'demo'. Limity nejsou spolehlive.")
        print("       Zdarma vlastni klic: python scripts/set_api_key.py\n")

    if feed is None:
        feed = TwelveDataFeed(api_key=api_key, timeout=15)

    pace = pace_seconds(feed.budget)
    cycle_minutes = len(instruments) * pace / 60

    print("=" * 60)
    print("FXBOT - PRUBEZNA AKTUALIZACE (setrna k limitu API)")
    print("=" * 60)
    print(f"instrumentu: {len(instruments)} ({len(symbols)} paru x {len(timeframes)} timeframe)")
    print(f"max. rychlost: 1 volani / {pace:.0f} s")
    print(f"kazdy instrument se obnovi priblizne kazdych {cycle_minutes:.0f} min")
    if derived:
        print(f"odvozene casove ramce (zdarma): {', '.join(derived)}")
    print("zastaveni: Ctrl+C")
    print("=" * 60)

    summary = run_service(feed, instruments, derive_targets=derived)

    print(
        f"Konec: kol {summary['turns']}, volani {summary['calls']}, "
        f"ulozeno {summary['saved']}, chyb {summary['errors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
