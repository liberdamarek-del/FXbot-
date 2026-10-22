from datetime import datetime, timezone
from decimal import Decimal

from src.models import RawBar


def validate_raw_bar(bar: RawBar) -> list[str]:
    errors: list[str] = []

    if not bar.symbol:
        errors.append("symbol_empty")

    if not bar.timeframe:
        errors.append("timeframe_empty")

    if bar.bar_time.tzinfo is None:
        errors.append("bar_time_missing_timezone")

    if bar.received_at.tzinfo is None:
        errors.append("received_at_missing_timezone")

    if bar.bar_time.tzinfo is not None:
        if bar.bar_time.utcoffset() is None:
            errors.append("bar_time_invalid_timezone")

    if bar.received_at.tzinfo is not None:
        if bar.received_at.utcoffset() is None:
            errors.append("received_at_invalid_timezone")

    prices = {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
    }

    for name, value in prices.items():
        if not isinstance(value, Decimal):
            errors.append(f"{name}_not_decimal")
        elif value <= Decimal("0"):
            errors.append(f"{name}_not_positive")

    if all(isinstance(value, Decimal) for value in prices.values()):
        if bar.high < bar.low:
            errors.append("high_below_low")

        if not (bar.low <= bar.open <= bar.high):
            errors.append("open_outside_range")

        if not (bar.low <= bar.close <= bar.high):
            errors.append("close_outside_range")

    if bar.bar_time.tzinfo is not None and bar.received_at.tzinfo is not None:
        if bar.received_at < bar.bar_time:
            errors.append("received_before_bar")

    return errors


def is_valid_raw_bar(bar: RawBar) -> bool:
    return not validate_raw_bar(bar)
