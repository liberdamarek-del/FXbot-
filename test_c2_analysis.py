"""Block C2 - technical analysis, setup rules, report and ledger locking."""

import importlib.util
import io
import math
import os
import random
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_c2_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
os.environ["BAR_SETTLE_SECONDS"] = "0"
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "120"
os.environ.pop("COLLECTOR_SYMBOLS", None)

from src.database import initialize_database
from src.indicators import Level
from src.market_session import is_fx_market_open
from src.models import RawBar
from src.prediction_ledger import get_prediction, list_predictions
from src.storage import save_raw_bars
from src.tech_analysis import (
    MIN_RR, MODEL_VERSION, TimeframeView,
    analyze_symbol, build_setup, classify_trend, decimals, quantize,
)

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent
initialize_database()

spec = importlib.util.spec_from_file_location("analyze", ROOT / "scripts" / "analyze.py")
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)

CURRENT = "CURRENT"
VOCAB = {"BUY NOW", "SELL NOW", "WAIT FOR BUY", "WAIT FOR SELL", "NO TRADE"}


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# ================================================================ 1. trend classification
assert classify_trend(1.10, 1.09, 1.08, 0.3) == "UP"
assert classify_trend(1.10, 1.09, 1.08, 0.05) == "RANGE"           # flat EMA
assert classify_trend(1.07, 1.08, 1.09, -0.3) == "DOWN"
assert classify_trend(1.075, 1.09, 1.08, 0.3) == "RANGE"            # close below the slow EMA
assert decimals("USD/JPY") == 3 and decimals("EUR/USD") == 5
assert str(quantize("USD/JPY", 179.18239)) == "179.182" and str(quantize("EUR/USD", 1.1234567)) == "1.12346"


# ================================================================ 2. setup rules on hand-made views
def view(trend, close, atr, supports=(), resistances=(), recent=None):
    return TimeframeView(
        timeframe="x", bars=100, last_bar_open=at("2026-09-30T10:00"), close=close, atr=atr,
        atr_percentile=50, rsi=50, ema_fast=close, ema_slow=close, slope_atr=0.3, trend=trend,
        supports=[Level(p, 3, 50) for p in supports], resistances=[Level(p, 3, 50) for p in resistances],
        recent_closes=recent or [close] * 8,
    )

A = 0.0010

def setup(t4="UP", t1="UP", price=1.1000, sup=(1.0996,), res=(1.1050,), recent=None, state=CURRENT):
    v4 = view(t4, price, A * 3, sup, res)
    v1 = view(t1, price, A, sup, res)
    v15 = view("UP", price, A / 2, recent=recent)
    return build_setup(price, v4, v1, v15, state)

s = setup(state="STALE");            assert s.decision == "NO TRADE" and "CURRENT" in s.reasons[0]
s = setup(state="CLOSED");           assert s.decision == "NO TRADE" and "CLOSED" in s.reasons[0]
s = setup(t4="RANGE", t1="UP");      assert s.decision == "NO TRADE" and "4h bez trendu" in s.reasons[0]
s = setup(t4="UP", t1="DOWN");       assert s.decision == "NO TRADE" and "proti trendu" in s.reasons[0]
s = build_setup(1.1, None, None, None, CURRENT); assert s.decision == "NO TRADE" and "historie" in s.reasons[0]

# BUY NOW: price 0.4 ATR above the support, calm market
s = setup()
assert s.decision == "BUY NOW" and s.bias == "BUY"
assert math.isclose(s.entry, 1.1000) and math.isclose(s.stop, 1.0991)               # support - 0.5 ATR
assert math.isclose(s.zone_low, 1.0996) and math.isclose(s.zone_high, 1.1000)
assert math.isclose(s.targets[0], 1.1030)                                            # capped at 3 ATR from entry
assert s.targets == sorted(s.targets) and len(s.targets) == 3
assert math.isclose(s.rr, (1.1030 - 1.1000) / (1.1000 - 1.0991))

# no-chase: 2.5 ATR move in bias direction over the last bars -> WAIT, not NOW
s = setup(recent=[1.0975] * 4 + [1.0975] * 4)
assert s.decision == "WAIT FOR BUY" and any("no-chase" in r for r in s.reasons)

# far above the support -> WAIT FOR BUY at the level
s = setup(price=1.1020)
assert s.decision == "WAIT FOR BUY" and math.isclose(s.entry, 1.0996 + 0.0003)
assert s.zone_low < s.entry < s.zone_high and s.stop < s.zone_low

