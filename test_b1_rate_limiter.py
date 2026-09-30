"""Block B1 - credit budget (per minute / per day, shared, persistent)."""

import os
import tempfile
from datetime import datetime, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b1_")

from src.database import get_connection
from src.rate_limiter import CreditBudget, RateLimitExceeded


class FakeTime:
    def __init__(self, start: float):
        self.now = start
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


T0 = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc).timestamp()

# ------------------------------------------------------------------
# 1. per-minute limit: the 4th call in the same minute must WAIT, not fail
# ------------------------------------------------------------------
ft = FakeTime(T0)
budget = CreditBudget(per_minute=3, per_day=100, clock=ft.clock, sleep=ft.sleep)

for _ in range(3):
    budget.acquire()

assert ft.sleeps == [], "first calls must not wait"

budget.acquire()  # 4th

assert len(ft.sleeps) == 1, ft.sleeps
assert 59.9 <= ft.sleeps[0] <= 60.2, ft.sleeps   # waits for oldest call to age out
status = budget.status()
assert status["day_used"] == 4
assert status["minute_used"] <= 3

# ------------------------------------------------------------------
# 2. daily limit: raises immediately (waiting would not help)
# ------------------------------------------------------------------
ft = FakeTime(T0 + 3600)
small = CreditBudget(per_minute=10, per_day=6, clock=ft.clock, sleep=ft.sleep)

# 4 credits were already used today by the budget above (same DB, same day)
small.acquire()
small.acquire()
assert small.status()["day_used"] == 6

try:
    small.acquire()
except RateLimitExceeded as exc:
    assert "daily" in str(exc)
else:
    raise AssertionError("daily limit was not enforced")

assert small.status()["day_remaining"] == 0

# ------------------------------------------------------------------
# 3. new UTC day resets the daily counter
# ------------------------------------------------------------------
ft = FakeTime(T0 + 86400)
next_day = CreditBudget(per_minute=10, per_day=6, clock=ft.clock, sleep=ft.sleep)
assert next_day.status()["day_used"] == 0
next_day.acquire()
assert next_day.status()["day_used"] == 1

# ------------------------------------------------------------------
# 4. persistence: a NEW budget object (= program restart) sees old usage
# ------------------------------------------------------------------
restarted = CreditBudget(per_minute=10, per_day=6, clock=ft.clock, sleep=ft.sleep)
assert restarted.status()["day_used"] == 1

# ------------------------------------------------------------------
# 5. configuration: plan limits x safety margin
# ------------------------------------------------------------------
os.environ.pop("TWELVE_DATA_CREDITS_PER_MINUTE", None)
os.environ.pop("TWELVE_DATA_CREDITS_PER_DAY", None)
os.environ.pop("API_BUDGET_SAFETY", None)
default = CreditBudget.from_env()
assert (default.per_minute, default.per_day) == (7, 720), (default.per_minute, default.per_day)

os.environ["TWELVE_DATA_CREDITS_PER_MINUTE"] = "55"
os.environ["TWELVE_DATA_CREDITS_PER_DAY"] = "100000"
os.environ["API_BUDGET_SAFETY"] = "1.0"
paid = CreditBudget.from_env()
assert (paid.per_minute, paid.per_day) == (55, 100000)

os.environ["API_BUDGET_SAFETY"] = "5"
try:
    CreditBudget.from_env()
except ValueError:
    pass
else:
    raise AssertionError("invalid safety factor accepted")

# ------------------------------------------------------------------
# 6. guards
# ------------------------------------------------------------------
for bad in (0, -1):
    try:
        default.acquire(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("credits < 1 accepted")

try:
    default.acquire(8)   # more than the per-minute budget
except RateLimitExceeded:
    pass
else:
    raise AssertionError("oversized request accepted")

# ------------------------------------------------------------------
# 7. prune only removes old rows
# ------------------------------------------------------------------
ft = FakeTime(T0 + 10 * 86400)
old = CreditBudget(per_minute=10, per_day=100, clock=ft.clock, sleep=ft.sleep)
removed = old.prune(keep_days=3)
assert removed >= 1
with get_connection() as connection:
    left = connection.execute("SELECT COUNT(*) FROM api_call_log").fetchone()[0]
assert left == 0, left

print("=" * 60)
print("B1 RATE LIMITER / CREDIT BUDGET")
print("=" * 60)
print("PER-MINUTE WAIT (NOT FAIL): PASS")
print("DAILY LIMIT ENFORCED: PASS")
print("UTC DAY RESET: PASS")
print("PERSISTENT ACROSS RESTART: PASS")
print("CONFIG x SAFETY MARGIN: PASS")
print("GUARDS / PRUNE: PASS")
print("RESULT: PASS")
print("=" * 60)
