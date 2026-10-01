"""Research universe: FXCM hourly BID/ASK candles 2012-2026 for every cross
of the 8 major currencies the CDN publishes (25 of 28; no CHF/JPY, EUR/CAD,
GBP/AUD). One source for the whole period - no stitching.

    python scripts/fxcm_universe.py download     # raw week files (~20 000 requests, resumable)
    python scripts/fxcm_universe.py fill_m1      # weeks missing in H1: FXCM 1-minute files where published
    python scripts/fxcm_universe.py build        # -> data/research/fxcm_h1/<PAIR>.npz
    python scripts/fxcm_universe.py status

Raw files are kept unchanged (data/research/fxcm_h1/raw/<PAIR>/<year>_<week>.csv.gz,
sha256 in manifest.tsv). Each week file is decoded with the production
decoder (src/sources/fxcm.decode_week: plausibility range, crossed quotes
> 1 pip = invalid row). Invalid rows stay holes, nothing is filled. A week
file may hold a neighbouring week (FXCM numbering is inconsistent); every
bar is keyed by its own timestamp, duplicates must agree.
"""

import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.sources.fxcm import (BASE_URL, HOURLY_URL, decode_week, trading_monday, week_candidates,  # noqa: E402
                              week_endpoint)
from src.sources.http import FetchError, fetch  # noqa: E402

UTC = timezone.utc
ROOT = PROJECT_ROOT / "data" / "research" / "fxcm_h1"
RAW = ROOT / "raw"
RAW_M1 = ROOT / "raw_m1"
CURRENCIES = ("EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY")   # market quoting priority
UNAVAILABLE = {"CHF/JPY", "EUR/CAD", "GBP/AUD"}                          # 404 on the CDN (2008-2026 probed)
FIRST_YEAR, LAST_YEAR = 2012, 2026
FIELDS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def universe() -> list[str]:
    pairs = [f"{a}/{b}" for i, a in enumerate(CURRENCIES) for b in CURRENCIES[i + 1:]]
    return [p for p in pairs if p not in UNAVAILABLE]


def raw_path(symbol: str, year: int, week: int) -> Path:
    return RAW / symbol.replace("/", "") / f"{year}_{week:02d}.csv.gz"


def missing_path(symbol: str) -> Path:
    return RAW / symbol.replace("/", "") / "not_published.txt"


def _download_one(job) -> str:
    symbol, year, week = job
    target = raw_path(symbol, year, week)
    try:
        status, content, _ = fetch(f"{HOURLY_URL}/{week_endpoint(symbol, year, week)}", retries=4,
                                   ok_statuses=(200, 404))
    except FetchError as exc:
        return f"FAILED {symbol} {year}/{week}: {exc}"
    if status == 404 or not content:
        return f"404 {symbol} {year} {week}"
    tmp = target.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(target)
    return "OK"


def download() -> int:
    today = date.today()
    jobs = []
    for symbol in universe():
        folder = RAW / symbol.replace("/", "")
        folder.mkdir(parents=True, exist_ok=True)
        known_missing = set(missing_path(symbol).read_text().split("\n")) if missing_path(symbol).exists() else set()
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            for week in range(0, 54):
                if date(year, 1, 1) + timedelta(weeks=week - 1) > today:
                    continue
                recent = year == today.year and week >= today.isocalendar()[1] - 3     # may still appear
                if raw_path(symbol, year, week).exists() or (f"{year} {week}" in known_missing and not recent):
                    continue
                jobs.append((symbol, year, week))
    print(f"{len(jobs)} files to request", flush=True)
    started, done, failed = time.monotonic(), 0, []
    new_missing: dict[str, set] = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for result in pool.map(_download_one, jobs):
            done += 1
            if result.startswith("404"):
                _, symbol, year, week = result.split(" ")
                new_missing.setdefault(symbol, set()).add(f"{year} {week}")
            elif result != "OK":
                failed.append(result)
            if done % 500 == 0:
                print(f"  {done}/{len(jobs)} ({time.monotonic() - started:.0f} s, failed {len(failed)})", flush=True)
    for symbol, weeks in new_missing.items():
        path = missing_path(symbol)
        old = set(path.read_text().split("\n")) if path.exists() else set()
        path.write_text("\n".join(sorted((old | weeks) - {""})))
    for line in failed[:20]:
        print(line)
    print(f"done {done}, failed {len(failed)}, {time.monotonic() - started:.0f} s")
    return 1 if failed else 0


