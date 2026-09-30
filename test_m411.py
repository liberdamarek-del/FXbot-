from datetime import datetime, timezone
from decimal import Decimal

from src.paper_audit import (
    initialize_paper_audit,
    record_paper_event,
)


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)


# Valid OPEN
event_id = record_paper_event(
    event_time=T0,
    symbol="TEST/VALID",
    timeframe="1min",
    event_type="OPEN",
    side="LONG",
    price=Decimal("100"),
    quantity=Decimal("10"),
)

assert event_id > 0


# Invalid event type
try:
    record_paper_event(
        T0, "TEST/X", "1min", "INVALID",
    )
    raise AssertionError("invalid event_type was accepted")
except ValueError:
    pass


# Invalid side
try:
    record_paper_event(
        T0, "TEST/X", "1min", "OPEN",
        side="INVALID",
        price=Decimal("100"),
        quantity=Decimal("10"),
    )
    raise AssertionError("invalid side was accepted")
except ValueError:
    pass


# Negative price
try:
    record_paper_event(
        T0, "TEST/X", "1min", "OPEN",
        side="LONG",
        price=Decimal("-1"),
        quantity=Decimal("10"),
    )
    raise AssertionError("negative price was accepted")
except ValueError:
    pass


# Zero quantity
try:
    record_paper_event(
        T0, "TEST/X", "1min", "OPEN",
        side="LONG",
        price=Decimal("100"),
        quantity=Decimal("0"),
    )
    raise AssertionError("zero quantity was accepted")
except ValueError:
    pass


# OPEN with realized P&L
try:
    record_paper_event(
        T0, "TEST/X", "1min", "OPEN",
        side="LONG",
        price=Decimal("100"),
        quantity=Decimal("10"),
        realized_pnl=Decimal("100"),
    )
    raise AssertionError("OPEN accepted realized P&L")
except ValueError:
    pass


# CLOSE without realized P&L
try:
    record_paper_event(
        T0, "TEST/X", "1min", "CLOSE",
        side="LONG",
        price=Decimal("110"),
        quantity=Decimal("10"),
    )
    raise AssertionError("CLOSE without P&L was accepted")
except ValueError:
    pass


# OPEN without side
try:
    record_paper_event(
        T0, "TEST/X", "1min", "OPEN",
        price=Decimal("100"),
        quantity=Decimal("10"),
    )
    raise AssertionError("OPEN without side was accepted")
except ValueError:
    pass


# CLOSE without price
try:
    record_paper_event(
        T0, "TEST/X", "1min", "CLOSE",
        side="LONG",
        quantity=Decimal("10"),
        realized_pnl=Decimal("100"),
    )
    raise AssertionError("CLOSE without price was accepted")
except ValueError:
    pass


# Naive timestamp
try:
    record_paper_event(
        datetime(2026, 9, 29, 10, 0),
        "TEST/X",
        "1min",
        "OPEN",
        side="LONG",
        price=Decimal("100"),
        quantity=Decimal("10"),
    )
    raise AssertionError("naive timestamp was accepted")
except ValueError:
    pass


print("=" * 60)
print("M4.11 PAPER AUDIT VALIDATION")
print("=" * 60)
print("VALID EVENT: PASS")
print("EVENT TYPE VALIDATION: PASS")
print("SIDE VALIDATION: PASS")
print("PRICE VALIDATION: PASS")
print("QUANTITY VALIDATION: PASS")
print("OPEN PNL VALIDATION: PASS")
print("CLOSE PNL VALIDATION: PASS")
print("REQUIRED FIELDS: PASS")
print("TIMESTAMP VALIDATION: PASS")
print("RESULT: PASS")
print("=" * 60)
