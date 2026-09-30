"""Due-outcome audit of locked predictions (modules 61, 62, 65, 69, 81).

Every run first resolves all open predictions of the ledger on the
archived 1-minute path (src/engine/resolution.py), before any new
prediction is made. Results are appended (never overwritten):

- the cost layer is SIDE-CORRECT when every minute of the path came with
  BID/ASK (Dukascopy), otherwise MODEL-PRICE (Twelve Data mid minutes),
- a path hole before the decisive minute keeps the prediction UNRESOLVED
  until the data is repaired (then it resolves on a later run),
- the error family and root cause are derived from the path (module 69).
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.engine.resolution import FINAL, Plan, resolve
from src.path_archive import aggregate
from src.instruments import get_instrument
from src.prediction_ledger import add_state, list_predictions, record_outcome
from src.stats.errors import classify
from src.v78.coverage import path_minutes

UTC = timezone.utc
STATE_FOR_OUTCOME = {
    "TP1_BEFORE_SL": "RESOLVED",
    "SL_BEFORE_TP1": "RESOLVED",
    "SEQUENCE_UNKNOWN": "RESOLVED",
    "EXPIRED": "EXPIRED",
    "NOT_ACTIVATED": "NOT_ACTIVATED",
}


def parse_horizon(text: str | None) -> timedelta:
    match = re.fullmatch(r"\s*(\d+)\s*([hd])\s*", text or "", re.IGNORECASE)

    if not match:
        return timedelta(hours=24)

    amount = int(match.group(1))
    return timedelta(hours=amount) if match.group(2).lower() == "h" else timedelta(days=amount)


@dataclass
class AuditItem:
    prediction_id: str
    symbol: str
    decision: str
    status: str
    outcome_state: str | None
    r_net: float | None
    cost_layer: str
    actions: list
    notes: str
    triggered_at: int | None = None
    resolved_at: int | None = None


def _resolve_locked(p: dict, direction: str, entry: float, stop: float, tp1: float, now: datetime,
                    slippage_pips: float):
    """Resolve one locked plan on the archived path (shared by the audit of
    the prediction and by its anti-model control)."""
    instrument = get_instrument(p["instrument"])
    t0 = datetime.fromisoformat(p["t0"]).astimezone(UTC)
    horizon_end = t0 + parse_horizon(p["primary_horizon"])
    t0_ts, end_ts = int(t0.timestamp()), int(horizon_end.timestamp())
    # the minute that opens at/after T0 is the first usable one
    first_minute = t0_ts - t0_ts % 60 + (60 if t0_ts % 60 else 0)
    bars, sources = path_minutes(p["instrument"], first_minute, min(int(now.timestamp()), end_ts))
    entry_mode = locked_inputs(p).get("entry_mode", "limit")
    plan = Plan(direction, p["decision"].endswith("NOW"), entry, stop, tp1, first_minute, end_ts,
                slippage_pips * instrument.pip, entry_mode)
    side_correct = all(sources.get(b.ts) != "TWELVE_DATA" for b in bars)

    if entry_mode == "confirm" and not plan.is_now:
        # the locked trigger is an H1 CLOSE: resolve on complete hours, refine
        # ambiguous hours with the stored minutes
        hours = aggregate(bars, "1h")
        by_ts = {b.ts: b for b in bars}
        loader = lambda a, b: [by_ts[t] for t in range(a, b, 60) if t in by_ts]
        plan.t0 = first_minute - first_minute % 3600 + (3600 if first_minute % 3600 else 0)
        return resolve(plan, hours, 3600, int(now.timestamp()), loader, side_correct)

    return resolve(plan, bars, 60, int(now.timestamp()), None, side_correct)


def locked_inputs(p: dict) -> dict:
    try:
        return json.loads(p.get("inputs") or "{}")
    except ValueError:
        return {}


def mirrored_plan(p: dict) -> tuple[str, float, float, float]:
    """Anti-model control of a locked prediction (module 74): the same entry
    offset, risk and reward measured from the same analysis price, in the
    opposite direction - fixed at T0, nothing is taken from the path. Same
    construction as the backtest control (src/engine/backtest.py _plan)."""
    price = float(locked_inputs(p).get("analysis_price") or p["reference_price"])
    entry, stop, tp1 = float(p["entry"]), float(p["stop_loss"]), float(p["tp1"])
    s0 = 1.0 if p["direction"] == "BUY" else -1.0
    offset, risk, reward = s0 * (price - entry), s0 * (entry - stop), s0 * (tp1 - entry)
    s1 = -s0
    anti_entry = price - s1 * offset
    return ("SELL" if s0 > 0 else "BUY"), anti_entry, anti_entry - s1 * risk, anti_entry + s1 * reward


def control_outcome(p: dict, now: datetime, slippage_pips: float = 0.2):
    """Outcome of the mirrored plan on the very same path. Computed on demand
    for the review; never written to the ledger (it is not a prediction)."""
    direction, entry, stop, tp1 = mirrored_plan(p)
    return _resolve_locked(p, direction, entry, stop, tp1, now, slippage_pips)


def audit_prediction(p: dict, now: datetime, slippage_pips: float = 0.2) -> AuditItem:
    symbol = p["instrument"]
    t0 = datetime.fromisoformat(p["t0"]).astimezone(UTC)
    outcome = _resolve_locked(p, p["direction"], float(p["entry"]), float(p["stop_loss"]), float(p["tp1"]), now,
                              slippage_pips)
    actions = []
    states = {s["state"] for s in p["states"]}
    pid = p["prediction_id"]

    if p["decision"].startswith("WAIT") and "WAITING" not in states:
        add_state(pid, "WAITING", "cekani na vstup", changed_at=t0)
        actions.append("WAITING")

    if outcome.triggered_at and "TRIGGERED" not in states:
        add_state(pid, "TRIGGERED", "vstup aktivovan",
                  changed_at=datetime.fromtimestamp(outcome.triggered_at, tz=UTC))
        actions.append("TRIGGERED")

    if outcome.outcome_state:
        recorded = [o["outcome_state"] for o in p["outcomes"]]
        last = recorded[-1] if recorded else None
        new_information = last is None or (last == "UNRESOLVED" and outcome.outcome_state != "UNRESOLVED")

        if new_information:
            record = {
                "outcome_state": outcome.outcome_state, "r_net": outcome.r_net, "mfe_r": outcome.mfe_r,
                "mae_r": outcome.mae_r, "notes": "; ".join(outcome.notes), "setup_type": p.get("setup_type"),
            }
            error = classify(record)
            record_outcome(
                pid,
                outcome.outcome_state,
                path_coverage=f"{outcome.coverage} ({outcome.granularity}, {outcome.cost_layer})",
                r_multiple=None if outcome.r_net is None else round(outcome.r_net, 4),
                mfe=None if outcome.mfe_r is None else round(outcome.mfe_r, 4),
                mae=None if outcome.mae_r is None else round(outcome.mae_r, 4),
                error_family=error["family"] if error else None,
                root_cause=error["root_cause"] if error else None,
                notes="; ".join(outcome.notes) + (f" | protifaktual: {error['counterfactual']}" if error else ""),
                recorded_at=now,
            )
            actions.append(f"vysledek {outcome.outcome_state}")
            final_state = STATE_FOR_OUTCOME.get(outcome.outcome_state)

            if final_state and final_state not in states:
                when = datetime.fromtimestamp(outcome.resolved_at, tz=UTC) if outcome.resolved_at else now
                add_state(pid, final_state, "; ".join(outcome.notes)[:200], changed_at=when)
                actions.append(final_state)

    return AuditItem(pid, symbol, p["decision"], outcome.status, outcome.outcome_state, outcome.r_net,
                     outcome.cost_layer, actions, "; ".join(outcome.notes), outcome.triggered_at, outcome.resolved_at)


def audit_all(now: datetime, limit: int = 2000) -> list[AuditItem]:
    """Resolve every locked prediction that has no final outcome yet."""
    items = []

    for p in reversed(list_predictions(limit=limit)):
        if p["direction"] == "NONE" or not p.get("entry") or not p.get("stop_loss") or not p.get("tp1"):
            continue

        if any(o["outcome_state"] in FINAL for o in p["outcomes"]):
            continue

        items.append(audit_prediction(p, now))

    return items
