"""FXBOT - technical analysis (TECH-0.1, without macro layer).

    python scripts/analyze.py                    # all pairs, short overview + top 3
    python scripts/analyze.py --pair EUR/USD     # one pair in detail
    python scripts/analyze.py --lock             # also lock actionable setups in the ledger

Works on the STORED data only (run scripts/update_data.py first). A proposal
is made only when the 1-minute data are CURRENT; otherwise the pair gets
NO TRADE with the reason. This is a technical proposal without macro
information and no investment advice; thresholds are provisional.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_update import DEFAULT_SYMBOLS  # noqa: E402  (loads .env first)
from src.database import initialize_database  # noqa: E402
from src.tech_analysis import (  # noqa: E402
    MODEL_VERSION,
    Analysis,
    analyze_symbol,
    decimals,
    quantize,
)

TREND_CZ = {"UP": "roste", "DOWN": "klesa", "RANGE": "bez trendu"}
DECISION_CZ = {
    "BUY NOW": "KOUPIT TED",
    "SELL NOW": "PRODAT TED",
    "WAIT FOR BUY": "CEKAT NA NAKUP",
    "WAIT FOR SELL": "CEKAT NA PRODEJ",
    "NO TRADE": "NEOBCHODOVAT",
}
DUPLICATE_WINDOW = timedelta(hours=4)


def fmt(symbol: str, value: float | None) -> str:
    return "-" if value is None else f"{quantize(symbol, value)}"


def format_pair(a: Analysis, detail: bool = False) -> list[str]:
    s = a.setup
    v4, v1, v15 = a.views["4h"], a.views["1h"], a.views["15min"]
    lines = []

    head = f"{a.symbol}  cena {fmt(a.symbol, a.price)}"

    if v4 and v1:
        head += f" | 4h {TREND_CZ[v4.trend]} | 1h {TREND_CZ[v1.trend]}"

    lines.append(head)

    if s.decision == "NO TRADE":
        lines.append(f"   {DECISION_CZ[s.decision]}: {s.reasons[0]}")
    else:
        lines.append(
            f"   {DECISION_CZ[s.decision]}  zona {fmt(a.symbol, s.zone_low)} - {fmt(a.symbol, s.zone_high)}"
            f"  SL {fmt(a.symbol, s.stop)}"
        )
        lines.append(
            "   TP " + " / ".join(fmt(a.symbol, t) for t in s.targets) + f"  R:R {s.rr:.2f}"
        )

    if detail:
        for name, v in (("4h", v4), ("1h", v1), ("15min", v15)):
            if v is None:
                lines.append(f"   {name}: nedostatek dat")
                continue

            sup = v.supports[0] if v.supports else None
            res = v.resistances[0] if v.resistances else None
            lines.append(
                f"   {name}: {TREND_CZ[v.trend]} | ATR {fmt(a.symbol, v.atr)} "
                f"(percentil {v.atr_percentile:.0f}) | RSI {v.rsi:.0f}"
                f" | podpora {fmt(a.symbol, sup.price) + f' ({sup.touches}x)' if sup else '-'}"
                f" | odpor {fmt(a.symbol, res.price) + f' ({res.touches}x)' if res else '-'}"
            )

        for reason in s.reasons[1:] if s.decision != "NO TRADE" else []:
            lines.append(f"   duvod: {reason}")

    return lines


def format_report(analyses: list[Analysis], now: datetime, detail: bool = False) -> str:
    out = [
        "=" * 60,
        f"FXBOT - TECHNICKA ANALYZA ({MODEL_VERSION}, bez makra)",
        "=" * 60,
        f"cas (UTC): {now.strftime('%Y-%m-%d %H:%M')}",
    ]

    states = sorted({a.data_state for a in analyses})
    out.append("data 1min: " + ", ".join(states))

    if any(s != "CURRENT" for s in states):
        out.append("POZOR: nektera data nejsou CURRENT - navrhy nelze vytvorit.")
        out.append("       Nejdriv: python scripts/update_data.py")

    actionable = sorted(
        (a for a in analyses if a.setup.decision != "NO TRADE"),
        key=lambda a: a.setup.rr or 0,
        reverse=True,
    )

    out.append("-" * 60)

    if actionable:
        out.append("TOP navrhy (razeno podle R:R):")

        for a in actionable[:3]:
            s = a.setup
            out.append(
                f"  {a.symbol}: {DECISION_CZ[s.decision]}  zona {fmt(a.symbol, s.zone_low)}"
                f"-{fmt(a.symbol, s.zone_high)}  SL {fmt(a.symbol, s.stop)}"
                f"  TP1 {fmt(a.symbol, s.targets[0])}  R:R {s.rr:.2f}"
            )
    else:
        out.append("Zadny navrh neprosel branami (viz duvody nize).")

    out.append("-" * 60)

    for a in analyses:
        out.extend(format_pair(a, detail))

    out.append("-" * 60)
    out.append("Technicky navrh bez makra a bez zaruky. Prahy jsou provizorni.")
    out.append("=" * 60)
    return "\n".join(out)


def lock_setup(a: Analysis, now: datetime) -> str:
    """Lock an actionable setup into the prediction ledger. Returns a status text."""
    from src.prediction_ledger import PredictionRejected, list_predictions, lock_prediction

    s = a.setup

    if s.decision == "NO TRADE":
        return "nelze zamknout (NO TRADE)"

    recent = list_predictions(a.symbol, limit=1)

    if recent:
        last = recent[0]
        locked = datetime.fromisoformat(last["locked_at"])

        if last["decision"] == s.decision and now - locked < DUPLICATE_WINDOW:
            return f"preskoceno (stejny navrh uz je zamcen: {last['prediction_id']})"

    v4, v1 = a.views["4h"], a.views["1h"]
    side = "podpora" if s.bias == "BUY" else "odpor"
    opposite = "odpor" if s.bias == "BUY" else "podpora"
    q = lambda value: quantize(a.symbol, value)

    try:
        prediction_id = lock_prediction(
            model_version=MODEL_VERSION,
            t0=now,
            instrument=a.symbol,
            decision=s.decision,
            reference_price=q(a.price),
            price_source="TwelveData 1min",
            price_timestamp=a.price_bar_open + timedelta(minutes=1),
            data_state=a.data_state,
            data_quality="C",
            forecast_mode="TECHNICAL_ONLY",
            setup_type="PULLBACK_TO_LEVEL",
            entry=q(s.entry),
            entry_zone_low=q(s.zone_low),
            entry_zone_high=q(s.zone_high),
            stop_loss=q(s.stop),
            tp1=q(s.targets[0]),
            tp2=q(s.targets[1]),
            tp3=q(s.targets[2]),
            primary_horizon="24h",
            thesis=f"Technicky navrh: 4h {v4.trend}, 1h {v1.trend}; vstup u urovne ({side}).",
            counterforce=f"Protilehla uroven ({opposite}) a chybejici makro vrstva; jediny zdroj dat.",
            invalidation=f"Uzavreni 1h svicky za SL {q(s.stop)}",
            regime=f"4h {v4.trend} / 1h {v1.trend}",
            reasons=s.reasons,
            inputs={
                "atr_1h": round(v1.atr, 6),
                "rsi_1h": round(v1.rsi, 1),
                "rr": round(s.rr, 2),
                "thresholds": "provisional",
            },
            now=now,
        )
    except PredictionRejected as exc:
        return f"zamitnuto: {exc}"

    return f"zamceno: {prediction_id}"


def main(argv: list[str], now: datetime | None = None) -> int:
    initialize_database()
    now = now or datetime.now(timezone.utc)

    symbols = [s.strip() for s in os.getenv("COLLECTOR_SYMBOLS", DEFAULT_SYMBOLS).split(",") if s.strip()]
    detail = False

    if "--pair" in argv:
        index = argv.index("--pair")

        if index + 1 >= len(argv):
            raise SystemExit("--pair needs a value, e.g. --pair EUR/USD")

        symbols = [argv[index + 1].upper()]
        detail = True

    analyses = [analyze_symbol(symbol, now=now) for symbol in symbols]
    print(format_report(analyses, now, detail))

    if "--lock" in argv:
        print("\nZAMKNUTI DO EVIDENCE PREDIKCI:")

        for a in analyses:
            print(f"  {a.symbol}: {lock_setup(a, now)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
