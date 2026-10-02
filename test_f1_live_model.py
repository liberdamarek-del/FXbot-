"""F1 - the live model scripts (no network, no production data).

The weekly decision time (no signal from an unfinished Friday), the stale
rate warning, the 12-month forward fill of the OECD rates, the price cache
rebuilt after a new download, the trade simulator (target, stop, same-bar
order, one position per pair) and the account simulation (compounding,
one position per pair, margin cap).
"""

import os
import pickle
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_f1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import numpy as np  # noqa: E402

import fxcm_universe as U  # noqa: E402
import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402
import profit_lab2 as P  # noqa: E402
import signals_live as SL  # noqa: E402

UTC = timezone.utc
H = 3600


def utc(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp())


# ---------------------------------------------------------------- decision time
friday = date(2026, 10, 2)
assert not SL.decision_ready(friday, utc("2026-10-02T03:00"))      # Thursday 23:00 New York: day just started
assert not SL.decision_ready(friday, utc("2026-10-02T18:00"))      # 14:00 New York: 3 hours before the close
assert SL.decision_ready(friday, utc("2026-10-02T19:00"))          # last bar 15:00-16:00 New York
assert SL.decision_ready(friday, utc("2026-10-02T20:00"))          # last bar 16:00-17:00 (the close)
assert SL.decision_ready(friday, utc("2026-10-04T21:00"))          # weekend run: Friday is complete
assert not SL.decision_ready(date(2026, 10, 1), utc("2026-10-01T20:00"))   # Thursday never decides
assert SL.decision_ready(date(2026, 1, 9), utc("2026-01-09T20:00"))        # winter time: 15:00 New York

# ---------------------------------------------------------------- rates
series = {(2026, m): 3.0 + m / 10 for m in range(1, 9)}
assert P.rate_at(series, 2026, 10, 2) == 3.8                        # August, two months back
assert P.rate_at(series, 2026, 10, 5) == 3.5                        # May
stale = {(2026, 1): 3.71}
assert P.rate_at(stale, 2026, 10, 2) == 3.71 and P.rate_at(stale, 2026, 10, 5) == 3.71   # carried forward: change 0
assert P.rate_at(stale, 2027, 3, 2) is None                         # more than 12 months: no value
warn = SL.stale_rates({"USD": series, "GBP": stale, "JPY": {(2026, 7): 1.4}}, friday)
assert warn == {"GBP": "2026-01"}, warn                             # one month late (JPY) is normal

# ---------------------------------------------------------------- price cache
tmp = Path(tempfile.mkdtemp(prefix="fxbot_f1_cache_"))
U.ROOT, U.HISTDATA, P.OUT = tmp / "h1", tmp / "hd", tmp / "out"
U.ROOT.mkdir()


def write_npz(days: int, price: float) -> None:
    ts = np.arange(utc("2026-09-07T21:00"), utc("2026-09-07T21:00") + days * 24 * H, H)
    fields = {k: np.full(len(ts), price + (0.0001 if k.startswith("a") else 0.0)) for k in U.FIELDS}
    np.savez(U.ROOT / "EURUSD.npz", ts=ts, **fields)


write_npz(3, 1.10)
first = P.series("EUR/USD")
assert len(first["days"]) == 3 and abs(first["dc"][-1] - 1.10005) < 1e-9
assert P.series("EUR/USD")["days"] == first["days"]                 # cached
time.sleep(0.05)
write_npz(4, 1.20)                                                   # the weekly download
os.utime(U.ROOT / "EURUSD.npz", (time.time() + 5, time.time() + 5))
second = P.series("EUR/USD")
assert len(second["days"]) == 4 and abs(second["dc"][-1] - 1.20005) < 1e-9, "cache must be rebuilt after new data"

# ---------------------------------------------------------------- trade simulator
N_DAYS = 330
SYMBOL = "EUR/USD"
half = (P.SPREAD_PIPS[SYMBOL] / 2 + P.SLIPPAGE_PIPS / 2) * 0.0001


