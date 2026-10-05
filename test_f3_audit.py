"""F3 - regressions of the code audit 2026-10-04 (docs/AUDIT_2026-10-04.md); no network, synthetic data.

Leverage per pair (ESMA: 1:30 for two majors, 1:20 otherwise) in the simulator and the forward test; the
weekly values known at each day (no look-ahead on Monday-Thursday); RSI of a flat market; Bollinger bands
that do not depend on where the series starts; the live-timing mode of the simulator (decision 1 h before
the Friday close with the earlier days' full closes, exactly what the live run at 16:05 New York sees);
the forward test with costs, the stop before the target in the same hour and the time exit.
"""

import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_f3_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import numpy as np  # noqa: E402

import indikatory as K  # noqa: E402
import profit_deep as D  # noqa: E402
import profit_lab as PL  # noqa: E402
import profit_lab2 as P  # noqa: E402
import signals_live as SL  # noqa: E402
import strategy_mining as SM  # noqa: E402
import winrate_lab as W1  # noqa: E402

P.OUT = Path(tempfile.mkdtemp(prefix="fxbot_f3_out_"))              # caches of the test stay out of data/

UTC = timezone.utc
H = 3600
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- leverage per pair (ESMA retail)
for pair, lev in (("EUR/USD", 30), ("USD/JPY", 30), ("EUR/CHF", 30), ("GBP/JPY", 30), ("USD/CAD", 30),
                  ("AUD/USD", 20), ("NZD/USD", 20), ("AUD/JPY", 20)):
    assert P.leverage(pair) == lev, pair

# ---------------------------------------------------------------- weekly values known at each day
days = [date(2024, 1, 1) + timedelta(days=k) for k in range(700) if (date(2024, 1, 1) + timedelta(days=k)).weekday() < 5]
c = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.004, len(days))))
o = np.concatenate([[c[0]], c[:-1]])
h, l_ = np.maximum(o, c) * 1.001, np.minimum(o, c) * 0.999
full = PL.weekly_aligned(days, o, h, l_, c)
for cut in (300, 301, 302, 303, 304, 450):                          # every weekday as the last known day
    part = PL.weekly_aligned(days[:cut], o[:cut], h[:cut], l_[:cut], c[:cut])
    for key, v in part.items():
        assert np.allclose(v, full[key][:cut], equal_nan=True), (key, cut)
assert np.array_equal(full["week_end"], [d.weekday() == 4 for d in days])

# ---------------------------------------------------------------- RSI of a flat market = neutral 50
flat = np.full(30, 1.25)
assert np.allclose(K.rsi(flat, 2)[5:], 50.0) and np.allclose(SM.rsi(flat, 2)[5:], 50.0)

# ---------------------------------------------------------------- the two indicator libraries agree
x = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.005, 800)))           # (strategy_mining: model, indikatory: research)
for n in (2, 3, 14):
    assert np.allclose(SM.rsi(x, n)[30:], K.rsi(x, n)[30:], atol=1e-9), n
assert np.allclose(SM.ema(x, 20)[200:], K.ema(x, 20)[200:], rtol=1e-9)   # EMA: other seed, the same after
                                                                           # the warm-up (10 x the period)

# ---------------------------------------------------------------- Bollinger: the same value whatever the start
jpy = 150 * np.exp(np.cumsum(rng.normal(0, 0.003, 1500)))
atr = np.full(1500, 0.5)
a_full = W1.indicators(jpy, jpy * 1.002, jpy * 0.998, jpy, atr)
for i in (900, 1200, 1499):
    a_pre = W1.indicators(*(x[i - 400:i + 1] for x in (jpy, jpy * 1.002, jpy * 0.998, jpy, atr)))
    for key in ("bb20_2.0", "bb20_1.5", "bb10_2.0"):
        assert abs(a_full[key][i] - a_pre[key][-1]) <= 1e-11, (key, i)

# ---------------------------------------------------------------- live timing of the simulator (decide_h)
SYMBOL, N_DAYS = "EUR/USD", 330
t0 = int(datetime(2025, 1, 6, 22, tzinfo=UTC).timestamp())
cal = [date(2025, 1, 7) + timedelta(days=k) for k in range(N_DAYS)]
i0 = next(i for i in range(280, N_DAYS) if cal[i].weekday() == 4)  # the Friday with the late-day turn
hc = 1.0 * (1 + 2e-5 * np.arange(N_DAYS * 24))                       # a steady rise: RSI(2) = 100, no buy signal
first = np.arange(N_DAYS) * 24
last = first + 23
prev = hc[first[i0] - 1]
hc[first[i0]:last[i0]] = np.linspace(prev * 0.995, prev * 0.97, last[i0] - first[i0])   # -3 % by 16:00 New York
hc[last[i0]:] = prev * 1.0001 * (1 + 2e-5 * np.arange(len(hc) - last[i0]))             # back up by the close
ho = np.concatenate([[hc[0]], hc[:-1]])
hh, hl = np.maximum(ho, hc), np.minimum(ho, hc)
s = {"ts": t0 + np.arange(N_DAYS * 24) * H, "o": ho, "h": hh, "l": hl, "c": hc, "days": cal, "first": first,
     "last": last, "do": ho[first], "dh": np.array([hh[a:b + 1].max() for a, b in zip(first, last)]),
     "dl": np.array([hl[a:b + 1].min() for a, b in zip(first, last)]), "dc": hc[last], "close_ts": t0 + (last + 1) * H}
