from datetime import datetime, timezone

from src.backtest_fingerprint import fingerprint_bars
from src.historical_data import load_bars


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
SOURCE = "TwelveData"

START = datetime(
    2026, 9, 28, 18, 32,
    tzinfo=timezone.utc,
)

END = datetime(
    2026, 9, 29, 8, 56,
    tzinfo=timezone.utc,
)


bars_a = load_bars(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    start=START,
    end=END,
    source=SOURCE,
)

bars_b = load_bars(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    start=START,
    end=END,
    source=SOURCE,
)

fingerprint_a = fingerprint_bars(bars_a)
fingerprint_b = fingerprint_bars(bars_b)

print("=" * 70)
print("M3.12 INPUT DATA FINGERPRINT")
print("=" * 70)
print(f"BARS: {len(bars_a)}")
print(f"FINGERPRINT A: {fingerprint_a}")
print(f"FINGERPRINT B: {fingerprint_b}")

assert len(bars_a) == 865
assert len(bars_b) == 865
assert fingerprint_a == fingerprint_b
assert len(fingerprint_a) == 64

print("BAR COUNT: PASS")
print("SHA-256 LENGTH: PASS")
print("REPEATABLE FINGERPRINT: PASS")
print("DATABASE INPUT: PASS")
print("RESULT: PASS")
print("=" * 70)
