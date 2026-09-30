"""FXBOT - evaluate locked predictions.

    python scripts/resolve.py            # resolve what is due and show everything
    python scripts/resolve.py --open     # only predictions that are still open

Replays the stored 1-minute bars after each prediction was locked and records
what happened (entry touched? SL or TP1 first?). When SL and TP1 lie inside
the same 1-minute bar the order is unknown and is NEVER guessed. Run
scripts/update_data.py first so that the data reach the present.

Mid prices, no spread or slippage: results are optimistic. Under 20 closed
predictions the numbers are only descriptive (specification module 66).
"""

import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_update import DEFAULT_SYMBOLS  # noqa: E402,F401  (loads .env first)
from src.database import initialize_database  # noqa: E402
from src.resolver import FINAL_OUTCOMES, resolve_all  # noqa: E402
from src.tech_analysis import quantize  # noqa: E402

DECISION_CZ = {
    "BUY NOW": "KOUPIT TED",
    "SELL NOW": "PRODAT TED",
    "WAIT FOR BUY": "CEKAT NA NAKUP",
    "WAIT FOR SELL": "CEKAT NA PRODEJ",
}
OUTCOME_CZ = {
    "TP1_BEFORE_SL": "TP1 dosazen drive nez SL",
    "SL_BEFORE_TP1": "SL dosazen drive nez TP1",
    "SEQUENCE_UNKNOWN": "poradi neznamé (SL i TP1 ve stejne minute)",
    "EXPIRED": "horizont skoncil, obchod nebyl uzavren",
    "NOT_ACTIVATED": "vstup se neuskutecnil",
    "UNRESOLVED": "nerozhodnuto - v datech chybi minuty",
}


def closed_result(p: dict, res):
    """(final outcome, R multiple) of a closed prediction, else (None, None)."""
    if res is not None and res.status == "CLOSED":
        return res.outcome_state, res.r_multiple

    finals = [o for o in p["outcomes"] if o["outcome_state"] in FINAL_OUTCOMES]

    if finals:
        r = finals[-1]["r_multiple"]
        return finals[-1]["outcome_state"], (Decimal(r) if r else None)

    return None, None


def status_line(p: dict, res) -> str:
    if res is None:                                        # already closed earlier
        last = [o for o in p["outcomes"] if o["outcome_state"] in FINAL_OUTCOMES][-1]
        r = last["r_multiple"]
        return f"UZAVRENO: {OUTCOME_CZ[last['outcome_state']]}" + (f" ({Decimal(r):+.2f} R)" if r else "")

    if res.status == "CLOSED":
        text = OUTCOME_CZ[res.outcome_state]
        return f"UZAVRENO: {text}" + (f" ({res.r_multiple:+.2f} R)" if res.r_multiple is not None else "")

    if res.status == "UNRESOLVED":
        return f"NEROZHODNUTO: {res.notes}"

    if res.status == "OPEN":
        since = res.triggered_at.strftime("%d.%m. %H:%M")
        return f"OTEVRENO od {since} UTC" + (
            f" | zatim max +{res.mfe_r:.2f} R / -{res.mae_r:.2f} R" if res.mfe_r is not None else ""
        )

    return "CEKA NA VSTUP"


def main(argv: list[str], now: datetime | None = None) -> int:
    initialize_database()
    now = now or datetime.now(timezone.utc)
    results = resolve_all(now)
    only_open = "--open" in argv

    print("=" * 60)
    print("FXBOT - VYHODNOCENI PREDIKCI")
    print("=" * 60)
    print(f"cas (UTC): {now.strftime('%Y-%m-%d %H:%M')}")
    print("-" * 60)

    if not results:
        print("Zadne zamcene predikce. Nejdriv: python scripts/analyze.py --lock")
        print("=" * 60)
        return 0

    closed = Counter()
    r_values = []

    for p, res, actions in results:
        final, r = closed_result(p, res)

        if final:
            closed[final] += 1

            if r is not None and final in ("TP1_BEFORE_SL", "SL_BEFORE_TP1", "EXPIRED"):
                r_values.append(r)

            if only_open:
                continue

        symbol = p["instrument"]
        print(
            f"{p['prediction_id'][-5:]} {symbol} {DECISION_CZ[p['decision']]}"
            f" | vstup {quantize(symbol, Decimal(p['entry']))} SL {quantize(symbol, Decimal(p['stop_loss']))}"
            f" TP1 {quantize(symbol, Decimal(p['tp1']))}"
        )
        print(f"      zamceno {p['locked_at'][:16].replace('T', ' ')} UTC | {status_line(p, res)}")

        if actions:
            print(f"      zapsano do evidence: {', '.join(actions)}")

    total = len(results)
    n_closed = sum(closed.values())
    print("-" * 60)
    print(f"predikci celkem {total} | uzavrenych {n_closed} | otevrenych {total - n_closed}")

    if n_closed:
        wins, losses = closed["TP1_BEFORE_SL"], closed["SL_BEFORE_TP1"]
        line = f"TP1 pred SL: {wins} | SL pred TP1: {losses} | neznamé poradi: {closed['SEQUENCE_UNKNOWN']}"
        line += f" | vyprsely: {closed['EXPIRED']} | bez vstupu: {closed['NOT_ACTIVATED']}"
        print(line)

        if r_values:
            print(f"soucet R (uzavrene obchody): {sum(r_values):+.2f} R z {len(r_values)}")

        if n_closed < 20:
            print(f"vzorek n={n_closed} (<20): pouze popisne, bez zaveru o uspesnosti")

    print("Ceny stredni, bez spreadu a slippage - vysledky jsou optimisticke.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
