"""FXCM public 1-minute BID/ASK candles (weekly files) for the minute study (user's question 2026-10-05).

    python scripts/fxcm_m1.py download 2016 2026 [PAIR ...]   # -> data/research/fxcm_m1/<PAIR>/<YEAR>_<WEEK>.csv.gz
    python scripts/fxcm_m1.py load EUR/USD 2024                # quick check

Source: https://candledata.fxcorporate.com/m1/<SYMBOL>/<YEAR>/<WEEK>.csv.gz (public, keyless; FXCM's own
quotes, not the user's broker). Missing weeks stay missing (never filled). Two polite parallel workers.
"""

import gzip
import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.instruments import DEFAULT_ACTIVE  # noqa: E402
from src.sources.http import FetchError, fetch  # noqa: E402

ROOT = PROJECT_ROOT / "data" / "research" / "fxcm_m1"
URL = "https://candledata.fxcorporate.com/m1/{sym}/{year}/{week}.csv.gz"


def _get(pair: str, year: int, week: int) -> str:
    path = ROOT / pair.replace("/", "") / f"{year}_{week:02d}.csv.gz"
    if path.exists() and path.stat().st_size > 0:
        return "cached"
    try:
        _, content, _ = fetch(URL.format(sym=pair.replace("/", ""), year=year, week=week), retries=3)
    except FetchError as exc:
        return f"missing {exc}"[:60]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    time.sleep(0.2)
    return "ok"


def download(first: int, last: int, pairs: list[str]) -> None:
    jobs = [(p, y, w) for p in pairs for y in range(first, last + 1) for w in range(1, 54)]
    done = 0
    with ThreadPoolExecutor(2) as ex:
        for res in ex.map(lambda j: (j, _get(*j)), jobs):
            done += 1
            if done % 200 == 0 or not res[1] in ("ok", "cached"):
                print(done, len(jobs), res, flush=True)


def load(pair: str, years: range) -> dict:
    """1-minute bars of one pair, sorted, duplicates dropped: ts (UTC seconds, bar open), bid/ask OHLC."""
    frames = []
    for y in years:
        for f in sorted((ROOT / pair.replace("/", "")).glob(f"{y}_*.csv.gz")):
            try:
                frames.append(pd.read_csv(io.BytesIO(gzip.decompress(f.read_bytes()))))
            except (OSError, EOFError, pd.errors.ParserError):
                print(f"poskozeny soubor {f.name} - vynechan", file=sys.stderr)
    df = pd.concat(frames, ignore_index=True)
    dt = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M:%S.%f", utc=True)
    ts = (dt - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)       # independent of the datetime resolution
    df = df.assign(ts=ts).drop_duplicates("ts").sort_values("ts")
    cols = {"bo": "BidOpen", "bh": "BidHigh", "bl": "BidLow", "bc": "BidClose",
            "ao": "AskOpen", "ah": "AskHigh", "al": "AskLow", "ac": "AskClose"}
    out = {k: df[v].to_numpy(np.float64) for k, v in cols.items()}
    out["ts"] = df["ts"].to_numpy(np.int64)
    ok = (out["ac"] >= out["bc"]) & (out["bh"] >= out["bl"])          # broken rows are holes, never repaired
    return {k: v[ok] for k, v in out.items()}


if __name__ == "__main__":
    if sys.argv[1] == "download":
        pairs = [p for p in sys.argv[4:]] or list(DEFAULT_ACTIVE)
        download(int(sys.argv[2]), int(sys.argv[3]), pairs)
    elif sys.argv[1] == "load":
        d = load(sys.argv[2], range(int(sys.argv[3]), int(sys.argv[3]) + 1))
        print(len(d["ts"]), d["ts"][0], d["ts"][-1])
