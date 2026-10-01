"""Download BID/ASK price history into the Market Path Archive.

    python scripts/download_history.py                    # 1-minute: last 30 days, 12 pairs
    python scripts/download_history.py --days 120         # 1-minute: last 120 days
    python scripts/download_history.py --hourly-years 10  # + hourly candles, 10 years back
    python scripts/download_history.py --from 2025-01-01 --to 2025-06-30
    python scripts/download_history.py --symbols EUR/USD,USD/JPY --days 90
    python scripts/download_history.py --today            # + finished hours of today
    python scripts/download_history.py --status           # only show what is stored
    python scripts/download_history.py --source fxcm --days-file data/ambiguous_days_model.txt
                                                          # 1-minute days from FXCM (second source)

Source: Dukascopy public history (keyless, see src/sources/dukascopy.py).
Two layers:
- hourly candles, one file per month and side: cheap long history for the
  daily / 4h / 1h analysis and for backtests over many years,
- 1-minute candles, one file per day and side: recent path, entry timing
  and precise outcome resolution (which of SL / TP came first).

--source fxcm takes the 1-minute days from the FXCM public week files
instead (src/sources/fxcm.py): used for outcome checks only, never for the
canonical bars, and only for days Dukascopy does not have.

Every file is stored with its SHA-256; days/months are marked COMPLETE /
PARTIAL / GAP / EMPTY, nothing is ever filled in. Re-running is safe:
COMPLETE periods are skipped, GAP periods are tried again.

The server throttles clients that open connections too quickly. The
download therefore runs sequentially, pauses between files and waits
several minutes when the server stops answering; it simply continues
where it stopped when started again.

Size (approx.): 1 pair x 1 year of 1-minute data = ~520 files, ~11 MB;
1 pair x 10 years of hourly data = 240 files, ~3 MB. On a phone start with
--days 90 --hourly-years 5.
"""

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_DIR  # noqa: E402  (loads .env first)
from src.instruments import parse_symbols  # noqa: E402
from src.path_archive import (  # noqa: E402
    archive_summary,
    get_day,
    initialize_path_archive,
    next_month,
    rebuild_aggregates,
    rebuild_all,
    rebuild_hourly_aggregates,
)
from src.sources.dukascopy import (  # noqa: E402
    SOURCE_H1,
    SOURCE_M1,
    SourceUnavailable,
    ingest_day,
    ingest_month,
    ingest_provisional_hours,
)
from src.sources.fxcm import ingest_day as fxcm_ingest_day  # noqa: E402

UTC = timezone.utc
REBUILD_CHUNK_DAYS = 30
THROTTLE_PAUSE = int(os.getenv("DOWNLOAD_THROTTLE_PAUSE", "60"))           # seconds to wait when the server stops answering
MAX_PAUSE = int(os.getenv("DOWNLOAD_MAX_PAUSE", "1800"))                    # the pause doubles up to this while it keeps refusing
MAX_THROTTLE_PAUSES = int(os.getenv("DOWNLOAD_MAX_THROTTLE_PAUSES", "30"))  # then give up for this run (re-run later)


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
        line = f"{symbol}: 1min dny {complete.get('n', 0)}"

        if complete:
            line += f" ({complete['first']}..{complete['last']})"

        for state in ("PARTIAL", "GAP"):
            if state in days:
                line += f" {state} {days[state]['n']}"

        fxcm = summary.get("days_fxcm", {})

        if fxcm:
            line += " | FXCM dny " + " ".join(f"{k} {v['n']}" for k, v in sorted(fxcm.items()))

        months = summary.get("months", {}).get("COMPLETE")

        if months:
            line += f" | 1h mesice {months['n']} ({months['first']}..{months['last']})"

        print(line)

    print("=" * 70)


