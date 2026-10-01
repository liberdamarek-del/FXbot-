"""CHALLENGER CH-007 "75+": the high win-rate system found by
scripts/winrate_lab2.py (docs/USPESNOST75_K2.md), every day.

    python scripts/signals_75.py          # today's orders and tomorrow's trigger prices
    python scripts/signals_75.py --lock   # + record the orders in the ledger (forward test)

Rule (2014-2026 backtest on hourly BID/ASK with costs: 479 trades, 83 %
winners, +0.045 R per trade; the forward test is the real proof):

    BUY  when at the daily close (New York 17:00) RSI(3) < 15, the close is
         above SMA(200) and ATR(14) is above its 30th percentile of 250 days
    -> LIMIT order 0.5 x ATR below the close, valid 24 h
    -> TP 0.4 x ATR above the fill, SL 2.0 x ATR below, close after 5 days
    SELL mirrored (RSI(3) > 85, below SMA(200)).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import research_signals as RS  # noqa: E402  (loads .env first)
import strategy_mining as SM  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402

UTC = timezone.utc
MODEL = "CHALLENGER-75"
RSI_N, LOW, HIGH = 3, 15.0, 85.0
LIMIT_ATR, TP_ATR, SL_ATR, HOLD_DAYS = 0.5, 0.4, 2.0, 5


def wilder_state(c: np.ndarray, n: int) -> tuple[float, float]:
    """Last Wilder average gain and loss of RSI(n)."""
    d = np.diff(c, prepend=c[0])
    gain, loss = SM.wilder(np.clip(d, 0, None), n), SM.wilder(np.clip(-d, 0, None), n)
    return float(gain[-1]), float(loss[-1])


def trigger_close(c_last: float, ag: float, al: float, n: int, side: int) -> float:
    """Close at which RSI(n) crosses LOW (BUY) / HIGH (SELL) on the next bar."""
    if side > 0:          # down move d: AL' = (AL(n-1)+d)/n, AG' = AG(n-1)/n; RSI' < LOW <=> AG'/AL' < LOW/(100-LOW)
        d = (n - 1) * (ag * (100 - LOW) / LOW - al)
        return c_last - max(0.0, d)
    d = (n - 1) * (al * HIGH / (100 - HIGH) - ag)
    return c_last + max(0.0, d)


def analyse(symbol: str) -> dict:
    bars, sources = RS.stitched_daily(symbol)
    o, h, l, c = (np.array([getattr(b, k) for b in bars]) for k in ("mo", "mh", "ml", "mc"))
    atr = SM.wilder(SM.true_range(h, l, c), 14)
    rsi = SM.rsi(c, RSI_N)
    sma200 = SM.sma(c, 200)
    window = atr[-250:]
    pct = float((window <= atr[-1]).mean())
    ag, al = wilder_state(c, RSI_N)
    trend = 1 if c[-1] > sma200[-1] else -1
    inst = get_instrument(symbol)
    day = datetime.fromtimestamp(bars[-1].ts + 86400, tz=UTC).date()
    out = {"symbol": symbol, "day": day, "close": float(c[-1]), "atr": float(atr[-1]), "rsi": float(rsi[-1]),
           "trend": trend, "vol_ok": pct > 0.3, "pct": pct, "sma200": float(sma200[-1]), "d": inst.decimals,
           "source": sources[-1], "signal": 0}
    if out["vol_ok"] and trend > 0 and rsi[-1] < LOW:
        out["signal"] = 1
    elif out["vol_ok"] and trend < 0 and rsi[-1] > HIGH:
        out["signal"] = -1
    out["next_trigger"] = trigger_close(float(c[-1]), ag, al, RSI_N, trend)
    return out


def order(a: dict) -> tuple[float, float, float]:
    s = a["signal"]
    entry = a["close"] - s * LIMIT_ATR * a["atr"]
    return entry, entry + s * TP_ATR * a["atr"], entry - s * SL_ATR * a["atr"]


def lock(a: dict) -> str:
    from src.database import initialize_database
    from src.prediction_ledger import PredictionRejected, initialize_ledger, list_predictions, lock_prediction

    initialize_database()
    initialize_ledger()
    now = datetime.now(UTC)
    for p in list_predictions(instrument=a["symbol"], limit=50):
        if p["model_version"] == MODEL and p["t0"][:10] == now.date().isoformat():
            return "uz zapsano dnes"
    side = "BUY" if a["signal"] > 0 else "SELL"
    entry, tp, sl = order(a)
    q = lambda v: round(v, a["d"])
    try:
        return lock_prediction(
            model_version=MODEL, run_id="SIGNALS-75", t0=now, instrument=a["symbol"], decision=f"WAIT FOR {side}",
            reference_price=q(a["close"]), price_source=f"denni zaver {a['day']} ({a['source']})", price_timestamp=now,
            data_state="CURRENT", data_quality="C", forecast_mode="CHALLENGER", setup_type="RSI3_PULLBACK",
            entry=q(entry), trigger_price=q(entry), stop_loss=q(sl), tp1=q(tp), primary_horizon=f"{HOLD_DAYS * 24}h",
            thesis=f"RSI({RSI_N}) {a['rsi']:.0f}, trend SMA200 {'nahoru' if a['trend'] > 0 else 'dolu'}",
            counterforce="pokles muze pokracovat (SL 2 ATR)", invalidation=f"SL {q(sl)}",
            reasons=["CH-007 75+"], inputs={"entry_mode": "limit", "analysis_price": a["close"], "rule": "CH-007"},
            now=now)
    except PredictionRejected as exc:
        return f"zamitnuto: {exc}"


def main(argv: list[str]) -> int:
    symbols = parse_symbols(argv[argv.index("--symbols") + 1] if "--symbols" in argv else None)
    print("=" * 100)
    print(f"CH-007 '75+' (backtest 2014-2026: 83 % uspesnych, +0.045 R/obchod; dopredu neovereno) - "
          f"{datetime.now(UTC):%Y-%m-%d %H:%M} UTC")
    print("=" * 100)
    for symbol in symbols:
        a = analyse(symbol)
        d = a["d"]
        head = (f"{symbol:8} zaver {a['day']} {a['close']:.{d}f} | RSI({RSI_N}) {a['rsi']:5.1f} | trend SMA200 "
                f"{'nahoru' if a['trend'] > 0 else 'dolu  '} | volatilita {'OK' if a['vol_ok'] else 'nizka'}")
        if a["signal"]:
            entry, tp, sl = order(a)
            side = "BUY" if a["signal"] > 0 else "SELL"
            status = lock(a) if "--lock" in argv else "(nezapsano)"
            print(f"{head}\n         -> {side} LIMIT {entry:.{d}f} (plati 24 h), TP {tp:.{d}f}, SL {sl:.{d}f}, "
                  f"max {HOLD_DAYS} dni | {status}")
        else:
            side = "BUY" if a["trend"] > 0 else "SELL"
            cond = "<=" if a["trend"] > 0 else ">="
            note = "" if a["vol_ok"] else " (a volatilita nad 30. percentilem)"
            print(f"{head}\n         -> zitra {side}, kdyz denni zaver {cond} {a['next_trigger']:.{d}f}{note}")
    print("-" * 100)
    print("Riziko na obchod nejvyse 1 % uctu. Vysledky dopredu: python fxbot.py review --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
