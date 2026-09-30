"""Economic calendar snapshots (modules 47, 48, 91).

Source: the public weekly calendar feed (nfs.faireconomy.media, same data
as ForexFactory), current week only, with title, currency, scheduled time
(with UTC offset), impact class, forecast and previous value. It does NOT
contain the actual released value.

Every download is archived (hash) and merged into calendar_events; a
changed time or forecast is appended to calendar_changes. Because the feed
only shows the current week, calendar history exists only from the day the
project started collecting it - backtests before that date run WITHOUT the
event layer and say so (module 74: the benchmark gets the same limitation).

Event windows used by the decision layer (module 91):
    PRE-EVENT       scheduled time within the next `pre` hours
    IMMEDIATE-POST  released within the last `post` minutes
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.fundamental.store import (
    get_fund_connection,
    initialize_fundamentals,
    log_fetch,
    store_payload,
)
from src.sources.http import FetchError, fetch

UTC = timezone.utc
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
SOURCE_ID = "FF_CALENDAR"
IMPACT_ORDER = {"Holiday": 0, "Low": 1, "Medium": 2, "High": 3}


@dataclass(frozen=True)
class Event:
    event_id: str
    currency: str
    title: str
    scheduled_at: int
    impact: str
    forecast: str | None
    previous: str | None

    @property
    def time(self) -> datetime:
        return datetime.fromtimestamp(self.scheduled_at, tz=UTC)


def event_id(currency: str, title: str, scheduled: datetime) -> str:
    key = f"{currency}|{title.strip().lower()}|{scheduled.astimezone(UTC):%Y-%m-%d}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def parse_feed(content: bytes) -> list[Event]:
    events = []

    for item in json.loads(content):
        try:
            scheduled = datetime.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue

        if scheduled.tzinfo is None:
            continue           # time zone unknown -> TIMEZONE-UNRESOLVED, not used (module 109)

        currency = str(item.get("country", "")).upper()
        title = str(item.get("title", "")).strip()
        events.append(
            Event(
                event_id=event_id(currency, title, scheduled),
                currency=currency,
                title=title,
                scheduled_at=int(scheduled.astimezone(UTC).timestamp()),
                impact=str(item.get("impact", "")),
                forecast=(item.get("forecast") or None),
                previous=(item.get("previous") or None),
            )
        )

    return events


def store_events(events: list[Event], payload_id: int | None, seen: datetime) -> dict:
    initialize_fundamentals()
    seen_ts = int(seen.timestamp())
    counts = {"new": 0, "changed": 0, "unchanged": 0}

    with get_fund_connection() as connection:
        for event in events:
            row = connection.execute(
                "SELECT scheduled_at, impact, forecast, previous FROM calendar_events WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()

            if row is None:
                connection.execute(
                    "INSERT INTO calendar_events (event_id, currency, title, scheduled_at, impact, forecast, "
                    "previous, actual, source_id, first_seen_at, last_seen_at, payload_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)",
                    (event.event_id, event.currency, event.title, event.scheduled_at, event.impact,
                     event.forecast, event.previous, SOURCE_ID, seen_ts, seen_ts, payload_id),
                )
                counts["new"] += 1
                continue

            changed = False

            for field, old, new in (
                ("scheduled_at", row["scheduled_at"], event.scheduled_at),
                ("impact", row["impact"], event.impact),
                ("forecast", row["forecast"], event.forecast),
                ("previous", row["previous"], event.previous),
            ):
                if old != new:
                    changed = True
                    connection.execute(
                        "INSERT INTO calendar_changes (event_id, field, old_value, new_value, seen_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (event.event_id, field, None if old is None else str(old),
                         None if new is None else str(new), seen_ts),
                    )

            # the event row carries the latest known schedule; the history
            # of every change stays in calendar_changes
            connection.execute(
                "UPDATE calendar_events SET scheduled_at = ?, impact = ?, forecast = ?, previous = ?, "
                "last_seen_at = ? WHERE event_id = ?",
                (event.scheduled_at, event.impact, event.forecast, event.previous, seen_ts, event.event_id),
            )
            counts["changed" if changed else "unchanged"] += 1

        connection.commit()

    return counts


def update_calendar(now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)

    try:
        status, content, _ = fetch(FEED_URL)
    except FetchError as exc:
        log_fetch(SOURCE_ID, FEED_URL, "FAILED", None, None, str(exc))
        return {"ok": False, "detail": str(exc)}

    stored = store_payload(
        source_id=SOURCE_ID, kind="CALENDAR", endpoint=FEED_URL, instrument=None, side=None,
        period_start=None, period_end=None, http_status=status, content=content,
        parser_version="ff-1",
    )
    log_fetch(SOURCE_ID, FEED_URL, "OK", None, status, f"{len(content)} B")

    try:
        events = parse_feed(content)
    except ValueError as exc:
        return {"ok": False, "detail": f"parse error: {exc}"}

    counts = store_events(events, stored.payload_id, now)
    return {"ok": True, "events": len(events), **counts}


def events_between(
    start_ts: int,
    end_ts: int,
    currencies: tuple[str, ...] | list[str] | None = None,
    min_impact: str = "High",
    known_at: int | None = None,
) -> list[Event]:
    """Events scheduled in [start_ts, end_ts]. With known_at, only events
    that had already been seen in the calendar at that moment (no
    hindsight in backtests)."""
    initialize_fundamentals()
    query = "SELECT * FROM calendar_events WHERE scheduled_at >= ? AND scheduled_at <= ?"
    params: list = [start_ts, end_ts]

    if known_at is not None:
        query += " AND first_seen_at <= ?"
        params.append(known_at)

    with get_fund_connection() as connection:
        rows = connection.execute(query + " ORDER BY scheduled_at", params).fetchall()

    threshold = IMPACT_ORDER.get(min_impact, 3)
    out = []

    for row in rows:
        if IMPACT_ORDER.get(row["impact"], 0) < threshold:
            continue

        if currencies and row["currency"] not in currencies:
            continue

        out.append(Event(row["event_id"], row["currency"], row["title"], row["scheduled_at"],
                         row["impact"], row["forecast"], row["previous"]))

    return out


def calendar_coverage() -> tuple[int | None, int | None]:
    """(first_seen, last_seen) of the stored calendar: the period for which
    the event layer is available."""
    initialize_fundamentals()

    with get_fund_connection() as connection:
        row = connection.execute(
            "SELECT MIN(first_seen_at) AS a, MAX(last_seen_at) AS b FROM calendar_events"
        ).fetchone()

    return (row["a"], row["b"]) if row else (None, None)


def event_window(
    currencies: tuple[str, ...],
    t: int,
    pre_hours: float = 6.0,
    post_minutes: float = 90.0,
    known_at: int | None = None,
) -> dict:
    """High-impact events around t for the given currencies (module 47/91)."""
    upcoming = events_between(t, t + int(pre_hours * 3600), currencies, "High", known_at)
    recent = events_between(t - int(post_minutes * 60), t - 1, currencies, "High", known_at)
    return {"pre": upcoming, "post": recent}
