"""Performance statistics with sample guard (modules 66-73).

Three separate properties are never mixed (module 66, 84):
    forecast accuracy   was the DIRECTION right?
    trade performance   what did the TRADE earn (in R, after costs)?
    decision quality    see src/stats/errors.py (error families)

Sample guard (module 70): n < 20 descriptive only, 20-49 preliminary,
50-99 stronger but careful, 100+ long-run benchmark. Several predictions
from the same shock are not independent (module 71): the effective sample
counts event clusters (same UTC day and same currency exposure).

A 95 % interval is given for the win rate (Wilson) and for the
expectancy (normal approximation on the R values; with clustered samples
it is optimistic - stated in the output).
"""

import math
from dataclasses import dataclass, field

BINARY = ("TP1_BEFORE_SL", "SL_BEFORE_TP1")


def sample_class(n: int) -> str:
    if n < 20:
        return "POUZE POPISNE (n<20)"
    if n < 50:
        return "PREDBEZNE (n 20-49)"
    if n < 100:
        return "SILNEJSI, OPATRNE (n 50-99)"
    return "DLOUHODOBY BENCHMARK (n>=100)"


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n == 0:
        return None

    phat = successes / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def mean_ci(values: list[float], z: float = 1.96) -> tuple[float, float, float] | None:
    if not values:
        return None

    n = len(values)
    mean = sum(values) / n

    if n < 2:
        return mean, mean, mean

    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    half = z * sd / math.sqrt(n)
    return mean, mean - half, mean + half


def direction_correct(trade: dict) -> bool | None:
    """True/False for explicitly directional, resolved predictions (66)."""
    state = trade.get("outcome_state")

    if state == "TP1_BEFORE_SL":
        return True

    if state == "SL_BEFORE_TP1":
        return False

    if state == "NOT_ACTIVATED" and "TP1" in (trade.get("notes") or ""):
        return True           # the target was reached without entry: direction right

    if state == "EXPIRED" and trade.get("r_model") is not None:
        return trade["r_model"] > 0

    return None


def max_drawdown(values: list[float]) -> float:
    peak = equity = 0.0
    worst = 0.0

    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = min(worst, equity - peak)

    return worst


def longest_losing_streak(values: list[float]) -> int:
    best = current = 0

    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0

    return best


@dataclass
class Summary:
    label: str
    predictions: int = 0
    triggered: int = 0
    binary: int = 0
    wins: int = 0
    win_rate: float | None = None
    win_ci: tuple | None = None
    direction_n: int = 0
    direction_accuracy: float | None = None
    direction_ci: tuple | None = None
    r_values: list = field(default_factory=list)
    expectancy: float | None = None
    expectancy_ci: tuple | None = None
    median_r: float | None = None
    profit_factor: float | None = None
    max_drawdown_r: float | None = None
    losing_streak: int = 0
    total_r: float = 0.0
    not_activated: int = 0
    sequence_unknown: int = 0
    unresolved: int = 0
    effective_n: int = 0
    sample: str = ""

    def line(self) -> str:
        wr = f"{self.win_rate * 100:.0f}%" if self.win_rate is not None else "-"
        ex = f"{self.expectancy:+.3f}R" if self.expectancy is not None else "-"
        pf = f"{self.profit_factor:.2f}" if self.profit_factor is not None else "-"
        da = f"{self.direction_accuracy * 100:.0f}%" if self.direction_accuracy is not None else "-"
        return (f"{self.label:<28} n={self.predictions:>4} vstup={self.triggered:>4} "
                f"win={wr:>4} smer={da:>4} E={ex:>8} PF={pf:>5} DD={self.max_drawdown_r or 0:+.1f}R "
                f"[{self.sample}]")


def summarize(trades: list[dict], label: str = "vse") -> Summary:
    """trades: dicts with outcome_state, r_net, r_model, t0, symbol, notes,
    triggered (bool), event_cluster."""
    s = Summary(label)
    s.predictions = len(trades)
    ordered = sorted(trades, key=lambda x: x.get("t0", 0))
    r_values = []

    for trade in ordered:
        state = trade.get("outcome_state")

        if trade.get("triggered"):
            s.triggered += 1

        if state in BINARY:
            s.binary += 1
            s.wins += state == "TP1_BEFORE_SL"

        if state == "NOT_ACTIVATED":
            s.not_activated += 1
        elif state == "SEQUENCE_UNKNOWN":
            s.sequence_unknown += 1
        elif state == "UNRESOLVED":
            s.unresolved += 1

        if state in BINARY + ("EXPIRED",) and trade.get("r_net") is not None:
            r_values.append(float(trade["r_net"]))

    s.r_values = r_values

    if s.binary:
        s.win_rate = s.wins / s.binary
        s.win_ci = wilson(s.wins, s.binary)

    directional = [direction_correct(t) for t in ordered]
    directional = [d for d in directional if d is not None]
    s.direction_n = len(directional)

    if directional:
        s.direction_accuracy = sum(directional) / len(directional)
        s.direction_ci = wilson(sum(directional), len(directional))

    if r_values:
        s.expectancy, low, high = mean_ci(r_values)
        s.expectancy_ci = (low, high)
        ordered_r = sorted(r_values)
        mid = len(ordered_r) // 2
        s.median_r = ordered_r[mid] if len(ordered_r) % 2 else (ordered_r[mid - 1] + ordered_r[mid]) / 2
        gains = sum(r for r in r_values if r > 0)
        losses = -sum(r for r in r_values if r < 0)
        s.profit_factor = gains / losses if losses > 0 else None
        s.max_drawdown_r = max_drawdown(r_values)
        s.losing_streak = longest_losing_streak(r_values)
        s.total_r = sum(r_values)

    clusters = {t.get("event_cluster") for t in ordered if t.get("outcome_state") in BINARY + ("EXPIRED",)}
    s.effective_n = len(clusters - {None})
    s.sample = sample_class(min(len(r_values), s.effective_n or len(r_values)))
    return s


def breakdown(trades: list[dict], key) -> list[Summary]:
    groups: dict[str, list] = {}

    for trade in trades:
        groups.setdefault(str(key(trade)), []).append(trade)

    return [summarize(v, k) for k, v in sorted(groups.items())]


def calibration(trades: list[dict]) -> dict:
    """Does a higher evidence class really perform better? (module 72)"""
    by_class = {s.label: s for s in breakdown(trades, lambda t: t.get("confidence") or "-")}
    a, c = by_class.get("A"), by_class.get("C")
    b = by_class.get("B")
    verdict = "NEDOSTATEK DAT"
    usable = [x for x in (a, b, c) if x and len(x.r_values) >= 20]

    if len(usable) >= 2:
        ordered = sorted(usable, key=lambda x: x.label)
        expectancies = [x.expectancy for x in ordered]
        verdict = "KALIBRACE OK" if expectancies == sorted(expectancies, reverse=True) else "CALIBRATION FAILURE"

    return {"classes": by_class, "verdict": verdict}


def rolling(trades: list[dict], window: int) -> list[float]:
    """Rolling expectancy over the last `window` R values (module 70)."""
    values = [float(t["r_net"]) for t in sorted(trades, key=lambda x: x.get("t0", 0))
              if t.get("outcome_state") in BINARY + ("EXPIRED",) and t.get("r_net") is not None]
    return [sum(values[i - window:i]) / window for i in range(window, len(values) + 1)]
