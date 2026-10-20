"""Outcome resolver for locked predictions (specification modules 61, 62, 65, 90).

For every locked prediction it replays the stored 1-minute bars that came
AFTER the lock time and decides, without guessing:

- WAIT decisions: was the entry touched? (NOT_ACTIVATED if the target was
  reached first or the horizon ended without entry),
- NOW decisions: entry at the reference price at T0,
- then SL or TP1 first -> TP1_BEFORE_SL / SL_BEFORE_TP1,
- SL and TP1 inside the same 1-minute bar (or entry and exit inside the same
  bar) -> SEQUENCE_UNKNOWN. The order is NEVER guessed,
- horizon over and neither hit -> EXPIRED (if triggered) or NOT_ACTIVATED,
- missing minutes in the path before the decisive bar -> UNRESOLVED
  (a hole could hide an earlier hit); a later repair lets it resolve,
- data not yet downloaded up to the horizon -> still open, nothing recorded.

No hindsight: only bars that open at or after T0 (rounded up to the minute)
are used. Results are appended to the ledger (states and outcomes are
append-only); re-running never duplicates a record.

Assumptions (NEOVERENO, provisional): mid prices without spread or slippage;
entry of a NOW decision at the reference price although the data lag about
two to three minutes; a limit order at the entry price for WAIT decisions.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.database import get_connection
from src.market_session import is_fx_market_open
from src.prediction_ledger import add_state, list_predictions, record_outcome

FINAL_OUTCOMES = (
    "TP1_BEFORE_SL",
    "SL_BEFORE_TP1",
    "SEQUENCE_UNKNOWN",
    "EXPIRED",
    "NOT_ACTIVATED",
)

STATE_FOR_OUTCOME = {
    "TP1_BEFORE_SL": "RESOLVED",
    "SL_BEFORE_TP1": "RESOLVED",
    "SEQUENCE_UNKNOWN": "RESOLVED",
    "EXPIRED": "EXPIRED",
    "NOT_ACTIVATED": "NOT_ACTIVATED",
}

DEFAULT_HORIZON = timedelta(hours=24)
MINUTE = timedelta(minutes=1)


@dataclass
class Resolution:
    prediction_id: str
    status: str                      # WAITING / OPEN / CLOSED / UNRESOLVED
    outcome_state: str | None = None
    triggered_at: datetime | None = None
    resolved_at: datetime | None = None
    path_coverage: str = "COMPLETE"
    r_multiple: Decimal | None = None
    mfe_r: Decimal | None = None
    mae_r: Decimal | None = None
    notes: str = ""


def parse_horizon(text: str | None) -> timedelta:
    match = re.fullmatch(r"\s*(\d+)\s*([hd])\s*", text or "", re.IGNORECASE)

    if not match:
        return DEFAULT_HORIZON

    amount = int(match.group(1))
    return timedelta(hours=amount) if match.group(2).lower() == "h" else timedelta(days=amount)


def _ceil_minute(moment: datetime) -> datetime:
    floor = moment.replace(second=0, microsecond=0)
    return floor if floor == moment else floor + MINUTE


def load_minutes(symbol: str, start: datetime, end: datetime, source: str = "TwelveData"):
    """Stored 1-minute bars with start <= bar_time <= end, oldest first."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT bar_time, high, low, close FROM raw_bars
            WHERE symbol = ? AND timeframe = '1min' AND source = ?
              AND bar_time >= ? AND bar_time <= ?
            ORDER BY bar_time ASC
            """,
            (symbol, source, start.isoformat(), end.isoformat()),
        ).fetchall()

    return [
        (
            datetime.fromisoformat(r["bar_time"]).astimezone(timezone.utc),
            Decimal(r["high"]),
            Decimal(r["low"]),
            Decimal(r["close"]),
        )
        for r in rows
    ]


def _missing_minutes(times: set, start: datetime, last: datetime) -> int:
    missing, current = 0, start

    while current <= last:
        if is_fx_market_open(current) and current not in times:
            missing += 1

        current += MINUTE

    return missing


def _covered_through(last_data: datetime, deadline: datetime) -> bool:
    """True when no in-session minute between the last stored bar and the
    deadline can still be missing (data complete up to the horizon)."""
    current = last_data + MINUTE

    while current < deadline:
        if is_fx_market_open(current):
            return False

        current += MINUTE

    return True


def resolve_prediction(p: dict, now: datetime | None = None) -> Resolution:
    if now is None:
        now = datetime.now(timezone.utc)

    t0 = datetime.fromisoformat(p["t0"]).astimezone(timezone.utc)
    deadline = t0 + parse_horizon(p["primary_horizon"])
    start = _ceil_minute(t0)
    decision = p["decision"]
    buy = p["direction"] == "BUY"
    sign = Decimal(1) if buy else Decimal(-1)

    entry = Decimal(p["entry"])
    stop = Decimal(p["stop_loss"])
    tp1 = Decimal(p["tp1"])
    risk = sign * (entry - stop)
    planned_rr = sign * (tp1 - entry) / risk

    is_now = decision.endswith("NOW")
    res = Resolution(prediction_id=p["prediction_id"], status="WAITING")
    triggered = is_now
    trigger_time = t0 if is_now else None

    if is_now:
        res.triggered_at = t0
        res.status = "OPEN"

    end = min(now, deadline)
    bars = load_minutes(p["instrument"], start, end)
    times = {b[0] for b in bars}

    mfe = mae = Decimal(0)
    last_close = None
    resolved = None                     # (outcome, time, note)

    for time, high, low, close in bars:
        if time > now:
            break

        last_close = close
        best = high if buy else low             # most favourable price in the bar
        worst = low if buy else high            # most adverse price in the bar
        sl_hit = sign * (worst - stop) <= 0
        tp_hit = sign * (best - tp1) >= 0

        if not triggered:
            touched = sign * (worst - entry) <= 0     # limit order at the entry price

            if touched:
                triggered, trigger_time = True, time
                res.triggered_at, res.status = time, "OPEN"

                if sl_hit or tp_hit:
                    resolved = ("SEQUENCE_UNKNOWN", time,
                                "vstup a SL/TP1 ve stejne minute - poradi neznamé")
                    break

                continue

            if tp_hit:
                resolved = ("NOT_ACTIVATED", time, "cil TP1 dosazen bez vstupu")
                break

            continue

        mfe = max(mfe, sign * (best - entry) / risk)
        mae = max(mae, sign * (entry - worst) / risk)

        if sl_hit and tp_hit:
            resolved = ("SEQUENCE_UNKNOWN", time, "SL a TP1 ve stejne minute - poradi neznamé")
            break

        if sl_hit:
            resolved = ("SL_BEFORE_TP1", time, "SL dosazen drive nez TP1")
            break

        if tp_hit:
            resolved = ("TP1_BEFORE_SL", time, "TP1 dosazen drive nez SL")
            break

    last_data = bars[-1][0] if bars else start - MINUTE

    if resolved is None:
        if now >= deadline and _covered_through(last_data, deadline):
            if triggered:
                r = sign * (last_close - entry) / risk if last_close is not None else Decimal(0)
                resolved = ("EXPIRED", deadline, f"horizont skoncil, obchod nebyl uzavren ({r:+.2f} R)")
                res.r_multiple = r
            else:
                resolved = ("NOT_ACTIVATED", deadline, "horizont skoncil bez vstupu")
        else:
            res.mfe_r, res.mae_r = (mfe, mae) if triggered else (None, None)
            return res

    outcome, when, note = resolved
    holes = _missing_minutes(times, start, min(when, last_data)) if bars else 0

    res.resolved_at = when
    res.notes = note
    res.mfe_r, res.mae_r = (mfe, mae) if triggered else (None, None)

    if holes:
        res.outcome_state = "UNRESOLVED"
        res.status = "UNRESOLVED"
        res.path_coverage = f"PARTIAL ({holes} min chybi)"
        res.notes = f"{note}; v datech chybi {holes} minut pred rozhodnutim - nelze potvrdit"
        res.r_multiple = None
        return res

    res.outcome_state = outcome
    res.status = "CLOSED"

    if outcome == "TP1_BEFORE_SL":
        res.r_multiple = planned_rr
    elif outcome == "SL_BEFORE_TP1":
        res.r_multiple = Decimal(-1)
    elif outcome != "EXPIRED":
        res.r_multiple = None

    return res


def apply_resolution(p: dict, res: Resolution, now: datetime) -> list[str]:
    """Append the missing states / outcome to the ledger. Idempotent."""
    actions = []
    states = {s["state"] for s in p["states"]}
    t0 = datetime.fromisoformat(p["t0"]).astimezone(timezone.utc)
    pid = p["prediction_id"]

    if p["decision"].startswith("WAIT") and "WAITING" not in states:
        add_state(pid, "WAITING", "cekani na vstup", changed_at=t0)
        actions.append("stav WAITING")

    if res.triggered_at and "TRIGGERED" not in states:
        add_state(pid, "TRIGGERED", "vstup aktivovan", changed_at=res.triggered_at)
        actions.append("stav TRIGGERED")

    if res.outcome_state:
        recorded = [o["outcome_state"] for o in p["outcomes"]]
        last = recorded[-1] if recorded else None
        new_information = last is None or (last == "UNRESOLVED" and res.outcome_state != "UNRESOLVED")

        if new_information:
            record_outcome(
                pid,
                res.outcome_state,
                path_coverage=res.path_coverage,
                r_multiple=res.r_multiple,
                mfe=res.mfe_r,
                mae=res.mae_r,
                notes=res.notes,
                recorded_at=now,
            )
            actions.append(f"vysledek {res.outcome_state}")

            final_state = STATE_FOR_OUTCOME.get(res.outcome_state)

            if final_state and final_state not in states:
                add_state(pid, final_state, res.notes, changed_at=res.resolved_at or now)
                actions.append(f"stav {final_state}")

    return actions


def resolve_all(now: datetime | None = None, instrument: str | None = None, limit: int = 1000):
    """Resolve every prediction that is not closed yet. Returns [(prediction, resolution, actions)]."""
    if now is None:
        now = datetime.now(timezone.utc)

    results = []

    for p in reversed(list_predictions(instrument, limit=limit)):
        if p["direction"] == "NONE":
            continue

        closed = any(o["outcome_state"] in FINAL_OUTCOMES for o in p["outcomes"])

        if closed:
            results.append((p, None, []))
            continue

        res = resolve_prediction(p, now)
        results.append((p, res, apply_resolution(p, res, now)))

    return results
