"""Paper account derived from the immutable prediction ledger (module 57, 67).

No separate order book to drift out of sync: every locked prediction of
the V7.8.0 implementation is one paper trade, sized by its locked risk
percentage (inputs / confidence), and its P/L is the resolved side-correct
R multiple. The equity curve can therefore always be recomputed from the
ledger alone (reproducible, module 99).
"""

import json
from datetime import datetime, timezone

from src.prediction_ledger import list_predictions
from src.stats.performance import max_drawdown

UTC = timezone.utc


def paper_equity(start_balance: float = 10000.0, model_prefix: str = "V7.8.0") -> dict:
    trades = []

    for p in reversed(list_predictions(limit=10000)):
        if not p["model_version"].startswith(model_prefix) or p["direction"] == "NONE" or not p["outcomes"]:
            continue

        last = p["outcomes"][-1]

        if last["r_multiple"] is None:
            continue

        risk_pct = 0.5

        try:
            inputs = json.loads(p["inputs"] or "{}")
            risk_pct = float(inputs.get("risk_pct", risk_pct))
        except (ValueError, TypeError):
            pass

        trades.append((p["t0"], p["prediction_id"], p["instrument"], float(last["r_multiple"]), risk_pct,
                       last["outcome_state"]))

    balance = start_balance
    curve = []
    r_values = []

    for t0, pid, symbol, r, risk_pct, state in trades:
        pnl = balance * risk_pct / 100.0 * r
        balance += pnl
        r_values.append(r)
        curve.append({"t0": t0, "prediction_id": pid, "symbol": symbol, "r": r, "pnl": round(pnl, 2),
                      "balance": round(balance, 2), "outcome": state})

    return {"start": start_balance, "balance": round(balance, 2), "trades": len(curve),
            "return_pct": round((balance / start_balance - 1) * 100, 2),
            "max_drawdown_r": max_drawdown(r_values), "curve": curve,
            "computed_at": datetime.now(UTC).isoformat()}
