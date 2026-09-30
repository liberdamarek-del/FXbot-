"""Full-model replay backtest (modules 74, 77, 142).

Walks through history decision by decision with exactly the code of the
live run (src/engine/pipeline.py), on the archived BID/ASK path:

- at every decision time t (default: each H4 close) only bars CLOSED at t
  and fundamental values PUBLIC at t are visible,
- the thesis book knows an outcome only from the moment it happened
  (resolved bar close <= t), so the no-instant-flip logic cannot peek,
- outcomes are resolved side-correct with costs (src/engine/resolution.py);
  ambiguous hourly bars are refined with archived 1-minute data when it
  exists, otherwise they stay SEQUENCE_UNKNOWN (never guessed),
- the economic calendar has no history before collection started, so the
  event layer is ABLATED in backtests and every report says so,
- a PLACEBO run uses the same decision times and the same trade geometry
  with a random (seeded) direction (module 74: path-consistent control).
"""

import bisect
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.engine.data import PairSeries, load_pair, minute_loader
from src.engine.decision import Candidate
from src.engine.params import ModelParams
from src.engine.pipeline import analyze_pair
from src.engine.resolution import Outcome, Plan, resolve
from src.engine.thesis import MemoryThesisStore, ThesisBook
from src.instruments import get_instrument

UTC = timezone.utc
H = 3600
SIGNAL_HORIZONS = (24, 72, 120)      # pure direction study (module 66), independent of SL/TP


@dataclass
class BacktestConfig:
    symbols: list
    start_ts: int
    end_ts: int
    params: ModelParams
    cadence: str = "4h"                 # decisions at each H4 close
    use_fundamentals: bool = True
    event_mode: str = "ABLATED"
    placebo_seed: int | None = 7
    label: str = "V7.8.0-impl"


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list = field(default_factory=list)
    placebo: list = field(default_factory=list)
    anti: list = field(default_factory=list)          # opposite direction, same geometry
    decisions: int = 0
    no_trade_reasons: dict = field(default_factory=dict)
    blocked_flips: int = 0
    kept: int = 0
    gate_failures: dict = field(default_factory=dict)
    per_symbol_decisions: dict = field(default_factory=dict)


def event_cluster(symbol: str, direction: str, t: int) -> str:
    """Predictions of the same day that share the USD (or JPY) leg in the
    same direction are one situation (module 71)."""
    instrument = get_instrument(symbol)
    day = datetime.fromtimestamp(t, tz=UTC).strftime("%Y-%m-%d")
    anchor = "USD" if "USD" in (instrument.base, instrument.quote) else (
        "JPY" if "JPY" in (instrument.base, instrument.quote) else instrument.base)
    sign = 1 if direction == "BUY" else -1
    sign = sign if instrument.base == anchor else -sign
    return f"{day}:{'+' if sign > 0 else '-'}{anchor}"


def _plan(candidate: Candidate, t: int, p: ModelParams, direction: str | None = None) -> Plan:
    """Plan of the candidate; with another direction the PLACEBO plan: the
    same distances (entry offset from the price, risk, reward) applied from
    the same price in the other direction (pre-specified, no future data)."""
    instrument = get_instrument(candidate.symbol)
    direction = direction or candidate.direction
    entry, stop, tp1 = candidate.entry, candidate.stop, candidate.targets[0]

    if direction != candidate.direction:
        s0 = 1.0 if candidate.direction == "BUY" else -1.0
        offset = s0 * (candidate.price - entry)          # pullback depth (>= 0)
        risk = s0 * (entry - stop)
        reward = s0 * (tp1 - entry)
        s1 = -s0
        entry = candidate.price - s1 * offset
        stop = entry - s1 * risk
        tp1 = entry + s1 * reward

    return Plan(direction, candidate.is_now, entry, stop, tp1, t, t + p.horizon_hours * H,
                p.slippage_pips * instrument.pip, p.entry_mode)


def forward_move_atr(series: PairSeries, t: int, direction: str, hours: int) -> float | None:
    """Mid-price move from t to t + horizon in the given direction, in
    ATR(H1) at t (the plain directional forecast, module 66)."""
    i0 = series.h1.index_at(t)
    i1 = series.h1.index_at(t + hours * H)

    if i0 < 0 or i1 <= i0 or not series.h1.atr14[i0]:
        return None

    sign = 1.0 if direction == "BUY" else -1.0
    return sign * (series.h1.close[i1] - series.h1.close[i0]) / series.h1.atr14[i0]


def _record(candidate: Candidate, outcome: Outcome, t: int, direction: str, known_at: int | None) -> dict:
    return {
        "symbol": candidate.symbol,
        "t0": t,
        "decision": candidate.decision if direction == candidate.direction else candidate.decision.replace(
            candidate.direction, direction),
        "direction": direction,
        "setup_type": candidate.setup_type,
        "confidence": candidate.confidence,
        "regime": candidate.regime,
        "entry": candidate.entry,
        "stop": candidate.stop,
        "tp1": candidate.targets[0],
        "rr_net_planned": candidate.rr_net,
        "clusters_for": ",".join(candidate.clusters_for),
        "outcome_state": outcome.outcome_state or outcome.status,
        "triggered": outcome.triggered_at is not None,
        "triggered_at": outcome.triggered_at,
        "resolved_at": outcome.resolved_at,
        "known_at": known_at,
        "r_net": outcome.r_net,
        "r_model": outcome.r_model,
        "mfe_r": outcome.mfe_r,
        "mae_r": outcome.mae_r,
        "granularity": outcome.granularity,
        "coverage": outcome.coverage,
        "notes": "; ".join(outcome.notes),
        "event_cluster": event_cluster(candidate.symbol, direction, t),
    }


