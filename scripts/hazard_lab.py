"""Gambling systems in FX (user's question 2026-10-05: "what about martingale and other systems from gambling -
maybe they raise the probability"). Three parts, all printed and pickled to data/research/hazard.pkl:

    python scripts/hazard_lab.py

A  theory: a fair bet and a bet with costs, flat stake vs martingale / d'Alembert / Fibonacci / anti-martingale,
   100 bets per session, 100,000 sessions: the probability that a session ends in profit, the average result,
   the worst result, and the probability of losing half the bankroll.
B  Kelly: the growth-optimal fraction of the account per trade for the live champion's own trades (2012-2022,
   the selection years) vs the margin the model uses.
C  the classic "grid / martingale robot" on hourly FXCM BID/ASK 2012-2026: open a basket, add a position every
   k x daily ATR against it (equal size = averaging down, or x2 = martingale), close the whole basket at a small
   profit; retail costs; the account is closed out by the broker at a margin level of 50 % (ESMA rule), checked
   at every hourly close with the open losses.
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import portfolio_sim as PS  # noqa: E402
import profit_lab2 as P  # noqa: E402
from src.instruments import get_instrument  # noqa: E402

OUT = PROJECT_ROOT / "data" / "research" / "hazard.pkl"


# ----------------------------------------------------------------------
# A: theory
# ----------------------------------------------------------------------

def theory(n_sessions: int = 100_000, n_bets: int = 100, seed: int = 1) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for label, p_win, cost in (("ferova sazka 50 %", 0.5, 0.0), ("sazka s naklady 5 % vkladu", 0.5, 0.05),
                               ("ruleta (18/37)", 18 / 37, 0.0)):
        wins = rng.random((n_sessions, n_bets)) < p_win
        for system in ("flat", "martingale:2:7", "dalembert:1:10", "fibonacci:7", "anti:2:3"):
            bank = np.zeros(n_sessions)
            low = np.zeros(n_sessions)
            staked = np.zeros(n_sessions)
            # vectorised over sessions: keep each session's level array
            level = np.zeros(n_sessions) if system != "dalembert:1:10" else np.ones(n_sessions)
            for b in range(n_bets):
                if system == "flat":
                    stake = np.ones(n_sessions)
                elif system.startswith("martingale"):
                    stake = 2.0 ** level
                elif system.startswith("anti"):
                    stake = 2.0 ** level
                elif system.startswith("dalembert"):
                    stake = level.copy()
                else:
                    stake = np.array(PS.Money.FIB)[level.astype(int)]
                w = wins[:, b]
                bank += np.where(w, stake, -stake) - cost * stake
                staked += stake
                low = np.minimum(low, bank)
                if system.startswith("martingale"):
                    level = np.where(w, 0, np.minimum(level + 1, 7))
                elif system.startswith("anti"):
                    level = np.where(w, np.minimum(level + 1, 3), 0)
                elif system.startswith("dalembert"):
                    level = np.clip(level + np.where(w, -1, 1), 1, 10)
                elif system.startswith("fibonacci"):
                    level = np.where(w, np.maximum(level - 2, 0), np.minimum(level + 1, 7))
            rows.append({"sazka": label, "system": system, "p_zisk": float((bank > 0).mean()),
                         "prumer": float(bank.mean()), "na_vsazenou": float(bank.sum() / staked.sum()),
                         "nejhorsi": float(bank.min()), "p_propad_50": float((low <= -50).mean())})
    return rows


# ----------------------------------------------------------------------
# B: Kelly for the champion's trades
# ----------------------------------------------------------------------

def kelly() -> dict:
    import self_learn as SL
    out = {}
    for prof in ("mesicne", "max"):
        SL.PROFILE = SL.PROFILES[prof]
        st = json.loads(SL.PROFILES[prof]["state"].read_text())
        cfg = st["config"]
        lists = SL.trade_lists(cfg)
        shares = st["eval"]["1"]["shares"]
        r = SL.run_pf(lists, shares, (2012, 2022), cfg)
        R = np.array([t["margin_pct"] / 100 for t in r["trades"]])       # result per unit of margin
        fs = np.linspace(0.01, 1.5, 150)
        g = [np.mean(np.log(np.maximum(1 + f * R, 1e-9))) for f in fs]
        f_star = float(fs[int(np.argmax(g))])
        out[prof] = {"obchodu": len(R), "uspesnost": float((R > 0).mean()), "prumer_marze": float(R.mean()),
                     "nejhorsi_marze": float(R.min()), "kelly_podil_uctu": f_star, "model_podily": shares,
                     "max_vazana_marze": r["max_used"], "max_otevrenych": r["max_open"]}
    return out


# ----------------------------------------------------------------------
# C: grid / martingale robot on hourly prices
# ----------------------------------------------------------------------

def daily_atr(H: dict) -> np.ndarray:
    """ATR(14) of 24-hour ranges known at each hour (computed from completed 24-hour blocks)."""
    mid_h = (H["bh"] + H["ah"]) / 2
    mid_l = (H["bl"] + H["al"]) / 2
    n = len(mid_h)
    out = np.full(n, np.nan)
    blk = 24
    rng = [mid_h[i:i + blk].max() - mid_l[i:i + blk].min() for i in range(0, n - blk, blk)]
    atr = np.convolve(rng, np.ones(14) / 14, mode="valid")
    for k, v in enumerate(atr):
        start = (k + 14) * blk
        out[start:start + blk] = v
    return out


def grid_robot(pair: str, step_atr: float, mult: float, levels: int, tp_atr: float, first_share: float,
               direction: str, rates: dict) -> dict:
    H = U.load(pair)
    inst = get_instrument(pair)
    lev = P.leverage(pair)
    retail = P.SPREAD_PIPS[pair] * inst.pip
    slip = P.SLIPPAGE_PIPS * inst.pip
    bid, ask = H["bc"], H["ac"]
    mid = (bid + ask) / 2
    extra = np.maximum(0.0, retail - (ask - bid)) / 2 + slip / 2
    atr = daily_atr(H)
    ts = H["ts"]
    dt = pd.to_datetime(ts, unit="s", utc=True)
    years, months = np.asarray(dt.year), np.asarray(dt.month)
    equity, peak, max_dd = 1.0, 1.0, 0.0
    basket = []                                   # (side, entry price incl. costs, units = notional / price)
    side = 0
    baskets_won = baskets_lost = stopouts = holes = 0
    opened_at, longest = 0, 0
    first_stopout = None
    curve = []
    for i in range(1, len(ts)):
        if ts[i] - ts[i - 1] > 4 * 86400:         # data hole: the basket stays open (as it would at the broker),
            holes += bool(basket)                  # it is valued again at the next known price
            continue
        if np.isnan(atr[i]):
            continue
        if not basket:
            if direction == "long":
                side = 1
            elif direction == "sazby":
                y, m = int(years[i]), int(months[i])
                v = [P.rate_at(rates[c], y, m, lag) for c in (inst.base, inst.quote) for lag in (2, 5)]
                if None in v:
                    continue
                mom = (v[0] - v[2]) - (v[1] - v[3])
                side = 1 if mom >= 0 else -1
            else:                                  # "proti": against the last 24 hours
                side = -1 if mid[i] > mid[max(i - 24, 0)] else 1
            px = ask[i] + extra[i] if side > 0 else bid[i] - extra[i]
            units = first_share * equity * lev / px
            basket = [(side, px, units)]
            opened_at = int(ts[i])
            continue
        # add to the grid when the price moved one step against the last entry
        last = basket[-1][1]
        step = step_atr * atr[i]
        if len(basket) < levels and ((side > 0 and ask[i] <= last - step) or (side < 0 and bid[i] >= last + step)):
            px = ask[i] + extra[i] if side > 0 else bid[i] - extra[i]
            units = basket[-1][2] * mult
            basket.append((side, px, units))
        # value of the basket at this close
        exit_px = (bid[i] - extra[i]) if side > 0 else (ask[i] + extra[i])
        pnl = sum(u * ((exit_px - e) if s > 0 else (e - exit_px)) for s, e, u in basket)
        used = sum(u * e / lev for _, e, u in basket)
        first_units = basket[0][2]
        target = tp_atr * atr[i] * first_units
        longest = max(longest, int(ts[i]) - opened_at)
        if pnl >= target:
            equity += pnl
            baskets_won += 1
            basket = []
        elif equity + pnl < 0.5 * used:            # ESMA close-out at a margin level of 50 %
            equity += pnl
            stopouts += 1
            baskets_lost += 1
            first_stopout = first_stopout or int(years[i])
            basket = []
            if equity <= 0.01:
                equity = 0.0
                max_dd = 1.0
                curve.append((int(ts[i]), equity))
                break
        mtm = equity + (pnl if basket else 0.0)
        peak = max(peak, mtm)
        max_dd = max(max_dd, 1 - mtm / peak)
        if i % 24 == 0:
            curve.append((int(ts[i]), mtm))
    span = (ts[-1] - ts[0]) / (365.25 * 86400)
    cagr = equity ** (1 / span) - 1 if equity > 0 else -1.0
    done = baskets_won + baskets_lost
    return {"pair": pair, "krok_atr": step_atr, "nasobek": mult, "urovni": levels, "cil_atr": tp_atr,
            "podil": first_share, "smer": direction, "kosu": done, "uspesnych_kosu": baskets_won / done if done else np.nan,
            "nucena_uzavreni": stopouts, "prvni_nucene": first_stopout, "konecny_ucet": equity, "rocne": cagr,
            "max_propad": max_dd, "kos_pres_diru_dat": holes,
            "nejdelsi_kos_dni": longest / 86400, "krivka": curve[::7]}


def main(argv: list[str]) -> int:
    if "--robot" in argv:
        res = pickle.loads(OUT.read_bytes()) if OUT.exists() else {}
        robot_part(res)
        OUT.write_bytes(pickle.dumps(res))
        return 0
    res = {"teorie": theory()}
    print("A) teorie (100 sazek na sezeni, 100 000 sezeni)")
    for r in res["teorie"]:
        print(f"  {r['sazka']:28} {r['system']:16} P(zisk) {r['p_zisk']:6.1%}  prumer {r['prumer']:+7.2f}  "
              f"na vsazene {r['na_vsazenou']:+.3f}  nejhorsi {r['nejhorsi']:+9.0f}  P(propad >= 50) {r['p_propad_50']:6.1%}")
    res["kelly"] = kelly()
    print("B) Kelly", json.dumps(res["kelly"], indent=1, default=float))
    robot_part(res)
    OUT.write_bytes(pickle.dumps(res))
    return 0


def robot_part(res: dict) -> None:
    rates = P.monthly_rates()
    res["robot"] = []
    print("C) mrizkovy / martingale robot, hodinove FXCM 2012-2026 (bez swapu)")
    for pair in ("EUR/USD", "GBP/USD", "USD/JPY", "EUR/GBP", "AUD/USD"):
        for mult in (1.0, 2.0):
            for levels in (5, 8):
                for direction in ("long", "sazby", "proti"):
                    r = grid_robot(pair, 0.5, mult, levels, 0.2, 0.02, direction, rates)
                    res["robot"].append(r)
                    print(f"  {pair} x{mult:.0f} {levels} urovni {direction:6} | kosu {r['kosu']:5d}, uspesnych "
                          f"{r['uspesnych_kosu']:.1%}, nucenych uzavreni {r['nucena_uzavreni']:3d} (prvni {r['prvni_nucene']}), "
                          f"konecny ucet {r['konecny_ucet']:.2f}, rocne {r['rocne']:+.1%}, max propad {r['max_propad']:.0%}, "
                          f"kos nejdele {r['nejdelsi_kos_dni']:.0f} dni", flush=True)
    rb = res["robot"]
    print(f"  souhrn {len(rb)} variant: ucet vyssi nez na zacatku {sum(r['konecny_ucet'] > 1 for r in rb)}, "
          f"znicen (< 10 %) {sum(r['konecny_ucet'] < 0.1 for r in rb)}, propad >= 50 % {sum(r['max_propad'] >= 0.5 for r in rb)}, "
          f"uspesnost kosu prumer {np.nanmean([r['uspesnych_kosu'] for r in rb]):.1%}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
