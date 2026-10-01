"""Today's signals of the CHALLENGER CH-005 "FUND_DIP" and their trigger prices.

    python scripts/signals_today.py                  # all 12 pairs (Twelve Data key: ~2 min, 8 calls/min)
    python scripts/signals_today.py --symbols USD/JPY
    python scripts/signals_today.py --lock           # record triggered signals in the ledger (forward test)

Rule (docs/CHANGE_LOG.md CH-005; the common pattern of the best mined rules,
NOT yet confirmed - that is what the forward test is for):

    direction  fundamentals: >= 1 cluster for and none against among carry
               (2y rate difference), 20-day rate momentum, VIX risk (risk
               currencies vs safe havens) and the central-bank policy trend
    entry      at the daily close when Williams %R(9) <= -90 (BUY) or >= -10
               (SELL), i.e. close <= LL9 + 10 % of the 9-day range (BUY)
    exit       after 5 trading days; protective SL and TP 3 x ATR(D1)

Daily bars: Twelve Data (UTC days) when a key is set, else the local archive.
"""

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from research_signals import RISK_BETA, Fundamentals  # noqa: E402  (loads .env first)
from src.instruments import get_instrument, parse_symbols  # noqa: E402
from src.sources.http import FetchError, fetch  # noqa: E402
from src.v78.sources import twelve_data_key  # noqa: E402

UTC = timezone.utc
MODEL = "CHALLENGER-FUND-DIP"
WR_N, ATR_MULT, HOLD = 9, 3.0, "120h"


def daily_bars(symbol: str, key: str | None) -> tuple[list, str]:
    """[(date, o, h, l, c)] oldest first, completed bars + the forming one."""
    if key:
        try:
            _, content, _ = fetch("https://api.twelvedata.com/time_series", retries=2, params={
                "symbol": symbol, "interval": "1day", "outputsize": 60, "timezone": "UTC", "apikey": key})
            data = json.loads(content)
            if "values" in data:
                rows = [(v["datetime"], *(float(v[k]) for k in ("open", "high", "low", "close"))) for v in data["values"]]
                return list(reversed(rows)), "Twelve Data (UTC dny)"
        except (FetchError, ValueError):
            pass

    from src.engine.data import load_pair
    from src.engine.params import DEFAULT_PARAMS

    d1 = load_pair(symbol, DEFAULT_PARAMS).d1
    rows = [(d1.time(i).date().isoformat(), d1.open[i], d1.high[i], d1.low[i], d1.close[i]) for i in range(len(d1))]
    return rows[-60:], "archiv (muze byt zastaraly)"


def fundamental_direction(symbol: str, t: int, fund: Fundamentals) -> tuple[int, list]:
    inst = get_instrument(symbol)
    b, q = fund.currency(inst.base, t), fund.currency(inst.quote, t)
    sgn = lambda x: 0 if x is None or x == 0 else (1 if x > 0 else -1)
    diff = lambda x, y: None if x is None or y is None else x - y
    carry = diff(b["short"], q["short"])
    rates = diff(carry, diff(b["short_20"], q["short_20"]))
    policy = diff(diff(b["policy"], b["policy_6m"]), diff(q["policy"], q["policy_6m"]))
    vix, vix_7 = fund.value("GLOBAL.VIX", t), fund.value("GLOBAL.VIX", t, 7)
    beta = RISK_BETA.get(inst.base, 0.0) - RISK_BETA.get(inst.quote, 0.0)
    risk = None if vix is None or vix_7 is None or not beta else -(vix - vix_7) * beta
    clusters = {"carry": sgn(carry), "sazby 20d": sgn(rates), "riziko VIX": sgn(risk), "politika CB": sgn(policy)}
    pro = [k for k, v in clusters.items() if v > 0]
    con = [k for k, v in clusters.items() if v < 0]

    if pro and not con:
        return 1, pro
    if con and not pro:
        return -1, con
    return 0, [f"{k} {'+' if v > 0 else '-'}" for k, v in clusters.items() if v]