def run_jobs(jobs: list, label: str, on_complete=None) -> dict:
    """Run (symbol, period, callable) jobs sequentially with throttle handling."""
    totals: dict[str, int] = {}
    started = time.monotonic()
    pauses = 0
    pause = THROTTLE_PAUSE
    index = 0

    while index < len(jobs):
        symbol, period, call = jobs[index]

        try:
            state = call()
        except SourceUnavailable as exc:
            pauses += 1

            if pauses > MAX_THROTTLE_PAUSES:
                print(f"  server neodpovida opakovane - konec, spustte znovu pozdeji ({exc})")
                totals["UNAVAILABLE"] = totals.get("UNAVAILABLE", 0) + len(jobs) - index
                break

            limit = "limit pozadavku" if "429" in str(exc) else "neodpovida"
            print(f"  server {limit} ({symbol} {period}) - pauza {pause} s "
                  f"[{datetime.now(UTC):%H:%M}]", flush=True)
            time.sleep(pause)
            pause = min(2 * pause, MAX_PAUSE)
            continue            # same job again

        pause = THROTTLE_PAUSE
        totals[state] = totals.get(state, 0) + 1
        index += 1

        if state in ("COMPLETE", "PARTIAL") and on_complete is not None:
            on_complete(symbol, period)

        if state not in ("COMPLETE", "EMPTY", "PENDING"):
            print(f"  {symbol} {period}: {state}")

        if index % 50 == 0 or index == len(jobs):
            rate = index / max(1e-9, time.monotonic() - started)
            remaining = (len(jobs) - index) / rate if rate else 0
            print(
                f"  {label}: {index}/{len(jobs)} | {rate:.2f}/s | "
                f"zbyva ~{remaining / 60:.0f} min | {totals}",
                flush=True,
            )

    return totals


def hourly(symbols: list[str], years: int, now: datetime) -> dict:
    last = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    first = (last[0] - years, last[1])
    months = []
    current = first

    while current <= last:
        months.append(current)
        current = next_month(*current)

    months.reverse()        # newest first
    jobs = [
        (symbol, f"{y}-{m:02d}", (lambda s=symbol, y=y, m=m: ingest_month(s, y, m, now)))
        for (y, m) in months
        for symbol in symbols
    ]
    def rebuild_month(symbol: str, period: str) -> None:
        y, m = (int(x) for x in period.split("-"))
        rebuild_hourly_aggregates(symbol, (y, m), next_month(y, m), SOURCE_H1)

    totals = run_jobs(jobs, "1h mesice", rebuild_month)

    for symbol in symbols:
        # yearly chunks keep memory small
        start = first

        while start <= last:
            end = min(last, (start[0], 12))
            rebuild_hourly_aggregates(symbol, start, end, SOURCE_H1)
            start = (start[0] + 1, 1)

    return totals


def minutes(symbols: list[str], first: date, last: date, now: datetime) -> dict:
    days = []
    day = last

    while day >= first:
        days.append(day)
        day -= timedelta(days=1)

    jobs = [
        (symbol, day.isoformat(), (lambda s=symbol, d=day: ingest_day(s, d, now)))
        for day in days
        for symbol in symbols
    ]
    def rebuild_day(symbol: str, period: str) -> None:
        day = date.fromisoformat(period)
        rebuild_aggregates(symbol, day - timedelta(days=1), day + timedelta(days=1), SOURCE_M1)

    totals = run_jobs(jobs, "1min dny", rebuild_day)

    for symbol in symbols:
        chunk_start = first

        while chunk_start <= last:
            chunk_end = min(last, chunk_start + timedelta(days=REBUILD_CHUNK_DAYS - 1))
            rebuild_aggregates(symbol, chunk_start, chunk_end, SOURCE_M1)
            chunk_start = chunk_end + timedelta(days=1)

    return totals


def days_wanted(args, symbols: list[str], now: datetime) -> list[tuple[str, date]]:
    if args.days_file:
        wanted = []

        for line in Path(args.days_file).read_text(encoding="utf-8").splitlines():
            if "," in line:
                symbol, day = line.strip().split(",")
                wanted.append((symbol, date.fromisoformat(day)))

        return wanted

    last = args.last or (now.date() - timedelta(days=1))
    first = args.first or (last - timedelta(days=max(1, args.days) - 1))
    days = [first + timedelta(days=k) for k in range((last - first).days + 1)]
    return [(s, d) for d in reversed(days) for s in symbols]