# resistance too close -> R:R gate (specification: at least 1:1.5)
s = setup(res=(1.1012,))
assert s.decision == "NO TRADE" and "R:R" in s.reasons[0] and s.bias == "BUY"
# resistance far enough -> structural TP1 just before it
s = setup(res=(1.1024,))
assert s.decision == "BUY NOW" and math.isclose(s.targets[0], 1.1023) and s.rr >= MIN_RR
# no resistance at all -> ATR target
s = setup(res=())
assert s.decision == "BUY NOW" and s.rr >= MIN_RR
# no support in reach
s = setup(sup=())
assert s.decision == "NO TRADE" and "podpora" in s.reasons[0]
s = setup(sup=(1.0900,))
assert s.decision == "NO TRADE", "a support 10 ATR away is out of reach"
# level on the wrong side of the price -> structure broken
s = setup(sup=(1.1004,))
assert s.decision == "NO TRADE" and "porusena" in s.reasons[0]

# SELL mirror
s = setup(t4="DOWN", t1="RANGE", price=1.1000, sup=(1.0950,), res=(1.1004,))
assert s.decision == "SELL NOW" and s.bias == "SELL"
assert s.stop > s.entry and math.isclose(s.stop, 1.1004 + 0.0005)
assert s.targets == sorted(s.targets, reverse=True) and s.targets[0] < s.entry and s.rr >= MIN_RR
s = setup(t4="DOWN", t1="UP");       assert s.decision == "NO TRADE"


# ================================================================ 3. synthetic markets
def make_market(symbol, days, seed, base, drift, amp, period_h, sigma, start=at("2026-08-31T00:00")):
    rnd = random.Random(seed)
    bars, prev, walk = [], base, 0.0
    t, end = start, start + timedelta(days=days)
    while t < end:
        if is_fx_market_open(t):
            walk = 0.98 * walk + rnd.gauss(0, sigma)
            hours = (t - start).total_seconds() / 3600
            price = base + drift * hours / 24 + amp * math.sin(2 * math.pi * hours / period_h) + walk
            hi = max(prev, price) + abs(rnd.gauss(0, sigma * 0.5))
            lo = min(prev, price) - abs(rnd.gauss(0, sigma * 0.5))
            bars.append(RawBar(symbol, "1min", t, t + timedelta(minutes=3), Decimal(f"{prev:.5f}"),
                               Decimal(f"{hi:.5f}"), Decimal(f"{lo:.5f}"), Decimal(f"{price:.5f}"), "TwelveData"))
            prev = price
        t += timedelta(minutes=1)
    save_raw_bars(bars)
    return bars[-1].bar_time + timedelta(minutes=1, seconds=20)      # a moment after the last bar closed


def check_setup_invariants(a):
    s = a.setup
    assert s.decision in VOCAB and s.reasons
    if s.decision == "NO TRADE":
        return False
    sign = 1 if s.bias == "BUY" else -1
    assert s.decision.endswith(s.bias) or s.decision.startswith(s.bias)
    assert sign * (s.entry - s.stop) >= 0.5 * s.atr_unit, "SL must respect the ATR noise buffer"
    assert s.zone_low <= s.entry <= s.zone_high
    if s.bias == "BUY":
        assert s.stop < s.zone_low and s.targets == sorted(s.targets) and s.targets[0] > s.entry
    else:
        assert s.stop > s.zone_high and s.targets == sorted(s.targets, reverse=True) and s.targets[0] < s.entry
    assert len(set(s.targets)) == 3
    assert s.rr >= MIN_RR - 1e-9 and math.isclose(s.rr, sign * (s.targets[0] - s.entry) / (sign * (s.entry - s.stop)))
    return True


# a deliberate up-trend, down-trend and range
now_up = make_market("UPT/USD", 22, 1, 1.10, 0.006, 0.003, 14, 0.00003)
now_dn = make_market("DNT/USD", 22, 2, 1.20, -0.006, 0.003, 14, 0.00003)
now_rg = make_market("RNG/USD", 22, 3, 1.10, 0.0, 0.004, 30, 0.00003)

up = analyze_symbol("UPT/USD", now=now_up)
dn = analyze_symbol("DNT/USD", now=now_dn)
rg = analyze_symbol("RNG/USD", now=now_rg)

assert up.data_state == CURRENT and up.views["4h"].trend == "UP", (up.data_state, up.views["4h"].trend)
assert dn.views["4h"].trend == "DOWN", dn.views["4h"].trend
assert up.setup.decision != "SELL NOW" and up.setup.decision != "WAIT FOR SELL"
assert dn.setup.decision not in ("BUY NOW", "WAIT FOR BUY")
assert rg.setup.decision == "NO TRADE"
for a in (up, dn, rg):
    assert a.views["1h"] and a.views["15min"] and a.views["4h"]
    assert a.views["1h"].atr > 0 and 0 <= a.views["1h"].rsi <= 100 and 0 <= a.views["1h"].atr_percentile <= 100
    check_setup_invariants(a)

