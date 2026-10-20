"""Block B7 - paced updater: at most one API call per pace interval."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b7_")
os.environ["BAR_SETTLE_SECONDS"] = "0"
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "120"
os.environ["UPDATE_INITIAL_BARS"] = "600"        # keeps the simulation light

from src.data_state import DataState, get_status
from src.data_update import DEFAULT_SYMBOLS, MAJOR_PAIRS
from src.database import get_connection, initialize_database
from src.gap_detector import timeframe_delta
from src.market_session import is_fx_market_open
from src.models import RawBar
from src.rate_limiter import CreditBudget
from src.update_service import (
    pace_seconds,
    pick_next,
    run_service,
    seconds_until_next_utc_day,
)

UTC = timezone.utc
initialize_database()


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class Sim:
    """Simulated time shared by the clock, the budget and the provider."""

    def __init__(self, start):
        self.now = start
        self.sleeps = []

    def clock(self):
        return self.now

    def stamp(self):
        return self.now.timestamp()

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += timedelta(seconds=seconds)


class SimProvider:
    def __init__(self, sim, budget):
        self.sim, self.budget = sim, budget
        self.call_times = []

    @property
    def now(self):
        return self.sim.now

    def _bars(self, symbol, timeframe, start, end):
        interval, current, out = timeframe_delta(timeframe), start, []
        while current <= end:
            if is_fx_market_open(current) and current <= self.now:
                out.append(RawBar(symbol, timeframe, current, self.now, Decimal("1.1"),
                                  Decimal("1.2"), Decimal("1.0"), Decimal("1.1"), "TwelveData"))
            current += interval
        return list(reversed(out))

    def fetch_bars(self, symbol, timeframe="1min", limit=100):
        self.budget.acquire()
        self.call_times.append(self.now)
        # like the real provider: bars lie on the minute grid
        end = self.now.replace(second=0, microsecond=0)
        return self._bars(symbol, timeframe, end - timedelta(days=6), end)[:limit]

    def fetch_bars_range(self, symbol, timeframe, start, end):
        self.budget.acquire()
        self.call_times.append(self.now)
        return self._bars(symbol, timeframe, start, end)


def make(start, per_day=720, per_minute=7):
    sim = Sim(start)
    budget = CreditBudget(per_minute=per_minute, per_day=per_day, provider=f"b7-{start.isoformat()}-{per_day}",
                          clock=sim.stamp, sleep=sim.sleep)
    provider = SimProvider(sim, budget)
    provider.budget_obj = budget
    provider.budget = budget
    return sim, budget, provider


# ------------------------------------------------------------ 1. defaults and pace
from src.data_update import CROSS_PAIRS

assert len(MAJOR_PAIRS) == 7 and len(CROSS_PAIRS) == 5
assert DEFAULT_SYMBOLS.split(",") == list(MAJOR_PAIRS + CROSS_PAIRS)
assert len(DEFAULT_SYMBOLS.split(",")) == 12
assert set(MAJOR_PAIRS) == {"EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD"}
assert pace_seconds(CreditBudget(7, 720)) == 120.0
assert pace_seconds(CreditBudget(7, 360)) == 240.0
assert seconds_until_next_utc_day(at("2026-09-30T23:59:00")) == 65.0

# ------------------------------------------------------------ 2. pick_next: no data first, then biggest backlog
NOW = at("2026-09-30T10:00:30")
instruments = [("AAA/USD", "1min"), ("BBB/USD", "1min"), ("CCC/USD", "1min")]
assert pick_next(instruments, NOW) in instruments                 # all MISSING
for minute in range(0, 60):                                       # BBB: complete up to 09:59
    RawBar  # noqa
    from src.storage import save_raw_bar
    save_raw_bar(RawBar("BBB/USD", "1min", at("2026-09-30T09:00") + timedelta(minutes=minute), NOW,
                        Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData"))
for minute in range(0, 30):                                       # CCC: up to 09:29 (30 missing)
    save_raw_bar(RawBar("CCC/USD", "1min", at("2026-09-30T09:00") + timedelta(minutes=minute), NOW,
                        Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData"))
assert get_status("BBB/USD", "1min", now=NOW).state == DataState.CURRENT
assert pick_next(instruments, NOW) == ("AAA/USD", "1min"), "instrument without data goes first"
assert pick_next([("BBB/USD", "1min"), ("CCC/USD", "1min")], NOW) == ("CCC/USD", "1min")
assert pick_next([("BBB/USD", "1min")], NOW) is None

# ------------------------------------------------------------ 3. weekend: no calls at all
sim, budget, provider = make(at("2026-09-26T12:00:00"))
events = []
summary = run_service(provider, [("WK1/USD", "1min")], budget=budget, max_turns=5,
                      clock=sim.clock, sleep=sim.sleep, on_event=events.append)
# an instrument without any data is loaded ONCE (the last session), then the
# weekend costs nothing: state CLOSED -> no further calls
assert len(provider.call_times) == 1, len(provider.call_times)
assert summary["calls"] == 1
assert get_status("WK1/USD", "1min", now=sim.now).state == DataState.CLOSED
assert summary["idle"] >= 3

# ------------------------------------------------------------ 4. spacing: never faster than the pace
majors = [(s, "1min") for s in MAJOR_PAIRS]
sim, budget, provider = make(at("2026-09-28T08:00:30"))
run_service(provider, majors, budget=budget, max_turns=30, clock=sim.clock, sleep=sim.sleep,
            on_event=lambda line: None)
times = provider.call_times
assert len(times) >= 20, len(times)
# a turn may use up to 2 calls, then the service sleeps 2 x pace: the AVERAGE spacing must be >= pace
span = (times[-1] - times[0]).total_seconds()
average = span / (len(times) - 1)
assert average >= 119.0, f"average spacing {average:.1f}s < 120s"
# never more than 2 calls inside one 120 s window
for i, t in enumerate(times):
    window = [x for x in times if t <= x < t + timedelta(seconds=120)]
    assert len(window) <= 2, (t, len(window))

# every major pair received data (no pair starved)
with get_connection() as c:
    got = {r[0] for r in c.execute("SELECT DISTINCT symbol FROM raw_bars")}
assert set(MAJOR_PAIRS) <= got, set(MAJOR_PAIRS) - got

# ------------------------------------------------------------ 5. one simulated day: budget and reserve are never touched
# (hourly bars + a budget of 100 credits keep the simulation fast; the
# budget / reserve logic is the same as with 720 credits and 1min bars)
hourly = [(s, "1h") for s in MAJOR_PAIRS]
sim, budget, provider = make(at("2026-09-29T00:00:30"), per_day=100)
assert pace_seconds(budget) == 864.0
events = []


def stop_after_the_day(seconds):
    sim.sleep(seconds)
    if sim.now >= at("2026-09-30T00:00"):
        raise KeyboardInterrupt        # run_service stops cleanly on Ctrl+C


run_service(provider, hourly, budget=budget, reserve=40, idle_seconds=600, max_turns=3000,
            clock=sim.clock, sleep=stop_after_the_day, on_event=events.append)
assert any("Zastaveno" in e for e in events)
day_calls = [t for t in provider.call_times if t.date() == at("2026-09-29T00:00").date()]
assert len(day_calls) <= 100 - 40 + 2, len(day_calls)            # reserve untouched (+ one turn of slack)
assert len(day_calls) >= 50, len(day_calls)                      # ... but the budget was really used
assert budget.status()["day_remaining"] >= 0
assert any("rezerva" in e for e in events), "reserve stop expected"
print("simulated day: calls =", len(day_calls), "| last call:", max(day_calls).strftime("%H:%M"))

# ------------------------------------------------------------ 6. daily budget used up -> waits for tomorrow
fresh = [(f"EX{i}/USD", "1min") for i in range(5)]

# 6a) another program (e.g. a manual update) already used 2 of 3 credits today
sim, budget, provider = make(at("2026-09-28T08:00:30"), per_day=3)
budget.acquire(); budget.acquire()
events = []
run_service(provider, fresh, budget=budget, reserve=0, max_turns=3, clock=sim.clock,
            sleep=sim.sleep, on_event=events.append)
first_day = [t for t in provider.call_times if t.date() == at("2026-09-28T00:00").date()]
assert len(first_day) == 1, len(first_day)               # exactly the one credit that was left
assert any("novy den" in e for e in events)
assert sim.now.date() > at("2026-09-28T00:00").date(), "service must sleep into the next UTC day"

# 6b) the budget runs out DURING a request (someone else was faster)
from src.rate_limiter import RateLimitExceeded

class ExhaustedProvider(SimProvider):
    def fetch_bars(self, *args, **kwargs):
        raise RateLimitExceeded("daily API budget used up (3/3 credits, UTC day)")
    fetch_bars_range = fetch_bars

sim, budget, _ = make(at("2026-09-28T09:00:30"), per_day=3)     # own counter (name contains the start time)
provider = ExhaustedProvider(sim, budget)
provider.budget = budget
events = []
run_service(provider, fresh, budget=budget, reserve=0, max_turns=1, clock=sim.clock,
            sleep=sim.sleep, on_event=events.append)
assert any("vycerpan" in e for e in events), events
assert sim.now.date() > at("2026-09-28T00:00").date()

# ------------------------------------------------------------ 6c. derived timeframes are built after new 1min bars, at no credit
from src.resample import DERIVED_SOURCE

sim, budget, provider = make(at("2026-09-28T09:00:30"), per_day=200)
d_inst = [("DRV/USD", "1min")]
run_service(provider, d_inst, budget=budget, reserve=0, max_turns=1, derive_targets=["5min", "15min", "1h"],
            clock=sim.clock, sleep=sim.sleep, on_event=lambda line: None)
credits_used = budget.status()["day_used"]
with get_connection() as c:
    got = {r[0] for r in c.execute("SELECT DISTINCT timeframe FROM raw_bars WHERE symbol='DRV/USD' AND source=?", (DERIVED_SOURCE,))}
assert {"5min", "15min", "1h"} <= got, got
assert credits_used == len(provider.call_times), "deriving must not cost any API credit"

# ------------------------------------------------------------ 7. guards
for bad in (lambda: run_service(provider, [], budget=budget),
            lambda: run_service(provider, majors, budget=budget, reserve=-1)):
    try:
        bad()
    except ValueError:
        pass
    else:
        raise AssertionError("bad argument accepted")

print("=" * 60)
print("B7 PACED UPDATER")
print("=" * 60)
print("12 DEFAULT PAIRS (7 MAJORS + 5 CROSSES): PASS")
print("PACE = 86400 / DAILY BUDGET (120 s): PASS")
print("MOST OVERDUE INSTRUMENT FIRST: PASS")
print("WEEKEND: ONE INITIAL LOAD, THEN ZERO CALLS: PASS")
print("AVERAGE SPACING >= 120 s, NO BURSTS: PASS")
print("ALL SEVEN PAIRS SERVED (NO STARVATION): PASS")
print("SIMULATED DAY <= BUDGET, RESERVE KEPT: PASS")
print("DAILY LIMIT -> WAITS FOR NEW UTC DAY: PASS")
print("DERIVED TIMEFRAMES AT NO CREDIT: PASS")
print("RESULT: PASS")
print("=" * 60)
