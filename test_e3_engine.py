"""E3 - decision engine: gates, evidence classes, thesis book, Top-3
concentration, side-correct resolution, placebo geometry."""

import os
import tempfile
from dataclasses import replace
from datetime import datetime, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e3_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.database import initialize_database  # noqa: E402
from src.engine import evidence as E  # noqa: E402
from src.engine.backtest import _plan  # noqa: E402
from src.engine.decision import decide  # noqa: E402
from src.engine.evidence import Evidence  # noqa: E402
from src.engine.fundamental import CurrencyState, FundamentalView  # noqa: E402
from src.engine.params import DEFAULT_PARAMS as P  # noqa: E402
from src.engine.portfolio import select_top  # noqa: E402
from src.engine.regime import RegimeView  # noqa: E402
from src.engine.resolution import Plan, resolve  # noqa: E402
from src.engine.series import PriceSeries  # noqa: E402
from src.engine.technical import TechLevel, TechnicalView, TFView  # noqa: E402
from src.engine.thesis import MemoryThesisStore, SqliteThesisStore, ThesisBook  # noqa: E402
from src.path_archive import Bar  # noqa: E402

UTC = timezone.utc
initialize_database()
T0 = int(datetime(2026, 9, 29, 12, 0, tzinfo=UTC).timestamp())      # Tuesday, market open
H = 3600


def h1_series(closes: list[float], rng: float = 0.0010) -> PriceSeries:
    start = T0 - len(closes) * H
    bars = [Bar(start + k * H, c, c + rng / 2, c - rng / 2, c, c + 0.00002, c + rng / 2 + 0.00002,
                c - rng / 2 + 0.00002, c + 0.00002, 1, 1, 60) for k, c in enumerate(closes)]
    return PriceSeries.from_bars("EUR/USD", "1h", bars)


def tfview(tf, trend, levels=(), atr=0.0010, close=1.1010):
    return TFView(tf, 199, close, atr, 50.0, 55.0, close, close - 0.002, None, 0.3, trend, 0.4, "HH_HL", list(levels))


def tech(bias="BUY", levels=(), price=1.1010):
    return TechnicalView("EUR/USD", T0, price, tfview("1d", "UP"), tfview("4h", "UP"), tfview("1h", "UP", levels),
                         1.2, bias, 2, [("H4 trend nahoru", bias), ("D1 trend nahoru", bias)] if bias != "NONE" else [])


def fund(items=(), events_pre=(), layer="AVAILABLE"):
    view = FundamentalView("EUR/USD", T0, CurrencyState("EUR"), CurrencyState("USD"), list(items))
    view.events_pre = list(events_pre)
    view.event_layer = layer
    return view


NORMAL = RegimeView("NORMAL", "TREND", "NEUTRAL", "NONE", False)
SUPPORT = TechLevel(1.1005, 2, 150, 180, "1h", "L", "ACTIVE")
RESIST = TechLevel(1.1050, 2, 120, 160, "1h", "H", "ACTIVE")
RATES_BUY = Evidence(E.RATES_REPRICING, "BUY", 2, "diferencial +25 bp ve prospech EUR")
RATES_SELL = Evidence(E.RATES_REPRICING, "SELL", 2, "diferencial -25 bp ve prospech USD")
FLAT = h1_series([1.1010] * 200)

# ---------------------------------------------------------------- A. all gates pass -> BUY NOW, class B
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.decision == "BUY NOW" and c.confidence == "B" and c.setup_type == "PULLBACK", (c.decision, c.reasons, c.gates)
assert abs(c.stop - 1.1000) < 1e-9 and abs(c.targets[0] - 1.1040) < 1e-9, "SL = level - 0.5 ATR, TP1 capped at 3 ATR"
assert abs(c.rr_gross - 3.0) < 1e-6 and c.rr_net < c.rr_gross, "costs reduce R:R (module 55/64)"
assert c.targets[0] < c.targets[1] < c.targets[2] and c.invalidation and set(c.hypotheses) == {"H1", "H2", "H3"}

