"""Download historical 1-minute BID/ASK history into the Market Path Archive.

    python scripts/download_history.py                   # last 30 days, 12 pairs
    python scripts/download_history.py --days 365        # one year
    python scripts/download_history.py --from 2025-01-01 --to 2025-06-30
    python scripts/download_history.py --symbols EUR/USD,USD/JPY --days 90
    python scripts/download_history.py --today           # + finished hours of today
    python scripts/download_history.py --status          # only show what is stored

Source: Dukascopy public history (keyless, see src/sources/dukascopy.py).
Every file is stored with its SHA-256; days are marked COMPLETE / PARTIAL /
GAP / EMPTY, nothing is ever filled in. Re-running is safe: COMPLETE days
are skipped, GAP days are tried again.

Size (approx.): 1 pair x 1 year = 520 files, ~6 MB payload + ~5 MB bars.
On a phone start with --days 90.
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_DIR  # noqa: E402  (loads .env first)
from src.instruments import parse_symbols  # noqa: E402
from src.path_archive import (  # noqa: E402
    archive_summary,
    initialize_path_archive,
    list_days,
    rebuild_aggregates,
)
from src.sources.dukascopy import (  # noqa: E402
    SOURCE_M1,
    SourceUnavailable,
    ingest_day,
    ingest_provisional_hours,
)

UTC = timezone.utc
REBUILD_CHUNK_DAYS = 30


def _date(text: str) -> date:
    return date.fromisoformat(text)


def print_status(symbols: list[str]) -> None:
    print("=" * 70)
    print("MARKET PATH ARCHIVE - STAV")
    print("=" * 70)

    for symbol in symbols:
        summary = archive_summary(symbol)
        days = summary["days"]
        complete = days.get("COMPLETE", {})
        line = f"{symbol}: dny COMPLETE {complete.get('n', 0)}"

        if complete:
            line += f" ({complete['first']} .. {complete['last']})"

        for state in ("PARTIAL", "GAP"):
            if state in days:
                line += f" | {state} {days[state]['n']}"

        bars = summary["bars"].get("1h")

        if bars:
            line += f" | svicky 1h {bars['n']}"

        print(line)

    print("=" * 70)


def ingest_range(symbols: list[str], first: date, last: date, workers: int) -> dict:
    days = []
    day = last

    while day >= first:
        days.append(day)
        day -= timedelta(days=1)

    totals: dict[str, int] = {}
    started = time.monotonic()
    done = 0
    touched: dict[str, list[date]] = {s: [] for s in symbols}

    def one(job):
        symbol, day = job

        try:
            return symbol, day, ingest_day(symbol, day)
        except SourceUnavailable as exc:
            return symbol, day, f"UNAVAILABLE ({str(exc)[-60:]})"

    jobs = [(symbol, day) for day in days for symbol in symbols]

    # one worker is fastest: parallel connections through the network
    # proxy stalled for seconds each (measured 2026-09-30)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        for symbol, day, state in pool.map(one, jobs):
            key = state.split(" ")[0]
            totals[key] = totals.get(key, 0) + 1
            touched[symbol].append(day)
            done += 1

            if key not in ("COMPLETE", "EMPTY", "PENDING"):
                print(f"  {symbol} {day}: {state}")

            if done % 100 == 0 or done == len(jobs):
                rate = done / max(1e-9, time.monotonic() - started)
                remaining = (len(jobs) - done) / rate if rate else 0
                print(
                    f"  {done}/{len(jobs)} dnu x paru | {rate:.1f}/s | "
                    f"zbyva ~{remaining / 60:.0f} min | {totals}",
                    flush=True,
                )

    # stored aggregates (15min .. 1d), in chunks to keep memory small
    for symbol in symbols:
        if not touched[symbol]:
            continue

        chunk_start = min(touched[symbol])
        end = max(touched[symbol])

        while chunk_start <= end:
            chunk_end = min(end, chunk_start + timedelta(days=REBUILD_CHUNK_DAYS - 1))
            rebuild_aggregates(symbol, chunk_start, chunk_end, SOURCE_M1)
            chunk_start = chunk_end + timedelta(days=1)

    return totals


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Download BID/ASK 1-minute history (Dukascopy).")
    parser.add_argument("--symbols", default=None, help="comma separated, default = 12 active pairs")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--from", dest="first", type=_date, default=None)
    parser.add_argument("--to", dest="last", type=_date, default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--today", action="store_true", help="also fetch finished hours of today (provisional)")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    symbols = parse_symbols(args.symbols)
    initialize_path_archive()

    if args.status:
        print_status(symbols)
        return 0

    now = datetime.now(UTC)
    last = args.last or (now.date() - timedelta(days=1))
    first = args.first or (last - timedelta(days=args.days - 1))

    print("=" * 70)
    print("FXBOT - STAHOVANI HISTORIE BID/ASK (Dukascopy)")
    print("=" * 70)
    print(f"pary: {', '.join(symbols)}")
    print(f"obdobi: {first} .. {last} | archiv: {DATA_DIR / 'market_path.sqlite3'}")

    totals = ingest_range(symbols, first, last, args.workers)

    if args.today:
        for symbol in symbols:
            count = ingest_provisional_hours(symbol, now.date(), now)
            print(f"  {symbol} dnes: {count} novych hodin (PROVISIONAL)")

    print_status(symbols)
    problems = {k: v for k, v in totals.items() if k not in ("COMPLETE", "EMPTY", "PENDING")}
    print("VYSLEDEK:", "OK" if not problems else f"problemy {problems} - spustte znovu pozdeji")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
