"""Research step R-046: difference of Yahoo (live) and FXCM (history) hourly closes, per pair.
Compared: the bar closes of all common hours and of the Friday bar before the 16:00 New York decision
(15:00 New York bar). Differences in % of price and in units of the pair's mean hourly range."""
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signals_live as S
import fxcm_universe as F

NY = ZoneInfo("America/New_York")


def main() -> None:
    print("par | spol. hodin | rozdil close median/p95 (% ceny) | v hodinovych rozsazich p95 | patky 15h NY: n, median, max (% ceny)")
    for pair, sym in S.YAHOO.items():
        y = S.yahoo_hourly(sym, "2y")
        f = F.load(pair)
        fc = (f["bc"] + f["ac"]) / 2
        fi = {int(t): k for k, t in enumerate(f["ts"])}
        ys, fs, rng, fri = [], [], [], []
        for k, t in enumerate(y["ts"]):
            j = fi.get(int(t))
            if j is None:
                continue
            d = abs(y["c"][k] - fc[j]) / fc[j] * 100
            ys.append(d)
            rng.append((f["bh"][j] - f["bl"][j]) / fc[j] * 100)
            dt = datetime.fromtimestamp(int(t), NY)
            if dt.weekday() == 4 and dt.hour == 15:
                fri.append(d)
        ys, rng = np.array(ys), np.array(rng)
        mr = rng.mean()
        print(f"{pair} | {len(ys)} | {np.median(ys):.4f} / {np.percentile(ys, 95):.4f} | "
              f"{np.percentile(ys, 95) / mr:.2f} | {len(fri)}, {np.median(fri) if fri else float('nan'):.4f}, "
              f"{max(fri) if fri else float('nan'):.4f} | stredni hodinovy rozsah {mr:.4f}")


if __name__ == "__main__":
    main()
