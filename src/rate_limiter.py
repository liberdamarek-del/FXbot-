"""API credit budget for the market data provider.

Twelve Data counts credits per request (1 credit per symbol per request for
time_series) and limits credits per minute and per day. The free (Basic)
plan allows 8 credits per minute and 800 per day.

The budget is shared between ALL processes on the device (collector service,
history service, manual update scripts) because every call is recorded in
the SQLite table `api_call_log` inside an exclusive transaction. Restarting
the program therefore does not reset the daily counter.

Safety margin: only a fraction (default 90 %) of the plan limits is used, to
absorb clock differences and the fact that the provider's exact day/minute
boundaries are NEOVERENO.

Configuration (environment or .env):
    TWELVE_DATA_CREDITS_PER_MINUTE   default 8    (plan limit)
    TWELVE_DATA_CREDITS_PER_DAY      default 800  (plan limit)
    API_BUDGET_SAFETY                default 0.9  (fraction of the limit used)
"""

import math
import os
import time
from datetime import datetime, timezone
from typing import Callable

from src.database import get_connection

PROVIDER_TWELVE_DATA = "twelvedata"

# Never sleep longer than this for the per-minute window in one step.
MAX_SINGLE_WAIT_SECONDS = 65.0


class RateLimitExceeded(RuntimeError):
    """The local credit budget does not allow the request."""


class ProviderRateLimited(RuntimeError):
    """The provider itself answered with a rate limit error (HTTP/JSON 429)."""


def _ensure_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_call_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            called_at REAL NOT NULL,
            credits INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_api_call_log_lookup
        ON api_call_log(provider, called_at)
        """
    )


class CreditBudget:
    def __init__(
        self,
        per_minute: int,
        per_day: int,
        provider: str = PROVIDER_TWELVE_DATA,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if per_minute < 1:
            raise ValueError("per_minute must be >= 1")

        if per_day < 1:
            raise ValueError("per_day must be >= 1")

        self.per_minute = per_minute
        self.per_day = per_day
        self.provider = provider
        self._clock = clock
        self._sleep = sleep

    @classmethod
    def from_env(cls, **kwargs) -> "CreditBudget":
        plan_minute = int(os.getenv("TWELVE_DATA_CREDITS_PER_MINUTE", "8"))
        plan_day = int(os.getenv("TWELVE_DATA_CREDITS_PER_DAY", "800"))
        safety = float(os.getenv("API_BUDGET_SAFETY", "0.9"))

        if not 0.1 <= safety <= 1.0:
            raise ValueError("API_BUDGET_SAFETY must be between 0.1 and 1.0")

        return cls(
            per_minute=max(1, math.floor(plan_minute * safety)),
            per_day=max(1, math.floor(plan_day * safety)),
            **kwargs,
        )

    # ------------------------------------------------------------------

    def _day_start(self, now: float) -> float:
        moment = datetime.fromtimestamp(now, tz=timezone.utc)
        midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def _usage(self, connection, now: float) -> tuple[int, int, float | None]:
        """(credits in last 60 s, credits today UTC, oldest call in window)."""
        window_start = now - 60.0

        minute_used, oldest = connection.execute(
            """
            SELECT COALESCE(SUM(credits), 0), MIN(called_at)
            FROM api_call_log
            WHERE provider = ? AND called_at > ?
            """,
            (self.provider, window_start),
        ).fetchone()

        day_used = connection.execute(
            """
            SELECT COALESCE(SUM(credits), 0)
            FROM api_call_log
            WHERE provider = ? AND called_at >= ?
            """,
            (self.provider, self._day_start(now)),
        ).fetchone()[0]

        return int(minute_used), int(day_used), oldest

    def status(self) -> dict:
        now = self._clock()

        with get_connection() as connection:
            _ensure_table(connection)
            minute_used, day_used, _ = self._usage(connection, now)

        return {
            "provider": self.provider,
            "minute_used": minute_used,
            "minute_limit": self.per_minute,
            "day_used": day_used,
            "day_limit": self.per_day,
            "day_remaining": max(0, self.per_day - day_used),
        }

    def acquire(self, credits: int = 1) -> None:
        """Reserve credits for one request; wait for the minute window.

        Raises RateLimitExceeded when the DAILY budget is used up (waiting
        would not help) or when the request alone exceeds a limit.
        """
        if credits < 1:
            raise ValueError("credits must be >= 1")

        if credits > self.per_minute:
            raise RateLimitExceeded(
                f"request needs {credits} credits, per-minute budget is "
                f"{self.per_minute}"
            )

        while True:
            now = self._clock()
            wait_seconds = 0.0

            with get_connection() as connection:
                _ensure_table(connection)
                connection.execute("BEGIN IMMEDIATE")

                try:
                    minute_used, day_used, oldest = self._usage(
                        connection, now
                    )

                    if day_used + credits > self.per_day:
                        connection.execute("ROLLBACK")
                        raise RateLimitExceeded(
                            f"daily API budget used up "
                            f"({day_used}/{self.per_day} credits, UTC day)"
                        )

                    if minute_used + credits <= self.per_minute:
                        connection.execute(
                            """
                            INSERT INTO api_call_log (provider, called_at, credits)
                            VALUES (?, ?, ?)
                            """,
                            (self.provider, now, credits),
                        )
                        connection.execute("COMMIT")
                        return

                    connection.execute("ROLLBACK")
                    wait_seconds = (oldest + 60.0) - now + 0.05

                except RateLimitExceeded:
                    raise
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise

            self._sleep(min(max(wait_seconds, 0.05), MAX_SINGLE_WAIT_SECONDS))

    def prune(self, keep_days: int = 3) -> int:
        """Delete log rows older than keep_days (housekeeping only)."""
        cutoff = self._clock() - keep_days * 86400

        with get_connection() as connection:
            _ensure_table(connection)
            cursor = connection.execute(
                "DELETE FROM api_call_log WHERE called_at < ?", (cutoff,)
            )
            connection.commit()
            return cursor.rowcount
