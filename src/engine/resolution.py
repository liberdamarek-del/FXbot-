"""Side-correct outcome resolution on the archived path (modules 12, 61-65, 90).

Shared by the live resolver and the backtest (module 74).

Execution sides (module 12, 90):
    BUY   entry (limit) fills when ASK low  <= entry
          TP1 when BID high >= TP1, SL when BID low <= SL
    SELL  entry (limit) fills when BID high >= entry
          TP1 when ASK low  <= TP1, SL when ASK high >= SL
    NOW   filled at the first available quote after T0 (ASK for BUY, BID
          for SELL) plus the assumed slippage
Bars without bid/ask (model-price sources) are resolved on mid and the
result is labelled MODEL-PRICE (module 63).

Sequence (module 61, 90): when one bar contains two decisive levels
(entry + SL/TP, or SL + TP) the finer 1-minute path is consulted if it is
archived; if the order still cannot be proven the result is
SEQUENCE_UNKNOWN. A later close is never used as intrabar evidence.

Coverage (module 62, 123): a missing in-session bar before the decisive
bar makes the result UNRESOLVED (the hole could hide an earlier hit).
A path that does not reach the horizon yet leaves the prediction OPEN.

R multiples: planned risk = |entry - SL| on the model price. The net R
uses the executed side-correct prices and slippage (KNOWN-COST-ADJUSTED).
"""

from dataclasses import dataclass, field
from typing import Callable, Iterable

from src.path_archive import Bar, is_session_minute

FINAL = ("TP1_BEFORE_SL", "SL_BEFORE_TP1", "SEQUENCE_UNKNOWN", "EXPIRED", "NOT_ACTIVATED")


@dataclass
class Plan:
    direction: str          # BUY / SELL
    is_now: bool
    entry: float            # model price; for NOW the reference price
    stop: float
    tp1: float
    t0: int
    horizon_end: int
    slippage: float = 0.0


@dataclass
class Outcome:
    status: str                         # OPEN / CLOSED / UNRESOLVED
    outcome_state: str | None = None
    triggered_at: int | None = None
    resolved_at: int | None = None
    executed_entry: float | None = None
    exit_price: float | None = None
    r_net: float | None = None          # side-correct, after slippage
    r_model: float | None = None        # on model prices (planned levels)
    mfe_r: float | None = None
    mae_r: float | None = None
    time_to_mfe: int | None = None
    coverage: str = "COMPLETE"          # COMPLETE / PARTIAL / GAP
    missing_bars: int = 0
    cost_layer: str = "SIDE-CORRECT"
    granularity: str = "1h"
    notes: list = field(default_factory=list)


def _levels(bar: Bar, direction: str):
    """Side-correct extremes: (fill_extreme, favourable_extreme, adverse_extreme)."""
    if direction == "BUY":
        return bar.al, bar.bh, bar.bl       # entry vs ASK low; TP vs BID high; SL vs BID low
    return bar.bh, bar.al, bar.ah           # entry vs BID high; TP vs ASK low; SL vs ASK high