# ---------------------------------------------------------------- B. no-chase: big move in the last 4 hours -> WAIT
chase = h1_series([1.0995] * 196 + [1.0998, 1.1002, 1.1006, 1.1010])
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, chase, P, "CURRENT", 0.00002)
assert c.decision in ("WAIT FOR BUY", "NO TRADE") and c.gate("NO_CHASE").status == "FAIL"

# ---------------------------------------------------------------- C. fundamentals against the price -> NO TRADE
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_SELL]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.decision == "NO TRADE" and "fundamenty proti" in c.reasons[0] and c.thesis_direction == "BUY"

# ---------------------------------------------------------------- D. R:R after costs below 1.5 -> NO TRADE
near_resist = TechLevel(1.1016, 2, 120, 160, "1h", "H", "ACTIVE")
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, near_resist]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.decision == "NO TRADE" and "R:R" in c.reasons[0]

# ---------------------------------------------------------------- E. high-impact event ahead -> no NOW
class Ev:
    currency, title, impact, forecast, previous, scheduled_at = "USD", "CPI m/m", "High", "0.3%", "0.2%", T0 + 2 * H


c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY], [Ev()]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert not c.is_now and c.gate("EVENT").status == "FAIL"

# ---------------------------------------------------------------- F. spread too wide -> no NOW
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.0004)
assert not c.is_now and c.gate("SPREAD").status == "FAIL"

# ---------------------------------------------------------------- G. unverified live quote -> never NOW
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "STALE", 0.00002,
           live_quote_ok=False)
assert not c.is_now and c.gate("LIVE_QUOTE").status == "FAIL" and c.gate("DATA_STATE").status == "FAIL"

# ---------------------------------------------------------------- H. technical only (class C) -> never NOW
c = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.confidence == "C" and not c.is_now