def synthetic(path_after: dict[int, tuple[float, float]], signal_days: list[int]) -> tuple[dict, dict]:
    """Flat price 1.0, ATR 0.01; hour offsets after the entry bar get (high, low)."""
    n = N_DAYS * 24
    ts = np.arange(utc("2025-01-06T22:00"), utc("2025-01-06T22:00") + n * H, H)
    c = np.full(n, 1.0)
    h, l_ = c.copy(), c.copy()
    first = np.arange(N_DAYS) * 24
    last = first + 23
    for d in signal_days:
        for k, (hi, lo) in path_after.items():
            h[last[d] + k], l_[last[d] + k] = hi, lo
    days = [date(2025, 1, 7) + timedelta(days=k) for k in range(N_DAYS)]
    s = {"ts": ts, "o": c, "h": h, "l": l_, "c": c, "days": days, "first": first, "last": last,
         "dc": c[last], "close_ts": ts[last] + H}
    rsi2 = np.full(N_DAYS, 50.0)
    rsi2[signal_days] = 1.0
    I = {"atr": np.full(N_DAYS, 0.01), "rsi2": rsi2, "week_end": np.ones(N_DAYS, bool),
         "vix": np.full(N_DAYS, 15.0), "vix_rise": np.zeros(N_DAYS), "rates_mom": np.full(N_DAYS, 0.5),
         "carry": np.full(N_DAYS, 1.0), "carry_fin": np.full(N_DAYS, 0.0)}
    return s, I


def run(path_after, signal_days, **rule):
    D._cache[(SYMBOL, 2, 3, 0, "oecd")] = synthetic(path_after, signal_days)
    return D.simulate(D.Rule("t", fund="rates_up", rates_thr=0.25, **rule), [SYMBOL])


# target 0.75 ATR reached 5 hours after the entry
trades = run({5: (1.0 + 0.0075 + 2 * half + 1e-6, 1.0)}, [270])   # bid high above entry (ask) + TP
assert len(trades) == 1 and trades[0]["reason"] == "TP" and trades[0]["side"] == 1
assert abs(trades[0]["entry"] - (1.0 + half)) < 1e-12
assert trades[0]["margin_pct"] > 20                                   # 0.75 % of the price x 30 minus costs
# stop 3 ATR below the entry
trades = run({5: (1.0, 1.0 - 0.03)}, [270])
assert trades[0]["reason"] == "SL" and trades[0]["margin_pct"] < -80
# target and stop in the same hour: the stop counts (conservative)
trades = run({5: (1.02, 0.96)}, [270])
assert trades[0]["reason"] == "SL"
# one position per pair: a second signal while the first trade is open is skipped
trades = run({}, [270, 275])
assert len(trades) == 1 and trades[0]["reason"] == "CAS"
# no rate support -> no trade
D._cache[(SYMBOL, 2, 3, 0, "oecd")][1]["rates_mom"][:] = 0.1
assert D.simulate(D.Rule("t", fund="rates_up", rates_thr=0.25), [SYMBOL]) == []

# ---------------------------------------------------------------- account simulation


T = utc("2024-03-01T00:00")


def trade(pair, day, t_in, t_out, pct, side=1):
    """t_in / t_out in days after T."""
    return {"pair": pair, "side": side, "day": day, "t_in": T + t_in * 86400, "t_out": T + t_out * 86400, "margin_pct": pct}


d0 = date(2024, 3, 1)
lists = [[trade("EUR/USD", d0, 1, 10, 20.0), trade("EUR/USD", d0, 5, 15, 20.0),   # 2nd: pair busy
          trade("GBP/USD", d0, 20, 30, -50.0)]]
r = PS.run_portfolio(lists, 0.1, (2024, 2024))
assert len(r["trades"]) == 2
assert abs(r["equity"] - 1.02 * (1 - 0.1 * 0.5)) < 1e-12          # compounding: 2nd trade sized on 1.02
assert abs(r["max_dd"] - 0.05) < 1e-12
r = PS.run_portfolio([[trade("EUR/USD", d0, 1, 10, 10.0), trade("GBP/USD", d0, 2, 12, 10.0)]], 0.6, (2024, 2024))
assert len(r["trades"]) == 1                                         # margins above 100 % of the account: skipped

print("=" * 60)
print("F1 LIVE MODEL")
print("=" * 60)
print("FRIDAY DECISION ONLY AT THE CLOSE (NOT FROM A PARTIAL DAY): PASS")
print("RATES: 2-MONTH LAG, 12-MONTH FILL, STALE WARNING: PASS")
print("PRICE CACHE REBUILT AFTER NEW DATA: PASS")
print("SIMULATOR: TP, SL, SAME-HOUR ORDER, ONE PER PAIR, RATE FILTER: PASS")
print("ACCOUNT: COMPOUNDING, PAIR BUSY, MARGIN CAP, DRAWDOWN: PASS")
print("RESULT: PASS")
print("=" * 60)