def resolve(
    plan: Plan,
    bars: list[Bar],
    bar_seconds: int,
    now: int,
    minute_loader: Callable[[int, int], list[Bar]] | None = None,
    side_correct: bool = True,
) -> Outcome:
    sign = 1.0 if plan.direction == "BUY" else -1.0
    risk = sign * (plan.entry - plan.stop)
    out = Outcome(status="OPEN", granularity="1min" if bar_seconds == 60 else f"{bar_seconds // 3600}h")

    if not side_correct:
        out.cost_layer = "MODEL-PRICE"

    if risk <= 0:
        out.status, out.outcome_state = "UNRESOLVED", "UNRESOLVED"
        out.notes.append("neplatna geometrie (SL na spatne strane)")
        return out

    # only bars that OPEN at or after T0 (no hindsight) and before the horizon
    path = [b for b in bars if b.ts >= plan.t0 and b.ts < plan.horizon_end and b.ts + bar_seconds <= now]
    triggered = False
    executed = None
    mfe = mae = 0.0
    mfe_time = None
    expected = plan.t0 - plan.t0 % bar_seconds
    if expected < plan.t0:
        expected += bar_seconds

    def check_missing(until_ts: int) -> int:
        """In-session bars expected before until_ts but not present."""
        nonlocal expected
        missing = 0

        while expected < until_ts:
            if is_session_minute(expected) and expected not in present:
                missing += 1
            expected += bar_seconds

        return missing

    present = {b.ts for b in path}

    if plan.is_now:
        if not path:
            return out
        first = path[0]
        executed = (first.ao if plan.direction == "BUY" else first.bo) + sign * plan.slippage
        triggered = True
        out.triggered_at = first.ts
        out.executed_entry = executed

    for index, bar in enumerate(path):
        out.missing_bars += check_missing(bar.ts)
        expected = bar.ts + bar_seconds
        fill_x, fav_x, adv_x = _levels(bar, plan.direction)
        tp_hit = sign * (fav_x - plan.tp1) >= 0
        sl_hit = sign * (adv_x - plan.stop) <= 0

        if not triggered:
            touched = sign * (fill_x - plan.entry) <= 0

            if not touched:
                if tp_hit:
                    return _finish(out, "NOT_ACTIVATED", bar.ts, None, "TP1 dosazen bez vstupu", plan, risk)
                continue

            triggered = True
            executed = plan.entry
            out.triggered_at = bar.ts
            out.executed_entry = executed

            if sl_hit or tp_hit:
                finer = _finer(plan, bar, bar_seconds, minute_loader, triggered_before=False)

                if finer is not None:
                    return _merge(out, finer, plan, risk, mfe, mae)

                return _finish(out, "SEQUENCE_UNKNOWN", bar.ts, None,
                               "vstup a SL/TP1 ve stejne svicce - poradi neznamo", plan, risk)
            continue

        # triggered: excursions (side-correct)
        favourable = sign * (fav_x - executed) / risk
        adverse = sign * (executed - adv_x) / risk

        if sl_hit and tp_hit:
            finer = _finer(plan, bar, bar_seconds, minute_loader, triggered_before=True, executed=executed)

            if finer is not None:
                return _merge(out, finer, plan, risk, mfe, mae)

            return _finish(out, "SEQUENCE_UNKNOWN", bar.ts, None, "SL a TP1 ve stejne svicce - poradi neznamo",
                           plan, risk)

        if favourable > mfe:
            mfe, mfe_time = favourable, bar.ts
        mae = max(mae, adverse)

        if sl_hit:
            out.mfe_r, out.mae_r, out.time_to_mfe = mfe, max(mae, 1.0), (mfe_time - plan.t0) if mfe_time else None
            exit_price = plan.stop - sign * plan.slippage
            return _finish(out, "SL_BEFORE_TP1", bar.ts, exit_price, "SL dosazen drive nez TP1", plan, risk)

        if tp_hit:
            out.mfe_r, out.mae_r, out.time_to_mfe = max(mfe, sign * (plan.tp1 - executed) / risk), mae, \
                (bar.ts - plan.t0)
            return _finish(out, "TP1_BEFORE_SL", bar.ts, plan.tp1, "TP1 dosazen drive nez SL", plan, risk)

    # no decision inside the stored path
    last_needed = min(plan.horizon_end, now)
    out.missing_bars += check_missing(last_needed - (last_needed % bar_seconds))

    if now >= plan.horizon_end:
        if out.missing_bars:
            out.status, out.outcome_state, out.coverage = "UNRESOLVED", "UNRESOLVED", "PARTIAL"
            out.notes.append(f"chybi {out.missing_bars} svicek v ceste - nelze potvrdit")
            return out

        if triggered:
            last = path[-1]
            exit_price = (last.bc if plan.direction == "BUY" else last.ac)
            out.mfe_r, out.mae_r = mfe, mae
            return _finish(out, "EXPIRED", plan.horizon_end, exit_price, "horizont skoncil, obchod otevreny", plan, risk)

        return _finish(out, "NOT_ACTIVATED", plan.horizon_end, None, "horizont skoncil bez vstupu", plan, risk)

    out.mfe_r, out.mae_r = (mfe, mae) if triggered else (None, None)
    return out