def fxcm_day(symbol: str, day: date, tried: set) -> str:
    duka = get_day(symbol, day, SOURCE_M1)

    if duka and duka["state"] == "COMPLETE":
        return "COMPLETE"           # the canonical day exists: nothing to do

    return fxcm_ingest_day(symbol, day, tried)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Download BID/ASK history (Dukascopy).")
    parser.add_argument("--symbols", default=None, help="comma separated, default = 12 active pairs")
    parser.add_argument("--days", type=int, default=30, help="1-minute history in days (0 = none)")
    parser.add_argument("--from", dest="first", type=_date, default=None)
    parser.add_argument("--to", dest="last", type=_date, default=None)
    parser.add_argument("--hourly-years", type=int, default=0, help="hourly history in years")
    parser.add_argument("--today", action="store_true", help="also fetch finished hours of today (provisional)")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--rebuild", action="store_true", help="only rebuild stored bars from the archive")
    parser.add_argument("--source", choices=("dukascopy", "fxcm"), default="dukascopy",
                        help="1-minute days from Dukascopy (canonical) or FXCM (second source, path checks only)")
    parser.add_argument("--days-file", default=None,
                        help="file with lines 'SYMBOL,YYYY-MM-DD': fetch exactly these 1-minute days "
                             "(e.g. days whose hourly bars were ambiguous in a backtest)")
    args = parser.parse_args(argv)

    symbols = parse_symbols(args.symbols)
    initialize_path_archive()

    if args.status:
        print_status(symbols)
        return 0

    if args.rebuild:
        for symbol in symbols:
            print(f"{symbol}: prestavba {rebuild_all(symbol)}")
        print_status(symbols)
        return 0

    now = datetime.now(UTC)

    print("=" * 70)
    print(f"FXBOT - STAHOVANI HISTORIE BID/ASK ({'FXCM' if args.source == 'fxcm' else 'Dukascopy'})")
    print("=" * 70)
    print(f"pary: {', '.join(symbols)}")
    print(f"archiv: {DATA_DIR / 'market_path.sqlite3'}")
    problems = {}

    if args.source == "fxcm":
        wanted = days_wanted(args, symbols, now)
        print(f"FXCM 1min dny: {len(wanted)} (jen kde Dukascopy den chybi)")
        tried: set = set()
        jobs = [(s, d.isoformat(), (lambda s=s, d=d: fxcm_day(s, d, tried))) for s, d in wanted]
        totals = run_jobs(jobs, "FXCM 1min dny")
        problems.update({k: v for k, v in totals.items() if k not in ("COMPLETE", "EMPTY", "PENDING", "PARTIAL")})
        print_status(symbols)
        print("VYSLEDEK:", "OK" if not problems else f"nedostupne {problems} (FXCM tyden nezverejnen)")
        return 0

    if args.days_file:
        wanted = []

        for line in Path(args.days_file).read_text(encoding="utf-8").splitlines():
            if "," in line:
                symbol, day = line.strip().split(",")
                wanted.append((symbol, date.fromisoformat(day)))

        print(f"cilene dny: {len(wanted)}")

        def rebuild_day(symbol: str, period: str) -> None:
            day = date.fromisoformat(period)
            rebuild_aggregates(symbol, day - timedelta(days=1), day + timedelta(days=1), SOURCE_M1)

        jobs = [(s, d.isoformat(), (lambda s=s, d=d: ingest_day(s, d, now))) for s, d in wanted]
        totals = run_jobs(jobs, "cilene 1min dny", rebuild_day)
        problems.update({k: v for k, v in totals.items() if k not in ("COMPLETE", "EMPTY", "PENDING")})
        args.days = 0

    if args.hourly_years > 0:
        print(f"hodinove svicky: {args.hourly_years} let zpet")
        totals = hourly(symbols, args.hourly_years, now)
        problems.update({k: v for k, v in totals.items() if k not in ("COMPLETE", "EMPTY", "PENDING")})

    if args.days > 0 or args.first:
        last = args.last or (now.date() - timedelta(days=1))
        first = args.first or (last - timedelta(days=args.days - 1))
        print(f"minutove svicky: {first} .. {last}")
        totals = minutes(symbols, first, last, now)
        problems.update({k: v for k, v in totals.items() if k not in ("COMPLETE", "EMPTY", "PENDING")})

    if args.today:
        for symbol in symbols:
            try:
                count = ingest_provisional_hours(symbol, now.date(), now)
            except SourceUnavailable:
                count = 0
            print(f"  {symbol} dnes: {count} novych hodin (PROVISIONAL)")

    print_status(symbols)
    print("VYSLEDEK:", "OK" if not problems else f"problemy {problems} - spustte znovu pozdeji")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
