"""Second research universe: HistData.com free 1-minute BID history for the
pairs FXCM does not publish (Scandinavian and emerging currencies with OECD
rates, plus CHF/JPY, EUR/CAD, GBP/AUD), aggregated to hourly bars in the
same format as scripts/fxcm_universe.py.

    python scripts/histdata_universe.py download   # yearly zips 2012-2025 + monthly 2026 (resumable)
    python scripts/histdata_universe.py build      # -> data/research/histdata_h1/<PAIR>.npz
    python scripts/histdata_universe.py status

HistData quotes are BID only. The site says "EST without daylight saving",
but the timestamps follow New York local time WITH daylight saving: measured
2026-10-01 on EUR/USD 2018 against FXCM (hourly closes differ by a median
0.1-0.2 pip only with America/New_York, by 4-7 pips with a fixed UTC-5).
The hourly arrays carry ASK = BID; the research labs apply the spread of the
pair (profit_lab2.SPREAD_PIPS) on both sides, so only the (constant) spread
assumption differs from the FXCM pairs. Raw zips are kept unchanged with
sha256 in manifest.tsv.
"""

import hashlib
import io
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.instruments import get_instrument  # noqa: E402

ROOT = PROJECT_ROOT / "data" / "research" / "histdata_h1"
RAW = ROOT / "raw"
PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{period}"
GET = "https://www.histdata.com/get.php"
PAIRS = ("USD/NOK", "EUR/NOK", "USD/SEK", "EUR/SEK", "USD/MXN", "USD/ZAR", "ZAR/JPY", "USD/PLN", "EUR/PLN",
         "USD/HUF", "EUR/HUF", "USD/CZK", "EUR/CZK", "CHF/JPY", "EUR/CAD", "GBP/AUD")
FIRST_YEAR = 2012
FIELDS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def code(pair: str) -> str:
    return pair.replace("/", "")


def periods() -> list[tuple[str, str]]:
    """(file label, URL period) - whole past years, single months of this year."""
    today = date.today()
    out = [(str(y), str(y)) for y in range(FIRST_YEAR, today.year)]
    out += [(f"{today.year}_{m:02d}", f"{today.year}/{m}") for m in range(1, today.month + 1)]
    return out


def _download(job) -> str:
    import requests

    pair, label, period = job
    target = RAW / code(pair) / f"{label}.zip"
    if target.exists():
        return "have"
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (fxbot research)"
    page_url = PAGE.format(pair=code(pair).lower(), period=period)
    for attempt in range(4):
        try:
            page = session.get(page_url, timeout=60).text
            fields = dict(re.findall(r'name="(tk|date|datemonth|platform|timeframe|fxpair)" id="\w+" value="([^"]*)"',
                                     page))
            if "tk" not in fields:
                return f"no form {pair} {label}"
            r = session.post(GET, data=fields, headers={"Referer": page_url}, timeout=300)
            if r.status_code == 200 and r.content[:2] == b"PK":
                tmp = target.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.replace(target)
                return "OK"
            if attempt == 3:
                return f"HTTP {r.status_code} {pair} {label}"
        except Exception as exc:                        # network: retry with backoff
            if attempt == 3:
                return f"FAILED {pair} {label}: {type(exc).__name__}"
        time.sleep(2 ** attempt * 2)
    return f"FAILED {pair} {label}"


def download() -> int:
    jobs = []
    for pair in PAIRS:
        (RAW / code(pair)).mkdir(parents=True, exist_ok=True)
        jobs += [(pair, label, period) for label, period in periods()]
    print(f"{len(jobs)} files", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for k, r in enumerate(pool.map(_download, jobs), 1):
            results.append(r)
            if r not in ("OK", "have"):
                print("  " + r, flush=True)
            if k % 50 == 0:
                print(f"  {k}/{len(jobs)}", flush=True)
    for r in sorted(set(x.split(" ")[0] for x in results)):
        print(f"{r}: {sum(1 for x in results if x.split(' ')[0] == r)}")
    return 0


def minutes(content: bytes, pair: str) -> np.ndarray:
    """(n, 5) array: UTC timestamp, O, H, L, C of valid minutes."""
    import pandas as pd

    with zipfile.ZipFile(io.BytesIO(content)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        frame = pd.read_csv(z.open(name), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"],
                            dtype={"t": str})
    local = pd.to_datetime(frame["t"], format="%Y%m%d %H%M%S")
    stamp = local.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    keep = stamp.notna().to_numpy()                   # the repeated / skipped hour at the DST switch is dropped
    frame, stamp = frame[keep], stamp[keep]
    ts = ((stamp - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy(dtype=np.int64)
    values = frame[["o", "h", "l", "c"]].to_numpy(dtype=np.float64)
    inst = get_instrument(pair)
    ok = ((values >= inst.min_price) & (values <= inst.max_price)).all(axis=1)
    ok &= (values[:, 1] >= values[:, [0, 3]].max(axis=1)) & (values[:, 2] <= values[:, [0, 3]].min(axis=1))
    return np.column_stack([ts[ok], values[ok]])


def hourly(m: np.ndarray) -> np.ndarray:
    """Hourly OHLC (bar open time UTC) from sorted minutes."""
    hour = (m[:, 0] // 3600 * 3600).astype(np.int64)
    starts = np.flatnonzero(np.r_[True, hour[1:] != hour[:-1]])
    ends = np.r_[starts[1:], len(hour)] - 1
    return np.column_stack([hour[starts], m[starts, 1], np.maximum.reduceat(m[:, 2], starts),
                            np.minimum.reduceat(m[:, 3], starts), m[ends, 4]])


def build() -> int:
    manifest = ["pair\tfile\tbytes\tsha256"]
    for pair in PAIRS:
        parts = []
        for path in sorted((RAW / code(pair)).glob("*.zip")):
            content = path.read_bytes()
            manifest.append(f"{pair}\t{path.name}\t{len(content)}\t{hashlib.sha256(content).hexdigest()}")
            parts.append(minutes(content, pair))
        if not parts:
            print(f"{pair}: no data")
            continue
        m = np.vstack(parts)
        m = m[np.argsort(m[:, 0], kind="stable")]
        m = m[np.r_[True, m[1:, 0] != m[:-1, 0]]]          # duplicates across files: keep the first
        h = hourly(m)
        cols = {"bo": h[:, 1], "bh": h[:, 2], "bl": h[:, 3], "bc": h[:, 4]}
        cols.update({"ao": h[:, 1], "ah": h[:, 2], "al": h[:, 3], "ac": h[:, 4]})
        np.savez_compressed(ROOT / f"{code(pair)}.npz", ts=h[:, 0].astype(np.int64), **cols)
        first, last = (time.strftime("%Y-%m-%d", time.gmtime(int(x))) for x in (h[0, 0], h[-1, 0]))
        print(f"{pair}: {len(m)} min -> {len(h)} h, {first} .. {last}", flush=True)
    (ROOT / "manifest.tsv").write_text("\n".join(manifest) + "\n")
    return 0


def status() -> int:
    for pair in PAIRS:
        files = sorted((RAW / code(pair)).glob("*.zip")) if (RAW / code(pair)).exists() else []
        print(f"{pair}: {len(files)} files {files[0].stem if files else ''} .. {files[-1].stem if files else ''}")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    raise SystemExit({"download": download, "build": build, "status": status}[command]())
