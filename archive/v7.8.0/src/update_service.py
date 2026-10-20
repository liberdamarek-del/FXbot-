"""Budget-paced continuous updater.

Unlike the old polling collector (a fixed poll every 30 s per instrument,
which needs thousands of calls per day), this service is built around the
daily API budget:

- PACE: on average at most ONE API call per `pace` seconds, where
  pace = 86400 / daily budget. With the free plan (800 credits/day, 90 %
  safety margin = 720) this is one call every 120 seconds.
- Every call is a catch-up: it fetches ALL bars missing since the newest
  stored bar of ONE instrument, so no bar is lost however rarely an
  instrument is visited.
- Each turn serves the instrument with the largest backlog (no data first).
- RESERVE: when only `reserve` credits are left for the UTC day, the
  service stops calling until the next UTC day, so manual runs of
  scripts/update_data.py still work.
- Closed market (weekend): no calls at all.
- After new 1-minute bars arrive, the longer timeframes (5min, 15min, 1h)
  are derived locally - they cost no credit.

Consequence for freshness: with N instruments the newest data of each one
is up to about N x pace old. That is the physical limit of the free plan,
not a defect. A paid plan raises the budget and the pace follows.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.data_state import DataState, get_status
from src.data_update import update_instrument
from src.logger import get_logger
from src.rate_limiter import CreditBudget
from src.resample import derive_symbol

logger = get_logger("update_service")

DEFAULT_RESERVE = int(os.getenv("UPDATER_RESERVE_CREDITS", "100"))
DEFAULT_IDLE_SECONDS = float(os.getenv("UPDATER_IDLE_SECONDS", "60"))
MAX_CALLS_PER_TURN = 2


def pace_seconds(budget: CreditBudget) -> float:
    """Minimum average spacing between API calls that fits the daily budget."""
    return 86400.0 / budget.per_day


def pick_next(
    instruments: list[tuple[str, str]],
    now: datetime,
) -> tuple[str, str] | None:
    """Instrument with the largest backlog; None when nothing needs data."""
    best = None
    best_key = None

    for symbol, timeframe in instruments:
        status = get_status(symbol, timeframe, now=now)

        if status.state not in (DataState.STALE, DataState.MISSING):
            continue

        # no data at all first, then the biggest number of missing bars,
        # then the oldest newest-bar
        oldest = (
            status.latest_bar_open.timestamp()
            if status.latest_bar_open
            else 0.0
        )
        key = (
            status.state == DataState.MISSING,
            status.missing_bars,
            -oldest,
        )

        if best_key is None or key > best_key:
            best, best_key = (symbol, timeframe), key

    return best


def seconds_until_next_utc_day(now: datetime) -> float:
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=5, microsecond=0
    )
    return (tomorrow - now).total_seconds()


def run_service(
    feed,
    instruments: list[tuple[str, str]],
    budget: CreditBudget | None = None,
    reserve: int = DEFAULT_RESERVE,
    idle_seconds: float = DEFAULT_IDLE_SECONDS,
    max_turns: int | None = None,
    derive_targets: list[str] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    sleep: Callable[[float], None] = time.sleep,
    on_event: Callable[[str], None] = print,
) -> dict:
    """Run until interrupted (or max_turns loop iterations, for tests)."""
    if not instruments:
        raise ValueError("no instruments configured")

    if reserve < 0:
        raise ValueError("reserve must be >= 0")

    if budget is None:
        budget = feed.budget

    pace = pace_seconds(budget)
    summary = {"turns": 0, "calls": 0, "saved": 0, "errors": 0, "idle": 0}

    on_event(
        f"Aktualizace: {len(instruments)} instrumentu, max. 1 volani / "
        f"{pace:.0f} s, rezerva {reserve} kreditu/den."
    )

    turn = 0

    try:
        while max_turns is None or turn < max_turns:
            turn += 1
            now = clock()
            status = budget.status()

            if status["day_remaining"] <= reserve:
                wait = seconds_until_next_utc_day(now)
                on_event(
                    f"Denni rozpocet: zbyva {status['day_remaining']} "
                    f"(rezerva {reserve}). Cekam na novy den UTC."
                )
                logger.info(
                    "UPDATER RESERVE REACHED | remaining=%d | wait=%.0fs",
                    status["day_remaining"],
                    wait,
                )
                summary["idle"] += 1
                sleep(wait)
                continue

            target = pick_next(instruments, now)

            if target is None:
                summary["idle"] += 1
                sleep(idle_seconds)
                continue

            symbol, timeframe = target
            result = update_instrument(
                feed,
                symbol,
                timeframe,
                now=now,
                max_calls=MAX_CALLS_PER_TURN,
            )

            summary["turns"] += 1
            summary["calls"] += result.calls
            summary["saved"] += result.saved

            # Longer timeframes are built locally from the new 1min bars
            # (no API credit).
            if derive_targets and timeframe == "1min" and result.saved:
                derive_symbol(symbol, derive_targets)

            used = budget.status()
            line = (
                f"{now:%H:%M:%S} {symbol} {timeframe}: "
                f"{result.before.state.value} -> {result.after.state.value}, "
                f"ulozeno {result.saved}, kredity dnes "
                f"{used['day_used']}/{used['day_limit']}"
            )

            if result.error:
                summary["errors"] += 1
                line += f" | CHYBA: {result.error[:100]}"

            on_event(line)

            if result.budget_exhausted:
                wait = seconds_until_next_utc_day(clock())
                on_event("Denni limit API vycerpan. Cekam na novy den UTC.")
                sleep(wait)
                continue

            # The pacing itself: every call "costs" `pace` seconds of time.
            sleep(pace * max(1, result.calls))

    except KeyboardInterrupt:
        on_event("Zastaveno uzivatelem.")

    return summary
