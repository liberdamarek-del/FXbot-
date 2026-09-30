"""Top-3 selection with factor concentration (modules 57, 58, 141).

Ranking: evidence class (A before B before C), then NOW before WAIT, then
R:R after costs. R:R alone never ranks a weak mechanism first (module 55).

Factor concentration (module 58): two candidates that hold the same
currency in the same direction are one exposure, not two independent
edges (EUR/USD long + GBP/USD long = one USD-negative bet). Only the best
of them is selected; the other is reported with the reason.
"""

from dataclasses import dataclass, field

from src.engine.decision import CONFIDENCE_RANK, Candidate
from src.engine.params import ModelParams


@dataclass
class Selection:
    top: list = field(default_factory=list)                 # Candidate
    concentration: dict = field(default_factory=dict)       # symbol -> reason
    others: list = field(default_factory=list)              # actionable, not selected


def rank_key(candidate: Candidate):
    return (
        CONFIDENCE_RANK.get(candidate.confidence, 9),
        0 if candidate.is_now else 1,
        -(candidate.rr_net or 0.0),
        candidate.symbol,
    )


def shared_exposure(a: Candidate, b: Candidate) -> str | None:
    ea, eb = a.exposure(), b.exposure()

    for currency, sign in ea.items():
        if eb.get(currency) == sign:
            return f"{'long' if sign > 0 else 'short'} {currency}"

    return None


def select_top(candidates: list[Candidate], p: ModelParams) -> Selection:
    selection = Selection()
    ranked = sorted((c for c in candidates if c.actionable), key=rank_key)

    for candidate in ranked:
        overlap = next(((chosen, shared_exposure(chosen, candidate)) for chosen in selection.top
                        if shared_exposure(chosen, candidate)), None)

        if overlap:
            chosen, exposure = overlap
            selection.concentration[candidate.symbol] = (
                f"stejna sazka jako {chosen.symbol} ({exposure}) - faktorova koncentrace"
            )
            selection.others.append(candidate)
            continue

        if len(selection.top) < p.max_candidates:
            selection.top.append(candidate)
        else:
            selection.others.append(candidate)

    return selection


def position_size(balance: float, risk_pct: float, entry: float, stop: float, pip: float,
                  pip_value_per_lot: float | None = None) -> dict:
    """Units for a given account risk (module 57). Without the broker's pip
    value, the result is expressed in units of the base currency for an
    account in the quote currency (an approximation, stated as such)."""
    risk_money = balance * risk_pct / 100.0
    distance = abs(entry - stop)

    if distance <= 0:
        return {"units": 0, "risk_money": risk_money, "note": "neplatna vzdalenost SL"}

    units = risk_money / distance
    out = {"units": units, "risk_money": risk_money, "stop_pips": distance / pip}

    if pip_value_per_lot:
        out["lots"] = risk_money / ((distance / pip) * pip_value_per_lot)

    out["note"] = "odhad v jednotkach zakladni meny (ucet v kotacni mene); presne jen s udaji brokera"
    return out
