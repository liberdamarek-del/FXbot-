"""H2 - one calculation of entry, target and stop for the backtest, the live plan and the forward test (R-048).

Before R-048 the backtest (profit_deep.simulate) measured the target and the stop from the fill price WITH half the
spread and the slippage (bought at the ask, sold at the bid), the live plan and the forward test from the MID price:
a published target was `half` closer and a published stop `half` farther than the tested ones. Now all three use
src/core/levels.py. This test takes the trades of the simulator (synthetic data, decision 1 h before the Friday
close as the live run) and checks that

1. the live plan (levels.plan_levels, signals_live.make_plan) gives each trade's entry, target and stop (in price and
   in % of the margin) exactly as the simulator had them,
2. a forward trade created from that plan and resolved on the same hourly bars (signals_live.resolve_forward) closes
   in the same hour, for the same reason, with the same result (to the rounding of 0.1 % of the margin and one
   hour of swap).
"""

import contextlib
import os
import sys
import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_h2_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
for p in (PROJECT_ROOT, PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests"):
    sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

import jadro_scenar as S  # noqa: E402
import profit_deep as D  # noqa: E402
import signals_live as SL  # noqa: E402
from src.core import levels as LV  # noqa: E402
from src.core import market as P  # noqa: E402

# ---------------------------------------------------------------- the formulas
assert LV.execution_price(1.10000, 1, 0.00006) == 1.10000 + 0.00006          # buy at the ask
assert LV.execution_price(1.10000, -1, 0.00006) == 1.10000 - 0.00006         # sell at the bid
assert LV.execution_price(1.1, 1, 0.0) == 1.1 and LV.execution_price(1.1, -1, 0.0) == 1.1
assert LV.atr_distances(0.75, 3.0, 0.01) == (0.75 * 0.01, 3.0 * 0.01)
lv = LV.plan_levels(-1, 150.0, 1.2, 0.75, 3.0, 0.0085, 30)
assert lv["entry"] == 150.0 - 0.0085 and lv["tp"] == lv["entry"] - 0.75 * 1.2 and lv["sl"] == lv["entry"] + 3.0 * 1.2
assert lv["tp_margin"] == 0.75 * 1.2 / lv["entry"] * 100 * 30 and lv["sl_margin"] == 3.0 * 1.2 / lv["entry"] * 100 * 30
assert P.half_spread("EUR/USD") == (0.8 / 2 + 0.4 / 2) * 0.0001 and abs(P.half_spread("USD/JPY") - 0.65 * 0.01) < 1e-15

# half = 0: the plan before R-048 (measured from the mid price), published prices are rounded to the decimals
old = SL.make_plan(1, 1.1, 0.01, {"sl": 3.0}, 5, "trh", 30)
assert old["vstup"] == old["vstup_exekucni"] == 1.1 and old["sl"]["cena"] == round(1.1 - 3.0 * 0.01, 5)
new = SL.make_plan(1, 1.1, 0.01, {"sl": 3.0}, 5, "trh", 30, half=0.0001)
assert new["vstup"] == 1.1 and new["vstup_exekucni"] == 1.1001
assert new["sl"]["cena"] == round(1.1001 - 3.0 * 0.01, 5) and new["tp"][0]["cena"] == round(1.1001 + new["tp"][0]["atr"] * 0.01, 5)

# ---------------------------------------------------------------- simulator trades == live plan == forward test
TMP = Path(tempfile.mkdtemp(prefix="fxbot_h2_data_"))
stack = contextlib.ExitStack()
stack.enter_context(S.dirs_core(TMP))
S.zapis_data(SimpleNamespace(P=P), TMP)
D._cache.clear()
D._cache["events"] = S.udalosti()
fields = {**S.BASE_MAX, "exit_before_cb": "", "fund": None, "signal": "D RSI2<10", "hold_days": 10}   # live timing, market entry
rule = replace(D.Rule("h2"), **fields)
base = {"tp": rule.tp, "sl": rule.sl}
checked, reasons, sides = 0, set(), set()
for symbol in S.SYMBOLS:
    s, I = D.prepared_live(symbol, rule.rates_lag, rule.rates_window, rule.rates_src, rule.decide_h, (4,))
    inst_dec = {"EUR/USD": 5, "AUD/JPY": 3}[symbol]
    lev, half = P.leverage(symbol), P.half_spread(symbol)
    hb = {"ts": s["ts"], "h": s["h"], "l": s["l"], "c": s["c"]}
    for t in D.simulate(rule, [symbol]):
        i = s["days"].index(t["day"])
        k0 = s["last"][i] - rule.decide_h
        mid, atr, side = float(s["c"][k0]), float(I["atr"][i]), t["side"]
        # 1. the live plan reproduces the simulator's entry, target and stop
        plan = LV.plan_levels(side, mid, atr, rule.tp, rule.sl, half, lev)
        assert plan["entry"] == t["entry"], (symbol, t["day"], plan["entry"], t["entry"])
        assert plan["tp_margin"] == t["tp_pct"] and plan["sl_margin"] == t["sl_pct"], (symbol, t["day"])
        published = SL.make_plan(side, mid, atr, base, inst_dec, "trh", lev, half)
        assert published["vstup_exekucni"] == round(plan["entry"], inst_dec)
        assert published["sl"]["cena"] == round(plan["sl"], inst_dec)
        assert published["sl"]["proc_marze"] == round(plan["sl_margin"], 1)
        for target in published["tp"]:
            assert target["cena"] == round(plan["entry"] + side * target["atr"] * atr, inst_dec)
        # 2. the forward trade made from the plan closes as the simulator's trade did
        ft = {"id": "x", "par": symbol, "smer": "KOUPIT" if side > 0 else "PRODAT", "den": t["day"].isoformat(),
              "cas_vstupu": int(s["ts"][k0]) + 3600, "vstup": mid, "tp": plan["tp"], "sl": plan["sl"], "stav": "otevreny",
              "cb_vystup": False, "drzeni_dni": rule.hold_days,
              "swap_proc_rocne": round(side * float(I["carry_fin"][i]) - P.FIN_MARKUP, 2)}
        SL.resolve_forward([ft], {symbol: hb})
        assert ft["stav"] == "uzavreny", (symbol, t["day"], ft)
        assert ft["duvod_vystupu"] == {"TP": "TP", "SL": "SL", "CAS": "cas"}[t["reason"]], (symbol, t["day"], t["reason"], ft)
        assert ft["cas_vystupu"] == t["t_out"], (symbol, t["day"], ft["cas_vystupu"], t["t_out"])
        assert abs(ft["vysledek_proc_marze"] - t["margin_pct"]) <= 0.1 + 1e-9, (symbol, t["day"], ft["vysledek_proc_marze"],
                                                                                 t["margin_pct"])
        checked += 1
        reasons.add(t["reason"])
        sides.add(side)
D._cache.clear()
stack.close()
assert checked >= 15 and {"TP"} <= reasons and len(reasons) >= 2 and sides == {1, -1}, (checked, reasons, sides)

print("=" * 60)
print("H2 ONE CALCULATION OF ENTRY / TARGET / STOP (R-048)")
print("=" * 60)
print("FILL PRICE = MID +/- HALF SPREAD, DISTANCES IN ATR: PASS")
print(f"LIVE PLAN == SIMULATOR (ENTRY, TARGET, STOP; {checked} TRADES, BOTH SIDES, EXITS {sorted(reasons)}): PASS")
print("FORWARD TEST FROM THE PLAN == SIMULATOR (SAME HOUR, SAME REASON, SAME RESULT): PASS")
print("RESULT: PASS")
print("=" * 60)
