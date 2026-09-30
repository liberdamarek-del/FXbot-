"""On-demand data update ("catch-up").

Fetches ONLY the closed bars that are missing between the newest stored bar
and the newest bar that should exist now. If the data is already complete,
no API credit is spent at all. This is what makes the free provider plan
(8 credits/minute, 800/day) sufficient for a run-when-needed workflow:
one request can return many bars.

Rules:
- only CLOSED and SETTLED bars are stored: a bar is stored only when at least
  BAR_SETTLE_SECONDS (default 120) have passed since it closed. Evidence from
  the collected data: a 5-minute bar fetched 12 s after it closed still missed
  its last minute (its low and close were wrong), and INSERT OR IGNORE would
  have kept that preliminary bar forever. The settle time is PROVISIONAL,
- only bars inside the trading session are stored. The provider also
  delivers off-hours quotes (observed: about 1 400 one-minute bars between
  Saturday 21:34 and Sunday 20:59 UTC, thin market, one-minute ranges of
  0.18 JPY). They would distort ATR and levels, so they are skipped and
  counted (existing ones can be moved away with
  scripts/quarantine_offsession.py),
- the still-forming bar is never stored,
- every bar passes the existing validator,
- saving is idempotent (duplicates are ignored, nothing is overwritten),
- older parts that do not fit into the call limit are NOT silently dropped:
  the newest bars are fetched first (so the data becomes current) and the
  untouched older part is reported as a remaining gap,
- every instrument gets a collector_runs audit row,
- one failing instrument never stops the others.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.data_state import (
    DataState,
    DataStatus,
    classify,
    expected_last_bar_open,
    get_earliest_bar_open,
    get_latest_bar_open,
)
from src.gap_detector import detect_gaps, timeframe_delta
from src.market_session import is_fx_market_open
from src.logger import get_logger
from src.rate_limiter import ProviderRateLimited, RateLimitExceeded
from src.storage import (
    finish_collector_run,
    save_raw_bars,
    start_collector_run,
)
from src.validator import validate_raw_bar

logger = get_logger("data_update")

DEFAULT_SOURCE = "TwelveData"

# The seven major currency pairs plus five crosses (chosen with the user;
# module 17 of the model specification lists further crosses - add them
# through COLLECTOR_SYMBOLS when wanted).
MAJOR_PAIRS = (
    "EUR/USD",
    "USD/JPY",
    "GBP/USD",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
)
CROSS_PAIRS = (
    "EUR/JPY",
    "GBP/JPY",
    "EUR/GBP",
    "EUR/CHF",
    "AUD/JPY",
)
DEFAULT_SYMBOLS = ",".join(MAJOR_PAIRS + CROSS_PAIRS)

# Only 1-minute bars are downloaded; longer timeframes are derived locally
# (src/resample.py) and cost no API credit.
DEFAULT_TIMEFRAMES = "1min"
DEFAULT_DERIVED_TIMEFRAMES = "5min,15min,1h"

# Bars requested in one range call. The provider allows up to 5000 bars per
# request (1 credit per symbol per request); 4500 keeps a safety margin.
DEFAULT_MAX_BARS_PER_CALL = int(os.getenv("UPDATE_MAX_BARS_PER_CALL", "4500"))
# maximum API calls for one instrument in one forward update
DEFAULT_MAX_CALLS = int(os.getenv("UPDATE_MAX_CALLS", "10"))
# maximum API calls per instrument for deep history (--days)
DEFAULT_HISTORY_MAX_CALLS = int(os.getenv("UPDATE_HISTORY_MAX_CALLS", "20"))
# bars requested when nothing is stored yet (provider maximum is 5000)
DEFAULT_INITIAL_BARS = int(os.getenv("UPDATE_INITIAL_BARS", "5000"))


def settle_seconds() -> float:
    """Seconds a bar must be closed before it is stored (read at call time)."""
    return float(os.getenv("BAR_SETTLE_SECONDS", "120"))


@dataclass
class InstrumentUpdate:
    symbol: str
    timeframe: str
    before: DataStatus
    after: DataStatus | None = None
    calls: int = 0
    fetched: int = 0
    closed: int = 0
    saved: int = 0
    duplicate: int = 0
    rejected: int = 0
    skipped_bars: int = 0          # older bars not fetched (call limit)
    remaining_gaps: int = 0        # MISSING_DATA gaps left in the newest 1000 bars
    error: str | None = None
    budget_exhausted: bool = False
    history_saved: int = 0
    history_skipped_bars: int = 0
    history_limit_reached: bool = False
    offsession: int = 0            # provider bars outside the trading session


def _chunks(
    start: datetime,
    end: datetime,
    interval: timedelta,
    max_bars: int,
) -> list[tuple[datetime, datetime]]:
    """Split [start, end] (bar open times) into request chunks.

    Closed-market periods (weekend) are skipped, so no API credit is spent
    on requests that could only return nothing. Every chunk lies inside one
    continuous open-market segment and has at most max_bars bars.
    """
    segments: list[tuple[datetime, datetime]] = []
    current = start
    segment_start = None
    previous = None

    while current <= end:
        if is_fx_market_open(current):
            if segment_start is None:
                segment_start = current
            previous = current
        elif segment_start is not None:
            segments.append((segment_start, previous))
            segment_start = None

        current += interval

    if segment_start is not None:
        segments.append((segment_start, previous))

    chunks = []

    for seg_start, seg_end in segments:
        # Cut from the NEWEST end backwards: the newest chunks are full, the
        # remainder (short chunk) is the oldest one. If the call limit cuts
        # the plan, the fetched part is as large as possible.
        segment_chunks = []
        chunk_end = seg_end

        while chunk_end >= seg_start:
            chunk_start = max(seg_start, chunk_end - interval * (max_bars - 1))
            segment_chunks.append((chunk_start, chunk_end))
            chunk_end = chunk_start - interval

        chunks.extend(reversed(segment_chunks))

    return chunks


def bar_in_session(bar_time: datetime, interval: timedelta) -> bool:
    """True when at least one minute of the bar lies in the trading session."""
    return is_fx_market_open(bar_time) or is_fx_market_open(
        bar_time + interval - timedelta(minutes=1)
    )


def _store(
    bars,
    start,
    end,
    timeframe,
    now,
    result: InstrumentUpdate,
    settle: float = 0.0,
) -> None:
    interval = timeframe_delta(timeframe)
    to_save = []

    for bar in bars:
        result.fetched += 1

        if not (start <= bar.bar_time <= end):
            continue

        # off-hours quotes of the provider are not stored (see docstring)
        if not bar_in_session(bar.bar_time, interval):
            result.offsession += 1
            continue

        # closed AND settled (see module docstring)
        if now < bar.bar_time + interval + timedelta(seconds=settle):
            continue

        result.closed += 1

        errors = validate_raw_bar(bar)

        if errors:
            result.rejected += 1
            logger.error(
                "UPDATE REJECTED | symbol=%s | timeframe=%s | "
                "bar_time=%s | errors=%s",
                bar.symbol,
                bar.timeframe,
                bar.bar_time.isoformat(),
                errors,
            )
            continue

        to_save.append(bar)

    # one transaction for the whole batch (a commit per bar is very slow
    # on a phone: thousands of bars arrive in a single response)
    saved, duplicate = save_raw_bars(to_save)
    result.saved += saved
    result.duplicate += duplicate


def _floor_to_grid(moment: datetime, interval: timedelta) -> datetime:
    seconds = int(interval.total_seconds())
    stamp = int(moment.timestamp())
    return datetime.fromtimestamp(stamp - stamp % seconds, tz=timezone.utc)


def _extend_history(
    feed,
    symbol: str,
    timeframe: str,
    days: int,
    now: datetime,
    source: str,
    max_bars_per_call: int,
    max_calls: int,
    settle: float,
    result: InstrumentUpdate,
) -> None:
    """Fetch OLDER bars so that at least `days` days of history are stored.

    Works backwards from the oldest stored bar, newest chunks first (so the
    stored data stays contiguous), skips weekends, and stops when the
    provider has nothing older. What does not fit into the call limit is
    reported, never silently dropped.
    """
    interval = timeframe_delta(timeframe)
    earliest = get_earliest_bar_open(symbol, timeframe, source)

    if earliest is None:
        return

    target = _floor_to_grid(now - timedelta(days=days), interval)

    if earliest <= target:
        return

    plan = _chunks(target, earliest - interval, interval, max_bars_per_call)

    if len(plan) > max_calls:
        skipped = plan[: len(plan) - max_calls]
        plan = plan[len(plan) - max_calls:]
        result.history_skipped_bars = sum(
            int((end - start) / interval) + 1 for start, end in skipped
        )

    for start, end in reversed(plan):
        fetch_end = end + interval if start == end else end

        bars = feed.fetch_bars_range(symbol, timeframe, start, fetch_end)
        result.calls += 1

        if not bars:
            # nothing that far back (provider history limit, or a holiday)
            result.history_limit_reached = True
            break

        before = result.saved
        _store(bars, start, end, timeframe, now, result, settle)
        result.history_saved += result.saved - before


def update_instrument(
    feed,
    symbol: str,
    timeframe: str,
    now: datetime | None = None,
    source: str = DEFAULT_SOURCE,
    max_bars_per_call: int = DEFAULT_MAX_BARS_PER_CALL,
    max_calls: int = DEFAULT_MAX_CALLS,
    initial_bars: int = DEFAULT_INITIAL_BARS,
    history_days: int | None = None,
    history_max_calls: int = DEFAULT_HISTORY_MAX_CALLS,
    settle_seconds_override: float | None = None,
) -> InstrumentUpdate:
    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must contain timezone information")

    if max_bars_per_call < 2:
        raise ValueError("max_bars_per_call must be >= 2")

    if max_calls < 1:
        raise ValueError("max_calls must be >= 1")

    interval = timeframe_delta(timeframe)
    settle = (
        settle_seconds()
        if settle_seconds_override is None
        else settle_seconds_override
    )
    latest = get_latest_bar_open(symbol, timeframe, source)

    # newest bar that is closed AND settled = the bar we can store now
    expected = expected_last_bar_open(
        now - timedelta(seconds=settle), timeframe
    )

    result = InstrumentUpdate(
        symbol=symbol,
        timeframe=timeframe,
        before=classify(symbol, timeframe, latest, now),
    )

    run_id = start_collector_run(symbol, timeframe, now.isoformat())

    try:
        if latest is None:
            bars = feed.fetch_bars(symbol, timeframe, initial_bars)
            result.calls += 1
            # no lower bound: the provider returns the newest available bars,
            # which may reach back over a weekend
            floor_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
            _store(bars, floor_time, expected, timeframe, now, result, settle)

        elif latest < expected:
            first_missing = latest + interval
            plan = _chunks(first_missing, expected, interval, max_bars_per_call)

            if len(plan) > max_calls:
                skipped = plan[: len(plan) - max_calls]
                plan = plan[len(plan) - max_calls:]
                result.skipped_bars = sum(
                    int((end - start) / interval) + 1 for start, end in skipped
                )
                logger.warning(
                    "UPDATE LIMIT | symbol=%s | timeframe=%s | "
                    "older_bars_not_fetched=%d",
                    symbol,
                    timeframe,
                    result.skipped_bars,
                )

            # newest chunks first: data becomes current as early as possible
            for start, end in reversed(plan):
                fetch_end = end

                # The provider requires end > start; a single-bar chunk is
                # requested one interval wider and filtered afterwards.
                if start == end:
                    fetch_end = end + interval

                bars = feed.fetch_bars_range(symbol, timeframe, start, fetch_end)
                result.calls += 1
                _store(bars, start, end, timeframe, now, result, settle)

        if history_days:
            _extend_history(
                feed,
                symbol,
                timeframe,
                history_days,
                now,
                source,
                max_bars_per_call,
                history_max_calls,
                settle,
                result,
            )

    except (RateLimitExceeded, ProviderRateLimited) as exc:
        result.budget_exhausted = True
        result.error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"

    if result.error:
        logger.error(
            "UPDATE FAILED | symbol=%s | timeframe=%s | %s",
            symbol,
            timeframe,
            result.error,
        )

    finish_collector_run(
        run_id,
        datetime.now(timezone.utc).isoformat(),
        "FAILED" if result.error else "SUCCESS",
        bars_saved=result.saved,
        bars_duplicate=result.duplicate,
        bars_fetched=result.fetched,
        bars_closed=result.closed,
        bars_open_skipped=result.fetched - result.closed,
        bars_rejected=result.rejected,
        error_message=result.error,
    )

    result.after = classify(
        symbol,
        timeframe,
        get_latest_bar_open(symbol, timeframe, source),
        now,
    )

    result.remaining_gaps = sum(
        1
        for gap in detect_gaps(symbol, timeframe, source, 1000)
        if gap["status"] == "MISSING_DATA"
    )

    logger.info(
        "UPDATE DONE | symbol=%s | timeframe=%s | before=%s | after=%s | "
        "calls=%d | saved=%d | duplicate=%d | rejected=%d | gaps=%d",
        symbol,
        timeframe,
        result.before.state.value,
        result.after.state.value,
        result.calls,
        result.saved,
        result.duplicate,
        result.rejected,
        result.remaining_gaps,
    )

    return result


def update_all(
    feed,
    instruments: list[tuple[str, str]],
    now: datetime | None = None,
    **kwargs,
) -> list[InstrumentUpdate]:
    results = []

    for symbol, timeframe in instruments:
        results.append(
            update_instrument(
                feed=feed,
                symbol=symbol,
                timeframe=timeframe,
                now=now,
                **kwargs,
            )
        )

    return results


# ----------------------------------------------------------------------
# human readable report (Czech labels, English state codes)
# ----------------------------------------------------------------------

_STATE_HINT = {
    DataState.CURRENT: "aktualni",
    DataState.CLOSED: "trh zavren / posledni platna svicka",
    DataState.STALE: "STARA DATA",
    DataState.MISSING: "ZADNA DATA",
    DataState.UNVERIFIED: "NEOVERENO",
    DataState.CONFLICT: "KONFLIKT ZDROJU",
}


def _age_text(seconds: float | None) -> str:
    if seconds is None:
        return "-"

    seconds = max(0, int(seconds))

    if seconds < 3600:
        return f"{seconds // 60} min"

    if seconds < 86400:
        return f"{seconds // 3600} h {(seconds % 3600) // 60} min"

    return f"{seconds // 86400} d {(seconds % 86400) // 3600} h"


def format_status_line(status: DataStatus) -> str:
    latest = (
        status.latest_bar_open.strftime("%Y-%m-%d %H:%M")
        if status.latest_bar_open
        else "-"
    )

    return (
        f"{status.symbol} {status.timeframe}: {status.state.value} "
        f"({_STATE_HINT[status.state]}) | posledni svicka {latest} UTC "
        f"| stari {_age_text(status.age_seconds)}"
        + (f" | chybi {status.missing_bars}" if status.missing_bars else "")
    )


def format_report(
    results: list[InstrumentUpdate],
    now: datetime,
    budget_status: dict | None = None,
) -> str:
    lines = [
        "=" * 60,
        "FXBOT - AKTUALIZACE DAT",
        "=" * 60,
        f"cas (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if results:
        lines.append(
            "trh: " + ("OTEVREN" if results[0].before.market_open else "ZAVREN")
        )

    if budget_status:
        lines.append(
            f"API kredity dnes: {budget_status['day_used']}/"
            f"{budget_status['day_limit']}"
        )

    lines.append("-" * 60)

    for item in results:
        after = item.after.state.value if item.after else "?"
        line = (
            f"{item.symbol} {item.timeframe}: {item.before.state.value}"
            f" -> {after} | volani {item.calls} | ulozeno {item.saved}"
        )

        if item.rejected:
            line += f" | zamitnuto {item.rejected}"

        if item.offsession:
            line += f" | mimo obchodni dobu preskoceno {item.offsession}"

        if item.remaining_gaps:
            line += f" | MEZERY {item.remaining_gaps}"

        lines.append(line)

        if item.history_saved or item.history_limit_reached or item.history_skipped_bars:
            note = f"  historie: pridano {item.history_saved}"

            if item.history_limit_reached:
                note += " | poskytovatel nema starsi data"

            if item.history_skipped_bars:
                note += f" | nestazeno {item.history_skipped_bars} (limit volani)"

            lines.append(note)

        if item.skipped_bars:
            lines.append(
                f"  NESTAZENO starsich svicek: {item.skipped_bars} "
                f"(prekrocen limit volani)"
            )

        if item.budget_exhausted:
            lines.append("  DENNI LIMIT API VYCERPAN - zkuste znovu zitra (UTC)")
        elif item.error:
            lines.append(f"  CHYBA: {item.error[:150]}")

    problems = [
        r for r in results
        if r.error
        or (r.after and r.after.state in (DataState.STALE, DataState.MISSING,
                                          DataState.UNVERIFIED))
    ]

    lines.append("-" * 60)
    lines.append(
        "VYSLEDEK: " + ("OK" if not problems else f"{len(problems)} problem(u)")
    )
    lines.append("=" * 60)

    return "\n".join(lines)
