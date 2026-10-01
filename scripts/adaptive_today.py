"""Self-learning challenger CH-006 "ADAPTIVE": re-learns every month which of
the 8 280 rules works now, trades only that one, records its signals.

    python scripts/adaptive_today.py            # today's selection and signals
    python scripts/adaptive_today.py --lock     # + record the signals in the ledger (daily, automatic)
    python scripts/adaptive_today.py --relearn  # force a new selection now

Meta-rule (chosen on 2017-2021 by scripts/adaptive_lab.py, docs/ADAPTIVNI.md):
re-learn at the first run of every month (P = 1), rank all rules by the
t-value of their closed trades in the trailing 36 months (W = 36), trade the
single best one with a positive mean (K = 1). A rule that stops working
loses its rank and is replaced at the next re-learning - nothing is fixed.

Each signal: entry at the latest daily close (New York 17:00), exit after
the rule's holding period (1 / 3 / 5 trading days); protective SL and TP
3 x ATR(D1). Recorded as model CHALLENGER-ADAPTIVE; `python fxbot.py review
--all` shows its forward result against a random direction.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import adaptive_lab as AL  # noqa: E402  (loads .env first)
import research_signals as RS  # noqa: E402
import strategy_mining as SM  # noqa: E402
from src.instruments import get_instrument  # noqa: E402
from src.path_archive import trading_date  # noqa: E402

UTC = timezone.utc
MODEL = "CHALLENGER-ADAPTIVE"
WINDOW_MONTHS, K = 36, 1
ATR_MULT = 3.0
STATE = PROJECT_ROOT / "data" / "research" / "adaptive_state.json"


def rule_signal(panel: dict, name: str, fname: str, sign: float) -> np.ndarray:
    sig = np.nan_to_num(panel["S"][name]) * sign
    filt = SM.fundamental_filters(panel)[fname]

    if filt is None:
        return sig
    if filt.ndim == 3:
        agree, against = (filt == sig[None]).sum(axis=0), (filt == -sig[None]).sum(axis=0)
        return np.where((agree >= 1) & (against == 0), sig, 0)
    return np.where(filt == 0, sig, np.where(filt == sig, sig, 0))


def relearn(panel: dict) -> dict:
    X, names, hz = AL.rule_matrix(panel)
    roll = AL.Rolling(X)
    T = len(panel["dates"])
    t, mean = AL.scores(roll, hz, T, WINDOW_MONTHS * 21)
    order = np.argsort(-t)
    best = [int(i) for i in order[:10] if np.isfinite(t[i]) and mean[i] > 0]
    pick = [names[i] for i in best[:K]]
    return {"learned_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "data_until": panel["dates"][-1].isoformat(), "month": panel["dates"][-1].strftime("%Y-%m"),
            "rules": [{"name": n[0], "filter": n[1], "sign": 1.0 if n[2] == "podle" else -1.0, "hz": int(n[3]),
                       "t": float(t[i]), "mean": float(mean[i])} for n, i in zip(pick, best[:K])],
            "runners_up": [{"rule": " / ".join(map(str, names[i])), "t": float(t[i])} for i in best[K:10]]}


def lock(symbol: str, side: str, price: float, atr: float, hz: int, why: str) -> str:
    from src.database import initialize_database
    from src.prediction_ledger import PredictionRejected, initialize_ledger, list_predictions, lock_prediction

    initialize_database()
    initialize_ledger()
    now = datetime.now(UTC)

    for p in list_predictions(instrument=symbol, limit=50):
        if p["model_version"] == MODEL and p["t0"][:10] == now.date().isoformat():
            return "uz zapsano dnes"

    inst = get_instrument(symbol)
    q = lambda v: round(v, inst.decimals)
    sign = 1 if side == "BUY" else -1

    try:
        return lock_prediction(
            model_version=MODEL, run_id="ADAPTIVE", t0=now, instrument=symbol, decision=f"{side} NOW",
            reference_price=q(price), price_source="archiv (denni zaver NY 17:00)", price_timestamp=now,
            data_state="CURRENT", data_quality="C", forecast_mode="CHALLENGER", setup_type="ADAPTIVE",
            entry=q(price), stop_loss=q(price - sign * ATR_MULT * atr), tp1=q(price + sign * ATR_MULT * atr),
            primary_horizon=f"{hz * 24}h", thesis=why, counterforce="pravidlo vybrane z minulosti nemusi dal fungovat",
            invalidation=f"SL {ATR_MULT} x ATR(D1)", reasons=["CH-006 ADAPTIVE"],
            inputs={"entry_mode": "limit", "analysis_price": price, "rule": why}, now=now)
    except PredictionRejected as exc:
        return f"zamitnuto: {exc}"


def main(argv: list[str]) -> int:
    started = time.monotonic()
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        RS.extract()                                 # fundamentals per day, refreshed
        panel = SM.build_panel()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    month = panel["dates"][-1].strftime("%Y-%m")

    if "--relearn" in argv or state.get("month") != month:
        state = relearn(panel)
        STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False))
        print(f"PREUCENO ({state['learned_at']}) na datech do {state['data_until']}")

    print("=" * 96)
    print(f"CH-006 ADAPTIVNI VYZYVATEL - data do {panel['dates'][-1]} | uceni {state['learned_at'][:10]} "
          f"(okno {WINDOW_MONTHS} mesicu, preuceni mesicne)")
    print("=" * 96)

    if not state["rules"]:
        print("zadne pravidlo nema v poslednich 36 mesicich kladny vysledek -> neobchodovat")
        return 0

    for rule in state["rules"]:
        why = (f"{rule['name']} / {rule['filter']} / {'podle' if rule['sign'] > 0 else 'proti'} signalu / "
               f"drzeni {rule['hz']} d (36 mes.: t {rule['t']:+.1f}, prumer {rule['mean']:+.3f} ATR)")
        print("VYBRANE PRAVIDLO:", why)
        sig = rule_signal(panel, rule["name"], rule["filter"], rule["sign"])

        for p, symbol in enumerate(panel["symbols"]):
            bars, _ = RS.stitched_daily(symbol)
            last = bars[-1]
            atr = float(SM.wilder(SM.true_range(*(np.array([getattr(b, k) for b in bars]) for k in ("mh", "ml", "mc"))),
                                  14)[-1])
            value = sig[p, panel["dates"].index(trading_date(last.ts))]
            side = "BUY" if value > 0 else "SELL" if value < 0 else None
            d = get_instrument(symbol).decimals
            day = datetime.fromtimestamp(last.ts + 86400, tz=UTC).date()

            if side is None:
                print(f"  {symbol:8} zaver {day} {last.mc:.{d}f} | bez signalu")
                continue

            sl = last.mc - (1 if side == "BUY" else -1) * ATR_MULT * atr
            tp = last.mc + (1 if side == "BUY" else -1) * ATR_MULT * atr
            status = lock(symbol, side, last.mc, atr, rule["hz"], why) if "--lock" in argv else "(nezapsano)"
            print(f"  {symbol:8} zaver {day} {last.mc:.{d}f} | {side} na {rule['hz']} d, SL {sl:.{d}f}, "
                  f"TP {tp:.{d}f} | {status}")

    print("-" * 96)
    print("Dalsi kandidati (pri dalsim preuceni mohou nahradit vybrane pravidlo):")
    for r in state["runners_up"][:5]:
        print(f"  t {r['t']:+.1f}  {r['rule']}")
    print(f"Vyzyvatel neni potvrzeny; vysledky: python fxbot.py review --all | {time.monotonic() - started:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