def _finish(out: Outcome, state: str, when: int, exit_price: float | None, note: str, plan: Plan, risk: float) -> Outcome:
    sign = 1.0 if plan.direction == "BUY" else -1.0

    if out.missing_bars and state in FINAL:
        out.status, out.outcome_state, out.coverage = "UNRESOLVED", "UNRESOLVED", "PARTIAL"
        out.resolved_at = when
        out.notes.append(f"{note}; v ceste chybi {out.missing_bars} svicek pred rozhodnutim - nelze potvrdit")
        return out

    out.status, out.outcome_state, out.resolved_at = "CLOSED", state, when
    out.notes.append(note)

    if exit_price is not None and out.executed_entry is not None:
        out.exit_price = exit_price
        out.r_net = sign * (exit_price - out.executed_entry) / risk

    if state == "TP1_BEFORE_SL":
        out.r_model = sign * (plan.tp1 - plan.entry) / risk
    elif state == "SL_BEFORE_TP1":
        out.r_model = -1.0
    elif state == "EXPIRED" and exit_price is not None:
        out.r_model = sign * (exit_price - plan.entry) / risk

    return out


def _finer(plan: Plan, bar: Bar, bar_seconds: int, loader, triggered_before: bool, executed: float | None = None):
    """Re-resolve one ambiguous coarse bar on archived 1-minute bars."""
    if loader is None or bar_seconds == 60:
        return None

    minutes = loader(bar.ts, bar.ts + bar_seconds)
    expected = [ts for ts in range(bar.ts, bar.ts + bar_seconds, 60) if is_session_minute(ts)]

    if not minutes or len(minutes) != len(expected):
        return None           # the fine path is not complete: stays unknown

    sub = Plan(plan.direction, plan.is_now and not triggered_before, plan.entry, plan.stop, plan.tp1,
               bar.ts, bar.ts + bar_seconds, plan.slippage)
    result = resolve_minutes_inside(sub, minutes, triggered_before, executed)
    return result


def resolve_minutes_inside(plan: Plan, minutes: list[Bar], triggered_before: bool, executed: float | None):
    """Decide inside one coarse bar using its complete minutes; None = still unknown."""
    sign = 1.0 if plan.direction == "BUY" else -1.0
    triggered = triggered_before
    fill_ts = None

    for bar in minutes:
        fill_x, fav_x, adv_x = _levels(bar, plan.direction)
        tp_hit = sign * (fav_x - plan.tp1) >= 0
        sl_hit = sign * (adv_x - plan.stop) <= 0

        if not triggered:
            if sign * (fill_x - plan.entry) <= 0:
                triggered, fill_ts = True, bar.ts

                if sl_hit or tp_hit:
                    return None           # same minute: unknown even at 1 minute
                continue

            if tp_hit:
                return ("NOT_ACTIVATED", bar.ts, None, None)
            continue

        if sl_hit and tp_hit:
            return None

        if sl_hit:
            return ("SL_BEFORE_TP1", bar.ts, fill_ts, plan.stop - sign * plan.slippage)

        if tp_hit:
            return ("TP1_BEFORE_SL", bar.ts, fill_ts, plan.tp1)

    return ("CONTINUE", None, fill_ts, None)


def _merge(out: Outcome, finer, plan: Plan, risk: float, mfe: float, mae: float) -> Outcome:
    state, when, fill_ts, exit_price = finer
    sign = 1.0 if plan.direction == "BUY" else -1.0

    if state == "CONTINUE":
        # the 1-minute path decided nothing inside this bar (the two sources
        # disagree slightly): the order stays unknown, nothing is guessed
        out.status, out.outcome_state, out.resolved_at = "CLOSED", "SEQUENCE_UNKNOWN", when
        out.notes.append("nejasna svicka ani na 1 minute nerozhodla - poradi neznamo")
        return out

    if state == "NOT_ACTIVATED":
        out.triggered_at = None
        out.executed_entry = None
        return _finish(out, "NOT_ACTIVATED", when, None, "TP1 bez vstupu (upresneno na 1 min)", plan, risk)

    if fill_ts is not None:
        out.triggered_at = fill_ts

    out.granularity = "1min (upresneno)"

    if state == "SL_BEFORE_TP1":
        out.mfe_r, out.mae_r = mfe, max(mae, 1.0)
        return _finish(out, state, when, exit_price, "SL drive nez TP1 (upresneno na 1 min)", plan, risk)

    out.mfe_r, out.mae_r = max(mfe, sign * (plan.tp1 - (out.executed_entry or plan.entry)) / risk), mae
    return _finish(out, state, when, exit_price, "TP1 drive nez SL (upresneno na 1 min)", plan, risk)