def analyse(symbol: str, rows: list, fund: Fundamentals) -> dict:
    inst = get_instrument(symbol)
    done = rows[:-1]                    # the last row is the forming day
    now = rows[-1]
    window = rows[-WR_N:]
    hh, ll = max(r[2] for r in window), min(r[3] for r in window)
    trs = [max(r[2], p[4]) - min(r[3], p[4]) for p, r in zip(done[-15:-1], done[-14:])]
    atr = sum(trs) / len(trs)
    direction, why = fundamental_direction(symbol, int(time.time()), fund)
    wr = -100 * (hh - now[4]) / (hh - ll) if hh > ll else -50
    last_window = done[-WR_N:]
    lh, lll = max(r[2] for r in last_window), min(r[3] for r in last_window)
    last_wr = -100 * (lh - done[-1][4]) / (lh - lll) if lh > lll else -50
    out = {"symbol": symbol, "price": now[4], "direction": direction, "why": why, "wr": wr, "atr": atr,
           "last_close": done[-1][4], "last_day": done[-1][0], "triggered_last_close": False}

    if direction > 0:
        out["trigger"] = ll + 0.1 * (hh - ll)
        out["triggered_last_close"] = last_wr <= -90
    elif direction < 0:
        out["trigger"] = hh - 0.1 * (hh - ll)
        out["triggered_last_close"] = last_wr >= -10

    out["pip"] = inst.pip
    out["decimals"] = inst.decimals
    return out


def lock(a: dict) -> str:
    from src.database import initialize_database
    from src.prediction_ledger import PredictionRejected, initialize_ledger, list_predictions, lock_prediction

    initialize_database()
    initialize_ledger()
    now = datetime.now(UTC)

    for p in list_predictions(instrument=a["symbol"], limit=50):
        if p["model_version"] == MODEL and p["t0"][:10] == now.date().isoformat():
            return "uz zapsano dnes"

    side = "BUY" if a["direction"] > 0 else "SELL"
    sign = 1 if side == "BUY" else -1
    q = lambda v: round(v, a["decimals"])
    entry = a["price"]

    try:
        return lock_prediction(
            model_version=MODEL, run_id="SIGNALS-TODAY", t0=now, instrument=a["symbol"], decision=f"{side} NOW",
            reference_price=q(entry), price_source="Twelve Data / archiv (denni zaver)", price_timestamp=now,
            data_state="CURRENT", data_quality="C", forecast_mode="CHALLENGER", setup_type="FUND_DIP",
            entry=q(entry), stop_loss=q(entry - sign * ATR_MULT * a["atr"]), tp1=q(entry + sign * ATR_MULT * a["atr"]),
            primary_horizon=HOLD, thesis="fundamenty: " + ", ".join(a["why"]) + f"; Williams %R(9) {a['wr']:.0f}",
            counterforce="kratkodoby trend proti vstupu", invalidation=f"SL {ATR_MULT} x ATR(D1)",
            reasons=["CH-005 FUND_DIP"], inputs={"entry_mode": "limit", "analysis_price": entry, "rule": "CH-005"},
            now=now)
    except PredictionRejected as exc:
        return f"zamitnuto: {exc}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="CH-005 FUND_DIP signals")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--lock", action="store_true")
    args = parser.parse_args(argv)
    key = twelve_data_key()
    fund = Fundamentals()
    symbols = parse_symbols(args.symbols)
    print("=" * 100)
    print(f"CH-005 FUND_DIP (vyzyvatel, NEOVERENO dopredu) - {datetime.now(UTC):%Y-%m-%d %H:%M} UTC")
    print("=" * 100)

    for k, symbol in enumerate(symbols):
        if key and k and len(symbols) > 1:
            time.sleep(8)               # free plan: 8 calls per minute
        rows, source = daily_bars(symbol, key)

        if len(rows) < 20:
            print(f"{symbol}: malo dat")
            continue

        a = analyse(symbol, rows, fund)
        d = a["decimals"]
        side = {1: "BUY", -1: "SELL", 0: "-"}[a["direction"]]
        line = f"{symbol:8} cena {a['price']:.{d}f} | fundamenty {side:4} ({', '.join(a['why']) or '-'}) | %R(9) {a['wr']:5.0f}"

        if a["direction"] == 0:
            print(line + " | bez fundamentalniho smeru -> nic")
            continue

        trig = a["trigger"]
        dist = abs(a["price"] - trig) / a["pip"]
        sl = trig - a["direction"] * ATR_MULT * a["atr"]
        tp = trig + a["direction"] * ATR_MULT * a["atr"]
        cond = "<=" if a["direction"] > 0 else ">="

        if a["triggered_last_close"]:
            status = f"SIGNAL na zaveru {a['last_day']} ({a['last_close']:.{d}f})"
            if args.lock:
                status += " -> " + lock(a)
        else:
            status = (f"{side} kdyz denni zaver {cond} {trig:.{d}f} ({dist:.0f} pip od ceny); "
                      f"pak SL {sl:.{d}f}, TP {tp:.{d}f}, max 5 dni")
        print(line + " | " + status + f" [{source}]")

    print("-" * 100)
    print("Vyzyvatel neni potvrzeny; zapisovanim (--lock) se meri dopredu: python fxbot.py review --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
