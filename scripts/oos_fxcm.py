"""Out-of-sample test of the model on history it has never seen (module 77).

    python scripts/oos_fxcm.py download    # FXCM hourly + 1-minute files 2016-06 .. 2023-07 (~20 min, ~0.6 GB)
    python scripts/oos_fxcm.py evaluate    # full evaluation -> docs/OOS_REPORT.md
    python scripts/oos_fxcm.py reprocess   # rebuild days/bars from the stored files (after a parser change)
    python scripts/oos_fxcm.py status

Why: every parameter and every rule change so far (CH-001..CH-003) was
looked at only on 2023-08 .. 2026-09 (Dukascopy). The years before that are
the honest test: the rules of the Word model with the champion parameters,
run unchanged on 2016-10 .. 2023-07 (fundamentals point-in-time from the
same keyless sources; JPY policy rate and S&P 500 start 2016-09).

Prices: FXCM public BID/ASK files (src/sources/fxcm.py) - hourly candles
are the canonical series of THIS archive, its 1-minute candles decide
ambiguous hours. A separate archive (data/oos_fxcm/) is used; the
production archive and the prediction ledger are never touched. The
fundamentals database is shared read-only through a link.
"""

import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OOS_DIR = PROJECT_ROOT / "data" / "oos_fxcm"
FIRST = date(2016, 6, 1)           # 4 months of warm-up before the first decision
LAST = date(2023, 7, 31)           # the in-sample period starts 2023-08

os.environ["DATA_DIR"] = str(OOS_DIR.relative_to(PROJECT_ROOT))
os.environ["FXBOT_CANONICAL_SOURCE"] = "fxcm"
sys.path.insert(0, str(PROJECT_ROOT))
OOS_DIR.mkdir(parents=True, exist_ok=True)
_link = OOS_DIR / "fundamentals.sqlite3"

if not _link.exists():
    _link.symlink_to(PROJECT_ROOT / "data" / "fundamentals.sqlite3")

from src.instruments import parse_symbols  # noqa: E402
from src.path_archive import (  # noqa: E402
    archive_summary,
    get_path_connection,
    initialize_path_archive,
    load_payload,
    store_hourly_series,
)
from src.sources.fxcm import SOURCE_FXCM_H1, decode_week, fill_week, hour_weeks, ingest_day, reprocess  # noqa: E402


def download(symbols: list[str]) -> None:
    initialize_path_archive()

    for symbol in symbols:
        started = time.monotonic()
        hours, missing = hour_weeks(symbol, FIRST, LAST)
        counts = store_hourly_series(symbol, hours, SOURCE_FXCM_H1)
        print(f"{symbol}: hodiny {counts} | chybejici tydny {len(missing)} "
              f"{[d.isoformat() for d in missing[:6]]} | {time.monotonic() - started:.0f} s", flush=True)

    tried: set = set()
    days = [FIRST + timedelta(days=k) for k in range((LAST - FIRST).days + 1)]

    for symbol in symbols:
        started = time.monotonic()
        states: dict[str, int] = {}

        for day in days:
            state = ingest_day(symbol, day, tried)
            states[state] = states.get(state, 0) + 1

        print(f"{symbol}: 1min dny {states} | {time.monotonic() - started:.0f} s", flush=True)


def reprocess_all(symbols: list[str]) -> None:
    for symbol in symbols:
        with get_path_connection() as connection:
            ids = [r[0] for r in connection.execute(
                "SELECT payload_id FROM raw_payloads WHERE source_id = ? AND instrument = ? ORDER BY period_start",
                (SOURCE_FXCM_H1, symbol))]

        hours = {}

        for payload_id in ids:
            content, _ = load_payload(payload_id)

            for bar in fill_week(*decode_week(content, symbol, step=3600), step=3600):
                hours[bar.ts] = bar

        counts = store_hourly_series(symbol, [hours[k] for k in sorted(hours)], SOURCE_FXCM_H1)
        print(f"{symbol}: nove hodinove svicky {counts} | minutove tydny {reprocess(symbol)}", flush=True)


def status(symbols: list[str]) -> None:
    for symbol in symbols:
        summary = archive_summary(symbol)
        bars = {k: v["n"] for k, v in summary["bars"].items()}
        print(f"{symbol}: {bars} | 1min dny {({k: v['n'] for k, v in summary['days_fxcm'].items()})}")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("download", "evaluate", "status", "reprocess"):
        print(__doc__)
        return 1

    symbols = parse_symbols(None)

    if argv[0] == "download":
        download(symbols)
        status(symbols)
        return 0

    if argv[0] == "reprocess":
        reprocess_all(symbols)
        status(symbols)
        return 0

    if argv[0] == "status":
        status(symbols)
        return 0

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import evaluate  # noqa: E402  (after DATA_DIR / canonical source are set)

    return evaluate.main(["--out", str(PROJECT_ROOT / "docs" / "OOS_REPORT.md"),
                          "--label", f"OUT-OF-SAMPLE {FIRST:%Y-%m} .. {LAST:%Y-%m} (FXCM, model tato data nevidel)"]
                         + argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