# ---------------------------------------------------------------- I. direction without price confirmation -> NO TRADE
carry = Evidence(E.CARRY, "BUY", 1, "carry")
c = decide("EUR/USD", T0, tech(bias="NONE"), fund([RATES_BUY, carry]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.decision == "NO TRADE" and c.thesis_direction == "BUY" and "smer != vstup" in c.reasons[0]

# ---------------------------------------------------------------- J. weakened/expired levels are not used
weak = replace(SUPPORT, state="WEAKENED")
c = decide("EUR/USD", T0, tech(levels=[weak, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
assert c.level is None or c.level.state != "WEAKENED"

# ---------------------------------------------------------------- K. thesis book: no-instant-flip
for store in (MemoryThesisStore(), SqliteThesisStore()):
    book = ThesisBook(store)
    buy = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
    assert book.check(buy, T0, False).action == "NEW"
    book.open_thesis(buy, "P-1", T0, 24)
    sell = replace(buy, direction="SELL", decision="SELL NOW", thesis_direction="SELL")
    flip = book.check(sell, T0 + H, regime_break=False)
    assert not flip.allowed and flip.action == "BLOCKED_FLIP" and store.get("EUR/USD").state == "WEAKENED"
    assert book.check(buy, T0 + H, False).action == "KEEP", "same direction: no new prediction (hysteresis)"
    breaking = book.check(sell, T0 + 2 * H, regime_break=True)
    assert breaking.allowed and breaking.action == "FLIP_ALLOWED" and store.get("EUR/USD").state == "INVALIDATED"

book = ThesisBook(MemoryThesisStore())
book.open_thesis(buy, "P-2", T0, 24)
book.update_from_path("EUR/USD", T0 + 3 * H, "SL_BEFORE_TP1", T0 + H)
assert book.store.get("EUR/USD").state == "INVALIDATED"
assert book.check(sell, T0 + 4 * H, False).allowed, "after invalidation a new opposite thesis is allowed"

# ---------------------------------------------------------------- L. Top-3 factor concentration
base = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
eurusd = replace(base, symbol="EUR/USD", confidence="B", rr_net=2.5)
gbpusd = replace(base, symbol="GBP/USD", confidence="B", rr_net=2.0)
usdjpy = replace(base, symbol="USD/JPY", direction="SELL", decision="SELL NOW", confidence="A", rr_net=1.8)
audnzd = replace(base, symbol="EUR/CHF", direction="SELL", decision="WAIT FOR SELL", confidence="B", rr_net=1.6)
selection = select_top([eurusd, gbpusd, usdjpy, audnzd], P)
assert [c.symbol for c in selection.top][0] == "USD/JPY", "class A first"
assert "EUR/USD" in selection.concentration and "GBP/USD" in selection.concentration, "all three are short USD"
assert "EUR/CHF" in [c.symbol for c in selection.top]

# ---------------------------------------------------------------- M. side-correct resolution
def bar(ts, bid_low, bid_high, spread=0.0002, close=None):
    close = close if close is not None else (bid_low + bid_high) / 2
    return Bar(ts, close, bid_high, bid_low, close, close + spread, bid_high + spread, bid_low + spread,
               close + spread, 1, 1, 60)


plan = Plan("BUY", True, 1.1000, 1.0990, 1.1020, T0, T0 + 24 * H, 0.00002)
# mid low 1.09905 stays above the SL, but the BID low touches it -> SL for a BUY (exits at BID)
out = resolve(plan, [bar(T0, 1.0995, 1.1005, close=1.0998), bar(T0 + H, 1.0990, 1.0999)], H, T0 + 5 * H)
assert out.outcome_state == "SL_BEFORE_TP1" and abs(out.executed_entry - (1.0998 + 0.0002 + 0.00002)) < 1e-9
assert out.r_net < -1.0, "entry at ASK + slippage, exit at BID: worse than -1R"
# the BUY limit fills only when the ASK reaches the entry
wait = Plan("BUY", False, 1.1000, 1.0990, 1.1020, T0, T0 + 24 * H, 0.0)
out = resolve(wait, [bar(T0, 1.09985, 1.1010)], H, T0 + 30 * H)
assert out.triggered_at is None, "ASK low 1.10005 > entry 1.1000: not filled although the BID touched"
# ambiguous hour refined with complete 1-minute data
amb = [bar(T0, 1.0995, 1.1005, close=1.1000), bar(T0 + H, 1.0985, 1.1025)]
minutes = [bar(T0 + H + 60 * k, 1.1001, 1.1004) for k in range(60)]
minutes[10] = bar(T0 + H + 600, 1.1010, 1.1025)          # TP first at minute 10
minutes[40] = bar(T0 + H + 2400, 1.0985, 1.0995)         # SL later
out = resolve(plan, amb, H, T0 + 30 * H, minute_loader=lambda a, b: [m for m in minutes if a <= m.ts < b])
assert out.outcome_state == "TP1_BEFORE_SL" and "1min" in out.granularity
out = resolve(plan, amb, H, T0 + 30 * H, minute_loader=lambda a, b: minutes[:30])
assert out.outcome_state == "SEQUENCE_UNKNOWN", "incomplete fine path: never guessed"

# ---------------------------------------------------------------- N. placebo geometry
cand = decide("EUR/USD", T0, tech(levels=[SUPPORT, RESIST]), fund([RATES_BUY]), NORMAL, FLAT, P, "CURRENT", 0.00002)
cand = replace(cand, decision="WAIT FOR BUY", entry=1.1004, stop=1.0994, targets=[1.1030, 1.1040, 1.1050])
mirror = _plan(cand, T0, P, "SELL")
assert abs(mirror.entry - (1.1010 + 0.0006)) < 1e-9, "same pullback depth on the other side of the price"
assert abs((mirror.stop - mirror.entry) - 0.0010) < 1e-9 and abs((mirror.entry - mirror.tp1) - 0.0026) < 1e-9

print("=" * 60)
print("E3 DECISION ENGINE")
print("=" * 60)
print("GATES: NOW / NO-CHASE / FUNDAMENTALS AGAINST / R:R / EVENT / SPREAD / LIVE QUOTE: PASS")
print("EVIDENCE CLASSES A/B/C, DIRECTION != ENTRY, LEVEL STATES: PASS")
print("THESIS BOOK: NO-INSTANT-FLIP, HYSTERESIS, INVALIDATION (MEMORY + SQLITE): PASS")
print("TOP-3 FACTOR CONCENTRATION: PASS")
print("SIDE-CORRECT RESOLUTION + 1MIN REFINEMENT: PASS")
print("PLACEBO GEOMETRY: PASS")
print("RESULT: PASS")
print("=" * 60)