def build() -> int:
    manifest = []
    for symbol in universe():
        folder = RAW / symbol.replace("/", "")
        bars: dict[int, tuple] = {}
        conflicts = invalid_rows = 0
        for path in sorted(folder.glob("*.csv.gz")):
            content = path.read_bytes()
            manifest.append(f"{symbol}\t{path.name}\t{len(content)}\t{hashlib.sha256(content).hexdigest()}")
            observed, invalid = decode_week(content, symbol, step=3600)
            invalid_rows += len(invalid)
            for b in observed:
                row = (b.bo, b.bh, b.bl, b.bc, b.ao, b.ah, b.al, b.ac)
                if b.ts in bars and bars[b.ts] != row:
                    conflicts += 1
                    continue
                bars[b.ts] = row
        from_m1 = 0
        for path in sorted((RAW_M1 / symbol.replace("/", "")).glob("*.csv.gz")):
            content = path.read_bytes()
            manifest.append(f"{symbol}\tm1/{path.name}\t{len(content)}\t{hashlib.sha256(content).hexdigest()}")
            minutes, _ = decode_week(content, symbol, step=60)
            for hour, row in hours_from_minutes(minutes).items():
                if hour not in bars:
                    bars[hour] = row
                    from_m1 += 1
        ts = np.array(sorted(bars), dtype=np.int64)
        values = np.array([bars[t] for t in ts], dtype=np.float64)
        np.savez_compressed(ROOT / f"{symbol.replace('/', '')}.npz", ts=ts,
                            **{f: values[:, i] for i, f in enumerate(FIELDS)})
        gaps = _missing_weeks(ts)
        first, last = (datetime.fromtimestamp(int(x), tz=UTC).date() for x in (ts[0], ts[-1]))
        print(f"{symbol}: {len(ts)} h  {first} .. {last}  invalid rows {invalid_rows}  conflicts {conflicts}  "
              f"from m1 {from_m1} h  weeks without data {len(gaps)}{' ' + ', '.join(map(str, gaps[:6])) if gaps else ''}", flush=True)
    (ROOT / "manifest.tsv").write_text("pair\tfile\tbytes\tsha256\n" + "\n".join(manifest) + "\n")
    return 0


def hours_from_minutes(minutes) -> dict[int, tuple]:
    """Hourly BID/ASK candles from valid 1-minute candles (open of the first,
    close of the last, extremes of all minutes in the hour)."""
    out: dict[int, list] = {}
    for b in minutes:
        hour = b.ts - b.ts % 3600
        row = out.get(hour)
        if row is None:
            out[hour] = [b.bo, b.bh, b.bl, b.bc, b.ao, b.ah, b.al, b.ac]
        else:
            row[1], row[2], row[3] = max(row[1], b.bh), min(row[2], b.bl), b.bc
            row[5], row[6], row[7] = max(row[5], b.ah), min(row[6], b.al), b.ac
    return {k: tuple(v) for k, v in out.items()}


def fill_m1() -> int:
    """Download the 1-minute files of the trading weeks without hourly data."""
    jobs = []
    for symbol in universe():
        path = ROOT / f"{symbol.replace('/', '')}.npz"
        if not path.exists():
            continue
        folder = RAW_M1 / symbol.replace("/", "")
        folder.mkdir(parents=True, exist_ok=True)
        for monday in _missing_weeks(np.load(path)["ts"]):
            for year, week in week_candidates(monday):
                if not (folder / f"{year}_{week:02d}.csv.gz").exists():
                    jobs.append((symbol, year, week, monday))
    print(f"{len(jobs)} minute files to try", flush=True)

    def one(job):
        symbol, year, week, monday = job
        try:
            status, content, _ = fetch(f"{BASE_URL}/{week_endpoint(symbol, year, week)}", retries=4,
                                       ok_statuses=(200, 404))
        except FetchError as exc:
            return f"FAILED {symbol} {year}/{week}: {exc}"
        if status != 200 or not content:
            return "404"
        try:
            minutes, _ = decode_week(content, symbol, step=60)
        except (ValueError, OSError, EOFError) as exc:
            return f"FAILED {symbol} {year}/{week}: {type(exc).__name__}"
        start = int(datetime(monday.year, monday.month, monday.day, tzinfo=UTC).timestamp()) - 86400 - 2 * 3600
        if not any(start <= b.ts < start + 6 * 86400 for b in minutes):
            return "other week"
        (RAW_M1 / symbol.replace("/", "") / f"{year}_{week:02d}.csv.gz").write_bytes(content)
        return "OK"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, jobs))
    for r in sorted(set(results)):
        print(f"  {r}: {results.count(r)}")
    return 0


def _missing_weeks(ts: np.ndarray) -> list[date]:
    have = {trading_monday(datetime.fromtimestamp(int(t) + 6 * 3600, tz=UTC).date()) for t in ts}
    first = min(d for d in have if d)
    last = max(d for d in have if d)
    out, monday = [], first
    while monday <= last:
        if monday not in have and not (monday.month == 1 and monday.day <= 2) and not (monday.month == 12
                                                                                       and monday.day >= 25):
            out.append(monday)
        monday += timedelta(days=7)
    return out


def load(symbol: str) -> dict:
    """Hourly arrays of one pair: ts (bar open, UTC) and BID/ASK OHLC."""
    data = np.load(ROOT / f"{symbol.replace('/', '')}.npz")
    return {k: data[k] for k in ("ts",) + FIELDS}


def status() -> int:
    for symbol in universe():
        folder = RAW / symbol.replace("/", "")
        files = len(list(folder.glob("*.csv.gz"))) if folder.exists() else 0
        miss = len(missing_path(symbol).read_text().split("\n")) if missing_path(symbol).exists() else 0
        print(f"{symbol}: {files} files, {miss} not published")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    raise SystemExit({"download": download, "fill_m1": fill_m1, "build": build, "status": status}[command]())
