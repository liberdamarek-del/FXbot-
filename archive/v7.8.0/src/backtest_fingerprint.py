import hashlib

from src.historical_data import HistoricalBar


def fingerprint_bars(
    bars: list[HistoricalBar],
) -> str:
    hasher = hashlib.sha256()

    for bar in bars:
        payload = "|".join(
            (
                bar.symbol,
                bar.timeframe,
                bar.bar_time.isoformat(),
                str(bar.open),
                str(bar.high),
                str(bar.low),
                str(bar.close),
                bar.source,
            )
        )

        hasher.update(payload.encode("utf-8"))
        hasher.update(b"\n")

    return hasher.hexdigest()
