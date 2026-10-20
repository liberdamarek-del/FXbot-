"""Block A5 - explicit policy for bars where SL and TP are both reachable."""

import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_a3_")

from src.historical_data import HistoricalBar
from src.paper_audit import get_recent_paper_events
from src.paper_session import (
    AMBIGUOUS_CLOSE_UNRESOLVED,
    AMBIGUOUS_CONTINUE,
    run_paper_session,
)
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side

UTC = timezone.utc


def bar(minute, o, h, l, c):
    return HistoricalBar(
        symbol="TEST/USD",
        timeframe="1min",
        bar_time=datetime(2026, 9, 29, 10, minute, tzinfo=UTC),
        open=Decimal(o), high=Decimal(h), low=Decimal(l), close=Decimal(c),
        source="TEST",
    )


def run(policy=None):
    engine = PaperTradingEngine(
        initial_cash=Decimal("10000"),
        quantity=Decimal("10"),
        symbol="TEST/USD",
        timeframe="1min",
    )
    engine.open_position(
        entry_time=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
        entry_price=Decimal("100"),
        side=Side.LONG,
        stop_loss_distance=Decimal("5"),
        take_profit_distance=Decimal("10"),
    )
    bars = [
        bar(0, "100", "103", "99", "102"),
        bar(1, "102", "111", "94", "105"),   # SL 95 and TP 110 both reachable
        bar(2, "105", "106", "104", "106"),
    ]
    kwargs = {} if policy is None else {"ambiguous_policy": policy}
    return engine, run_paper_session(
        bars=bars, engine=engine, symbol="TEST/USD", timeframe="1min", **kwargs
    )


# 1. Default = legacy behaviour, numerically unchanged
engine, legacy = run()
assert legacy.ambiguous_bars == 1
assert legacy.unresolved_trades == 0
assert legacy.trades == 1 and legacy.forced_close is True
assert legacy.realized_pnl == Decimal("60")     # closed at END_OF_DATA close 106
assert engine.position_simulator.position is None

# explicit CONTINUE gives the identical result
_, explicit = run(AMBIGUOUS_CONTINUE)
assert (explicit.trades, explicit.realized_pnl, explicit.forced_close) == (
    legacy.trades, legacy.realized_pnl, legacy.forced_close,
)

# 2. CLOSE_UNRESOLVED: closed at the OPEN of the ambiguous bar, no assumed order
engine, resolved = run(AMBIGUOUS_CLOSE_UNRESOLVED)
assert resolved.ambiguous_bars == 1
assert resolved.unresolved_trades == 1
assert resolved.trades == 1
assert resolved.stop_loss_exits == 0 and resolved.take_profit_exits == 0
assert resolved.forced_close is False
assert resolved.realized_pnl == Decimal("20")   # (102 - 100) * 10
assert engine.position_simulator.position is None

# 3. Audit trail: AMBIGUOUS events for every ambiguous bar, both policies;
#    the unresolved close carries its own reason.
events = get_recent_paper_events("TEST/USD", "1min", limit=100)
ambiguous = [e for e in events if e["event_type"] == "AMBIGUOUS"]
assert len(ambiguous) == 3, len(ambiguous)     # legacy, explicit, unresolved
assert all(e["reason"] == "SL_AND_TP_IN_SAME_BAR" for e in ambiguous)
assert all(e["side"] == "LONG" for e in ambiguous)

closes = [e for e in events if e["event_type"] == "CLOSE"]
assert any(e["reason"] == "UNRESOLVED_SEQUENCE" for e in closes)

# 4. Unknown policy is rejected before anything runs
try:
    run("GUESS_THE_ORDER")
except ValueError:
    pass
else:
    raise AssertionError("unsupported policy was accepted")

print("=" * 60)
print("A5 AMBIGUOUS BAR POLICY")
print("=" * 60)
print("LEGACY DEFAULT UNCHANGED: PASS")
print("CLOSE_UNRESOLVED AT BAR OPEN: PASS")
print("UNRESOLVED COUNTED SEPARATELY: PASS")
print("AUDIT EVENTS RECORDED: PASS")
print("INVALID POLICY REJECTED: PASS")
print("RESULT: PASS")
print("=" * 60)