def _resolve(series: PairSeries, plan: Plan, h1_ts: list[int]) -> tuple[Outcome, int | None]:
    lo = bisect.bisect_left(h1_ts, plan.t0)
    hi = bisect.bisect_left(h1_ts, plan.horizon_end)
    bars = series.h1_bars[lo:hi]
    outcome = resolve(plan, bars, H, plan.horizon_end + H, minute_loader(series.symbol))
    known_at = None

    if outcome.status in ("CLOSED", "UNRESOLVED") and outcome.resolved_at is not None:
        known_at = outcome.resolved_at + (H if outcome.resolved_at < plan.horizon_end else 0)

    return outcome, known_at


def decision_times(series: PairSeries, start_ts: int, end_ts: int, cadence: str) -> list[int]:
    source = series.h4 if cadence == "4h" else series.h1
    step = 4 * H if cadence == "4h" else H
    return [ts + step for ts in source.ts if start_ts <= ts + step <= end_ts]


def run_symbol(series: PairSeries, config: BacktestConfig, result: BacktestResult) -> None:
    p = config.params
    book = ThesisBook(MemoryThesisStore())
    rng = random.Random(f"{config.placebo_seed}-{series.symbol}") if config.placebo_seed is not None else None
    h1_ts = [b.ts for b in series.h1_bars]
    open_trade: dict | None = None
    decisions = 0

    for t in decision_times(series, config.start_ts, config.end_ts, config.cadence):
        # 1. what happened to the open thesis - only what is known at t
        if open_trade is not None:
            thesis = book.store.get(series.symbol)
            if thesis and thesis.open:
                if open_trade["triggered_at"] is not None and open_trade["triggered_at"] + H <= t:
                    book.update_from_path(series.symbol, t, None, open_trade["triggered_at"])
                known = open_trade["known_at"]
                if known is not None and known <= t:
                    book.update_from_path(series.symbol, known, open_trade["outcome_state"], open_trade["triggered_at"])
                elif t >= thesis.expires_at:
                    book.update_from_path(series.symbol, t, None, None)

        # 2. data state at t: the last H1 bar must have closed at t
        i1 = series.h1.index_at(t)

        if i1 < 0:
            continue

        state = "CURRENT" if series.h1.close_time(i1) >= t - H else "STALE"
        spread = series.h1.spread(i1) if series.h1.side_correct[i1] else None
        analysis = analyze_pair(series, t, p, state, spread, config.event_mode,
                                use_fundamentals=config.use_fundamentals)
        candidate = analysis.candidate
        decisions += 1

        if not candidate.actionable:
            reason = candidate.reasons[0].split(" (")[0].split(" - ")[0][:60] if candidate.reasons else "?"
            result.no_trade_reasons[reason] = result.no_trade_reasons.get(reason, 0) + 1
            book.check(candidate, t, analysis.regime.transition)
            continue

        for gate in candidate.failed_gates():
            result.gate_failures[gate.name] = result.gate_failures.get(gate.name, 0) + 1

        flip = book.check(candidate, t, analysis.regime.transition)

        if not flip.allowed:
            if flip.action == "BLOCKED_FLIP":
                result.blocked_flips += 1
            else:
                result.kept += 1
            continue

        plan = _plan(candidate, t, p)
        outcome, known_at = _resolve(series, plan, h1_ts)
        record = _record(candidate, outcome, t, candidate.direction, known_at)
        record["fwd_move_atr"] = forward_move_atr(series, t, candidate.direction, p.horizon_hours)
        for hours in SIGNAL_HORIZONS:
            record[f"fwd_{hours}h"] = forward_move_atr(series, t, candidate.direction, hours)
        result.trades.append(record)
        book.open_thesis(candidate, f"BT-{series.symbol}-{t}", t, p.horizon_hours)
        open_trade = record

        # ANTI-MODEL: the same decision and geometry in the opposite direction.
        # A random-direction control is exactly the 50/50 mix of model and
        # anti-model, so its expectation needs no random seed (module 74).
        anti_direction = "SELL" if candidate.direction == "BUY" else "BUY"
        anti_outcome, anti_known = _resolve(series, _plan(candidate, t, p, anti_direction), h1_ts)
        anti_record = _record(candidate, anti_outcome, t, anti_direction, anti_known)
        anti_record["fwd_move_atr"] = forward_move_atr(series, t, anti_direction, p.horizon_hours)
        result.anti.append(anti_record)

        if rng is not None:
            # seeded random direction, kept for a concrete placebo trade list
            result.placebo.append(record if rng.choice(("BUY", "SELL")) == candidate.direction else anti_record)

    result.decisions += decisions
    result.per_symbol_decisions[series.symbol] = decisions


def run(config: BacktestConfig, preloaded: dict | None = None, progress=None) -> BacktestResult:
    result = BacktestResult(config)

    for symbol in config.symbols:
        series = (preloaded or {}).get(symbol) or load_pair(symbol, config.params)

        if len(series.h1) < 500:
            if progress:
                progress(f"{symbol}: malo historie ({len(series.h1)} H1 svicek) - preskoceno")
            continue

        run_symbol(series, config, result)

        if progress:
            progress(f"{symbol}: {result.per_symbol_decisions.get(symbol, 0)} rozhodnuti, "
                     f"obchodu celkem {len(result.trades)}")

    return result