rates = {"EUR": {(y, m): 1.0 for y in range(2023, 2028) for m in range(1, 13)},
         "USD": {(y, m): 0.5 for y in range(2023, 2028) for m in range(1, 13)}}
I = P.indicators(s, rates, SYMBOL)
I.update(vix=np.full(N_DAYS, 15.0), vix_rise=np.zeros(N_DAYS), rates_mom=np.full(N_DAYS, 0.5))
D._cache.clear()
D._cache["rates"] = rates
D._cache[(SYMBOL, 2, 3, 0, "oecd")] = (s, I)
_, J0 = D.prepared_live(SYMBOL, 2, 3, "oecd", 0, (4,))
for key, v in I.items():                                             # cut 0 = the full series
    if isinstance(v, np.ndarray) and v.dtype != object:
        assert np.allclose(np.asarray(v, float), np.asarray(J0[key], float), rtol=1e-9, atol=1e-10, equal_nan=True), key
_, J1 = D.prepared_live(SYMBOL, 2, 3, "oecd", 1, (4,))
live_c = np.append(s["dc"][:i0], hc[last[i0] - 1])                  # earlier days full, the Friday at 16:00
assert abs(J1["rsi2"][i0] - SM.rsi(live_c, 2)[-1]) < 1e-9 and J1["rsi2"][i0] < 5 < I["rsi2"][i0]
other = np.array([d.weekday() != 4 for d in cal])
assert np.array_equal(J1["rsi2"][other], I["rsi2"][other], equal_nan=True)   # other days untouched
assert np.array_equal(J1["rates_mom"], I["rates_mom"])              # known inputs kept
half = (P.SPREAD_PIPS[SYMBOL] / 2 + P.SLIPPAGE_PIPS / 2) * 0.0001
rule = D.Rule("t", fund="rates_up", rates_thr=0.25, min_tp_pct=0.0)
at_close = [t for t in D.simulate(rule, [SYMBOL]) if t["day"] == cal[i0]]
live = [t for t in D.simulate(D.Rule("t", fund="rates_up", rates_thr=0.25, min_tp_pct=0.0, decide_h=1), [SYMBOL])
        if t["day"] == cal[i0]]
assert at_close == [] and len(live) == 1, (at_close, live)          # the 16:00 signal is gone by the close
assert abs(live[0]["entry"] - (hc[last[i0] - 1] + half)) < 1e-12     # entered at the 16:00 price (ask)
try:
    D.simulate(D.Rule("t", decide_h=1, knife_days=3), [SYMBOL])
    raise AssertionError("decide_h with an option that needs the full close must fail loudly")
except NotImplementedError:
    pass
D._cache.clear()

# ---------------------------------------------------------------- forward test: costs, order, leverage, time exit
start = int(datetime(2026, 9, 25, 20, tzinfo=UTC).timestamp())
pair = "AUD/USD"
hp = (P.SPREAD_PIPS[pair] / 2 + P.SLIPPAGE_PIPS / 2) * 0.0001


def fwd(path):
    n = len(path)
    hb = {"ts": start + np.arange(1, n + 1) * H, "h": np.array([p[0] for p in path]),
          "l": np.array([p[1] for p in path]), "c": np.array([p[2] for p in path])}
    t = {"id": "x", "par": pair, "smer": "KOUPIT", "den": "2026-09-25", "cas_vstupu": start, "vstup": 0.70,
         "tp": 0.705, "sl": 0.68, "stav": "otevreny", "cb_vystup": False, "swap_proc_rocne": 0.0}
    SL.resolve_forward([t], {pair: hb})
    return t