# ---------------------------------------------------------------- stale / closed data never produce a proposal
stale = analyze_symbol("UPT/USD", now=now_up + timedelta(hours=3))
assert stale.data_state == "STALE" and stale.setup.decision == "NO TRADE" and "CURRENT" in stale.setup.reasons[0]
weekend = analyze_symbol("UPT/USD", now=at("2026-09-26T12:00"))          # Saturday, newest bar is older -> not CURRENT
assert weekend.setup.decision == "NO TRADE"

# ---------------------------------------------------------------- property test: many random markets
actionable = []
for seed in range(10, 18):
    rnd = random.Random(seed)
    sym = f"P{seed}/USD"
    now = make_market(sym, 22, seed, 1.10, rnd.uniform(-0.008, 0.008), rnd.uniform(0.002, 0.006),
                      rnd.uniform(8, 40), 0.00003)
    a = analyze_symbol(sym, now=now)
    assert a.data_state == CURRENT
    if check_setup_invariants(a):
        actionable.append((sym, now, a))

assert actionable, "no random market produced a setup - thresholds or generator need review"

# ---------------------------------------------------------------- the ledger is the oracle: every actionable setup must be lockable
locked = 0
for sym, now, a in actionable:
    status = analyze.lock_setup(a, now)
    assert status.startswith("zamceno"), (sym, status)
    locked += 1
    p = get_prediction(status.split(": ")[1])
    assert p["model_version"] == MODEL_VERSION and p["data_state"] == "CURRENT" and p["data_quality"] == "C"
    assert p["forecast_mode"] == "TECHNICAL_ONLY" and p["current_state"] == "NEW"

sym, now, a = actionable[0]
assert analyze.lock_setup(a, now + timedelta(hours=1)).startswith("preskoceno"), "duplicate within 4 hours must be skipped"
assert analyze.lock_setup(analyze.analyze_symbol(sym, now=now + timedelta(hours=1)), now + timedelta(hours=1)).startswith(("preskoceno", "nelze", "zamitnuto"))
assert analyze.lock_setup(rg, now_rg).startswith("nelze zamknout")

# ---------------------------------------------------------------- CLI report (Czech, phone friendly)
os.environ["COLLECTOR_SYMBOLS"] = "UPT/USD,DNT/USD,RNG/USD"
buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = analyze.main([], now=now_up)
text = buffer.getvalue()
assert rc == 0 and "TECHNICKA ANALYZA" in text and "bez makra" in text
assert all(name in text for name in ("UPT/USD", "DNT/USD", "RNG/USD"))
assert "POZOR" not in text and "data 1min: CURRENT" in text
assert max(len(line) for line in text.splitlines()) <= 100

# three hours later nothing was updated: every pair is STALE and the report says so
buffer = io.StringIO()
with redirect_stdout(buffer):
    analyze.main([], now=now_up + timedelta(hours=3))
late = buffer.getvalue()
assert "POZOR" in late and "nelze vytvorit" in late and "STALE" in late
assert "Zadny navrh neprosel branami" in late and "TOP navrhy" not in late

buffer = io.StringIO()
with redirect_stdout(buffer):
    analyze.main(["--pair", "UPT/USD"], now=now_up)
detail = buffer.getvalue()
assert "4h:" in detail and "1h:" in detail and "15min:" in detail and "ATR" in detail and "RSI" in detail

try:
    analyze.main(["--pair"], now=now_up)
except SystemExit:
    pass
else:
    raise AssertionError("--pair without value accepted")

print("=" * 60)
print("C2 TECHNICAL ANALYSIS")
print("=" * 60)
print("TREND CLASSIFICATION, PRICE PRECISION: PASS")
print("SETUP RULES (DATA GATE, R:R >= 1.5, NO-CHASE, LEVELS, SELL MIRROR): PASS")
print("SYNTHETIC UP / DOWN / RANGE MARKETS: PASS")
print(f"PROPERTY TEST: {len(actionable)} OF 8 RANDOM MARKETS PRODUCED A SETUP, ALL CONSISTENT: PASS")
print(f"LEDGER ACCEPTS EVERY SETUP ({locked} LOCKED), DUPLICATES SKIPPED: PASS")
print("STALE / CLOSED DATA -> NO TRADE: PASS")
print("CZECH REPORT: PASS")
print("RESULT: PASS")
print("=" * 60)
