from datetime import datetime, timezone


def is_closed_bar(
    bar_time: datetime,
    timeframe: str = "1min",
    now: datetime | None = None,
) -> bool:
    if bar_time.tzinfo is None:
        raise ValueError("bar_time must contain timezone information")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must contain timezone information")

    if timeframe.endswith("min"):
        minutes = int(timeframe[:-3])
        interval_seconds = minutes * 60
    elif timeframe.endswith("h"):
        hours = int(timeframe[:-1])
        interval_seconds = hours * 3600
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    bar_open_ts = bar_time.timestamp()
    now_ts = now.timestamp()

    return now_ts >= bar_open_ts + interval_seconds