t = fwd([(0.701, 0.699, 0.70), (0.705 + hp + 1e-6, 0.70, 0.704)])
entry = 0.70 + hp
assert t["duvod_vystupu"] == "TP" and abs(t["vysledek_proc_marze"] - round((0.705 - entry) / entry * 100 * 20, 1)) < 1e-9
t = fwd([(0.705 + hp + 1e-6, 0.68 - 1e-6, 0.70)])                   # target and stop in the same hour: the stop
assert t["duvod_vystupu"] == "SL" and t["vysledek_proc_marze"] < 0
t = fwd([(0.701, 0.699, 0.70)] * 485)                                # neither: out after 20 trading days of hours
assert t["duvod_vystupu"] == "cas" and t["cas_vystupu"] == start + 481 * H
t = fwd([(0.7049, 0.6999, 0.70)])                                    # target touched only by the bid without the spread
assert t["stav"] == "otevreny" and "prubezne_proc_marze" in t

# ---------------------------------------------------------------- live daily bars: the Friday decision at 16:00 New York
fri0 = int(datetime(2026, 9, 20, 21, tzinfo=UTC).timestamp())       # Monday's trading day opens Sunday 17:00 New York
n_h = 5 * 24 + 1                                                     # Monday-Friday + one tick after the Friday close
yb = {"ts": fri0 + np.arange(n_h) * H, "o": np.full(n_h, 1.0), "h": np.full(n_h, 1.001), "l": np.full(n_h, 0.999),
      "c": 1.0 + np.arange(n_h) * 1e-4}
D_all = SL.daily(yb)
assert [d.weekday() for d in D_all["days"]] == [0, 1, 2, 3, 4]      # the tick after the close is not a "Saturday"
friday = D_all["days"][-1]
cut = SL.decision_cut(friday)
assert datetime.fromtimestamp(cut, tz=SL.NEW_YORK).hour == 16
D_dec = SL.daily(SL.until(yb, cut))
assert D_dec["days"][-1] == friday and int(D_dec["last_ts"][-1]) == cut - H
assert abs(D_dec["c"][-1] - yb["c"][np.searchsorted(yb["ts"], cut) - 1]) < 1e-12   # the 16:00 price

# ---------------------------------------------------------------- bet-sizing systems (portfolio_sim.Money, R-031)
import portfolio_sim as PS  # noqa: E402

seq = [-1, -1, 5, -1, -1, -1, -1, 3]
for spec, want in (("martingale:2:3", [1, 2, 4, 1, 2, 4, 8, 8]), ("fibonacci:5", [1, 1, 2, 1, 1, 2, 3, 5]),
                   ("dalembert:0.5:3", [1, 1.5, 2, 1.5, 2, 2.5, 3, 3]), ("anti:1.5:2", [1, 1, 1, 1.5, 1, 1, 1, 1])):
    mm, got = PS.Money(spec), []
    for r in seq:
        got.append(mm.mult())
        mm.update(r)
    assert np.allclose(got, want), (spec, got)
T0 = int(datetime(2024, 3, 1, tzinfo=UTC).timestamp())
seq_trades = [{"pair": p, "side": 1, "day": date(2024, 3, 1), "t_in": T0 + k * 10 * 86400, "t_out": T0 + (k * 10 + 5) * 86400,
               "margin_pct": v} for k, (p, v) in enumerate((("EUR/USD", -50.0), ("GBP/USD", 20.0), ("USD/JPY", 20.0)))]
flat = PS.run_portfolio([seq_trades], 0.1, (2024, 2024))
mart = PS.run_portfolio([seq_trades], 0.1, (2024, 2024), money="martingale:2:3")
eq = 1 - 0.1 * 0.5                                                # loss of 50 % of a 10 % margin
eq = eq + 2 * 0.1 * eq * 0.2                                      # the next trade doubled after the loss
eq = eq + 0.1 * eq * 0.2                                          # back to 1x after the win
assert abs(mart["equity"] - eq) < 1e-12 and abs(flat["equity"] - 0.95 * 1.02 * 1.02) < 1e-12

print("=" * 60)
print("F3 AUDIT 2026-10-04 REGRESSIONS")
print("=" * 60)
print("LEVERAGE PER PAIR (1:30 / 1:20): PASS")
print("WEEKLY VALUES WITHOUT LOOK-AHEAD, WEEK END = FRIDAY: PASS")
print("RSI FLAT = 50, BOTH INDICATOR LIBRARIES AGREE, BOLLINGER INDEPENDENT OF THE SERIES START: PASS")
print("LIVE TIMING (DECISION AT 16:00 NEW YORK, EARLIER DAYS FULL): PASS")
print("FORWARD TEST: COSTS, STOP BEFORE TARGET, LEVERAGE, TIME EXIT: PASS")
print("LIVE DAILY BARS: NO PHANTOM SATURDAY, FRIDAY UP TO 16:00 NEW YORK: PASS")
print("BET SIZING (MARTINGALE / FIBONACCI / D'ALEMBERT / ANTI) IN THE ACCOUNT SIMULATION: PASS")
print("RESULT: PASS")
print("=" * 60)
