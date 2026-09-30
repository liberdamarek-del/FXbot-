from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

from src.paper_session_audit import (
    initialize_paper_session_audit,
    save_paper_session,
    get_paper_session,
)


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 29, 10, 5, tzinfo=timezone.utc)

initialize_paper_session_audit()

session_key = "M4.13_TEST_SESSION"

session_id = save_paper_session(
    session_key=session_key,
    created_at=T0,
    symbol="TEST/USD",
    timeframe="1min",
    started_at=T0,
    finished_at=T1,
    bars_processed=5,
    trades=2,
    realized_pnl=Decimal("75.50"),
    final_equity=Decimal("10075.50"),
    stop_loss_exits=1,
    take_profit_exits=1,
    ambiguous_bars=1,
    forced_close=False,
)

assert session_id > 0

row = get_paper_session(session_key)

assert row is not None
assert row["session_key"] == session_key
assert row["symbol"] == "TEST/USD"
assert row["timeframe"] == "1min"
assert row["bars_processed"] == 5
assert row["trades"] == 2
assert row["realized_pnl"] == "75.50"
assert row["final_equity"] == "10075.50"
assert row["stop_loss_exits"] == 1
assert row["take_profit_exits"] == 1
assert row["ambiguous_bars"] == 1
assert row["forced_close"] == 0


# Duplicate session key must be rejected.
try:
    save_paper_session(
        session_key=session_key,
        created_at=T0,
        symbol="TEST/USD",
        timeframe="1min",
        started_at=T0,
        finished_at=T1,
        bars_processed=1,
        trades=0,
        realized_pnl=Decimal("0"),
        final_equity=Decimal("10000"),
        stop_loss_exits=0,
        take_profit_exits=0,
        ambiguous_bars=0,
        forced_close=False,
    )
    raise AssertionError("duplicate session_key was accepted")
except sqlite3.IntegrityError:
    pass


# Invalid risk-exit count must be rejected.
try:
    save_paper_session(
        session_key="M4.13_INVALID",
        created_at=T0,
        symbol="TEST/USD",
        timeframe="1min",
        started_at=T0,
        finished_at=T1,
        bars_processed=5,
        trades=1,
        realized_pnl=Decimal("0"),
        final_equity=Decimal("10000"),
        stop_loss_exits=1,
        take_profit_exits=1,
        ambiguous_bars=0,
        forced_close=False,
    )
    raise AssertionError("invalid risk-exit count was accepted")
except ValueError:
    pass


# Invalid time ordering must be rejected.
try:
    save_paper_session(
        session_key="M4.13_INVALID_TIME",
        created_at=T0,
        symbol="TEST/USD",
        timeframe="1min",
        started_at=T1,
        finished_at=T0,
        bars_processed=1,
        trades=0,
        realized_pnl=Decimal("0"),
        final_equity=Decimal("10000"),
        stop_loss_exits=0,
        take_profit_exits=0,
        ambiguous_bars=0,
        forced_close=False,
    )
    raise AssertionError("invalid time ordering was accepted")
except ValueError:
    pass


print("=" * 60)
print("M4.13 PAPER SESSION AUDIT")
print("=" * 60)
print("SESSION SAVE: PASS")
print("SESSION READBACK: PASS")
print("P&L PERSISTENCE: PASS")
print("EQUITY PERSISTENCE: PASS")
print("RISK EXIT COUNTS: PASS")
print("AMBIGUOUS COUNT: PASS")
print("DUPLICATE KEY PROTECTION: PASS")
print("VALIDATION: PASS")
print("RESULT: PASS")
print("=" * 60)
