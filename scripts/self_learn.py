"""Self-learning loop: the model keeps trying improvements on its own and
keeps only those that raise the annual return at the same risk on data the
choice did not see.

    python scripts/self_learn.py                      # profile "max": the largest annual return
    python scripts/self_learn.py --profile mesicne    # ... with >= 2 winning trades every month
    python scripts/self_learn.py --status             # champion and the learning log

State: data/research/profit2/champion.json (the current best configuration)
and docs/UCENI_LOG.md (every experiment, accepted or rejected, with numbers).

A configuration = trading rule (profit_deep.Rule fields) + tiers (overrides,
strongest first) + universe + sizing + portfolio limits. Its tier margins are
always re-fitted on the selection years only (largest annual return with the
max drawdown <= DD_MAX). Two walk-forward splits:
    select 2012-2018 -> test 2019-2022,   select 2012-2022 -> test 2023-2026.
Universe: all 41 pairs (25 FXCM + 16 HistData). Gate: a candidate replaces
the champion only if in BOTH test periods its annual return is higher by
>= MIN_GAIN and its drawdown stays within the risk budget (max(DD_MAX, the
champion's) + DD_SLACK), AND in the
last test period (2023-2026) its trades earn on average > 0 in each market
group separately (G1 = FXCM pairs, G2 = HistData pairs) - a rule must work
also on markets where it was not found (docs/DVA_TRHY.md). Note: each experiment looks at the same test years again, so a
small part of every accepted gain is luck; the forward test (ledger) stays
the final judge. Nothing here trades or touches the production database.
"""

import copy
import itertools
import json
import sys
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402
import profit_lab2 as P  # noqa: E402

CHAMPION = P.OUT / "champion.json"
# learning profiles: "max" = the largest annual return; "mesicne" = the same, but only configurations that
# close >= 2 winning trades a month on average and >= 2 in at least 70 % of the months (the user's condition)
PROFILES = {"max": {"state": P.OUT / "champion.json", "min_wpm": 0.0, "min_m2": 0.0},
            "mesicne": {"state": P.OUT / "champion_mesicne.json", "min_wpm": 2.0, "min_m2": 0.7}}
PROFILE = PROFILES["max"]
LOG = PROJECT_ROOT / "docs" / "UCENI_LOG.md"
SPLITS = (((2012, 2018), (2019, 2022)), ((2012, 2022), (2023, 2026)))
DD_MAX = 0.20
MIN_GAIN = 0.01
DD_SLACK = 0.03
SHARE_STEPS = (0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20)
REF_SL_MARGIN = 84.0                 # median stop of the champion in % of the margin (vol sizing anchor)

START = {                            # CH-009 rule set as pre-registered (docs/CHANGE_LOG.md), on all 41 pairs
    "name": "CH-009 (41 paru)",
    "universe": "all",
    "base": {"signal": "D RSI2<5", "weekly": True, "tp": 0.75, "sl": 3.0, "hold_days": 20},
    "tiers": [{"fund": "rates_up+carry", "rates_thr": 0.25}, {"fund": "rates_up", "rates_thr": 0.25},
              {"fund": "rates_up", "rates_thr": 0.10}, {"fund": "rates_up", "rates_thr": 0.0}],
    "sizing": "flat",
    "max_ccy": None,
}


# ----------------------------------------------------------------------
# evaluation
# ----------------------------------------------------------------------

_trades_cache: dict = {}


def trade_lists(cfg: dict) -> list[list[dict]]:
    symbols = U.universe_all() if cfg.get("universe", "all") == "all" else U.universe()
    out = []
    for tier in cfg["tiers"]:
        fields = {**cfg["base"], **tier}
        key = (tuple(symbols), json.dumps(fields, sort_keys=True))
        if key not in _trades_cache:
            _trades_cache[key] = D.simulate(replace(D.Rule("cfg"), **fields), symbols)
        trades = [dict(t) for t in _trades_cache[key]]
        if cfg["sizing"] == "vol":
            for t in trades:
                t["size_mult"] = float(np.clip(REF_SL_MARGIN / t["sl_pct"], 0.5, 2.0))
        out.append(trades)
    return out


def fit_shares(lists, cfg, years) -> tuple:
    """Tier margins (non-increasing) with the largest annual return at max drawdown <= DD_MAX."""
    best = (-np.inf, None, None)
    n = len(lists)
    steps = SHARE_STEPS if n <= 4 else (0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15)
    for sh in itertools.product(steps, repeat=n):
        if sh[0] == 0 or not all(a >= b for a, b in zip(sh, sh[1:])):
            continue
        if sum(1 for x in sh if x >= 0.12) > 2:      # keep the grid small: few big tiers
            continue
        r = PS.run_portfolio(lists, list(sh), years, cfg.get("max_ccy"))
        if r["wins_month"] < PROFILE["min_wpm"] or r["months_2wins"] < PROFILE["min_m2"]:
            continue
        if r["max_dd"] <= DD_MAX and r["cagr"] > best[0]:
            best = (r["cagr"], sh, r)
    return best


def evaluate(cfg: dict) -> dict:
    lists = trade_lists(cfg)
    out = {}
    for k, (sel, test) in enumerate(SPLITS):
        cagr, sh, r_sel = fit_shares(lists, cfg, sel)
        if sh is None:
            out[k] = None
            continue
        r_test = PS.run_portfolio(lists, list(sh), test, cfg.get("max_ccy"))
        g1 = set(U.universe())
        e_g = {g: [t["margin_pct"] for t in r_test["trades"] if (t["pair"] in g1) == (g == "G1")] for g in ("G1", "G2")}
        out[k] = {"e_G1": float(np.mean(e_g["G1"])) if e_g["G1"] else 0.0,
                  "e_G2": float(np.mean(e_g["G2"])) if e_g["G2"] else 0.0,"shares": sh, "sel_cagr": cagr, "sel_dd": r_sel["max_dd"], "test_cagr": r_test["cagr"],
                  "test_dd": r_test["max_dd"], "test_n_year": r_test["n_year"], "test_win": r_test["win"],
                  "test_wins_month": r_test["wins_month"], "test_months_2wins": r_test["months_2wins"]}
    return out


def better(cand: dict, champ: dict) -> bool:
    for k in range(len(SPLITS)):
        c, h = cand.get(k), champ.get(k)
        if c is None:
            return False
        if h is None:
            continue
        # fixed risk budget: every configuration is sized to the same drawdown limit on its selection years,
        # so in the test it may use that budget (+ DD_SLACK), not only the champion's realised drawdown
        if c["test_cagr"] < h["test_cagr"] + MIN_GAIN or c["test_dd"] > max(DD_MAX, h["test_dd"]) + DD_SLACK:
            return False
        if c["test_wins_month"] < 0.9 * PROFILE["min_wpm"]:
            return False
    last = cand[len(SPLITS) - 1]
    return last["e_G1"] > 0 and last["e_G2"] > 0


# ----------------------------------------------------------------------
# experiments (each takes the current champion and returns a candidate)
# ----------------------------------------------------------------------

def _with(cfg, **changes):
    new = copy.deepcopy(cfg)
    for k, v in changes.items():
        if k in ("signal", "tp", "sl", "hold_days", "max_sl_margin", "min_tp_pct", "rates_lag", "limit_atr"):
            new["base"][k] = v
        else:
            new[k] = v
    return new


def _tiers(cfg, fn):
    new = copy.deepcopy(cfg)
    new["tiers"] = fn(copy.deepcopy(cfg["tiers"]))
    return new


DAILY_LIMIT = {"weekly": False, "limit_atr": 0.5, "sl": 4.0}       # the cross-market robust family (DVA_TRHY.md)

EXPERIMENTS = [
    ("jen_sazby_carry", "jen nejsilnejsi stupen (sazby >= 0.25 + carry) - ostatni na 41 parech neprezily",
     lambda c: _tiers(c, lambda t: t[:1])),
    ("denni_limit_stupne", "pridat stupne: denni limit 0.5 ATR po RSI(2) < 5, sazby >= 0.25 / 0.10, stop 4 ATR",
     lambda c: _tiers(c, lambda t: t + [{**DAILY_LIMIT, "fund": "rates_up", "rates_thr": 0.25},
                                        {**DAILY_LIMIT, "fund": "rates_up", "rates_thr": 0.10}])),
    ("denni_limit_r14", "pridat stupen: denni limit 0.5 ATR po %R14 < 10, sazby >= 0.25, stop 4 ATR",
     lambda c: _tiers(c, lambda t: t + [{**DAILY_LIMIT, "signal": "D %R14<10", "fund": "rates_up",
                                         "rates_thr": 0.25}])),
    ("cil_15_procent", "obchodovat jen kdyz cil >= 15 % marze (volatilnejsi trhy)",
     lambda c: _with(c, min_tp_pct=0.5)),
    ("velikost_podle_volatility", "marze obchodu neprimo umerna sirce stopu (stejne riziko na obchod, 0.5-2x)",
     lambda c: _with(c, sizing="vol")),
    ("limit_meny_3", "nejvyse 3 otevrene obchody dlouhe (kratke) v jedne mene",
     lambda c: _with(c, max_ccy=3)),
    ("limit_meny_2", "nejvyse 2 otevrene obchody dlouhe (kratke) v jedne mene",
     lambda c: _with(c, max_ccy=2)),
    ("bez_extremnich_stopu", "neobchodovat, kdyz stop > 150 % marze (extremni volatilita)",
     lambda c: _with(c, max_sl_margin=150.0)),
    ("slabe_stupne_i_rsi3", "slabsi stupne (2 posledni) berou i signal RSI(3) < 15",
     lambda c: _tiers(c, lambda t: t[:-2] + [{**x, "signal": "D RSI2<5|D RSI3<15"} for x in t[-2:]])),
    ("drzeni_10_dni", "nejdele 10 obchodnich dni misto 20", lambda c: _with(c, hold_days=10)),
    ("tp_1_atr", "cil 1.0 ATR misto 0.75", lambda c: _with(c, tp=1.0)),
    ("stop_4_atr", "stop 4 ATR misto 3", lambda c: _with(c, sl=4.0)),
    ("stupen_carry_bez_sazeb", "dalsi nejslabsi stupen: jen carry ve smeru obchodu (sazby se nemeni)",
     lambda c: _tiers(c, lambda t: t + [{"fund": "carry", "rates_thr": 0.25}])),
    ("stupen_sazby_cb", "dalsi stupen: totez se sazbami centralnich bank (o 2 mesice zpet) misto OECD",
     lambda c: _tiers(c, lambda t: t + [{**t[0], "rates_src": "policylag"}])),
    ("signal_i_rsi3", "nejsilnejsi stupen bere i signal RSI(3) < 15",
     lambda c: _tiers(c, lambda t: [{**t[0], "signal": "D RSI2<5|D RSI3<15"}] + t[1:])),
    ("signal_i_r14", "nejsilnejsi stupen bere i signal %R14 < 10",
     lambda c: _tiers(c, lambda t: [{**t[0], "signal": "D RSI2<5|D %R14<10"}] + t[1:])),
    ("prah_sazeb_015", "nejsilnejsi stupen: zmena sazeb >= 0.15 p.b. misto 0.25",
     lambda c: _tiers(c, lambda t: [{**t[0], "rates_thr": 0.15}] + t[1:])),
    ("patek_limit_05", "patecni vstup limitem 0.5 ATR pod zaverem (platny tyden) misto trhu",
     lambda c: _tiers(c, lambda t: [{**t[0], "limit_atr": 0.5}] + t[1:])),
    ("denni_sazby_carry", "dalsi stupen: denni limit 0.5 ATR po RSI(2) < 5 se sazbami >= 0.25 + carry",
     lambda c: _tiers(c, lambda t: t + [{**DAILY_LIMIT, "fund": "rates_up+carry", "rates_thr": 0.25}])),
    ("vix_pod_30", "neotevirat, kdyz je VIX nad 30 (panika na trzich)",
     lambda c: _tiers(c, lambda t: [{**x, "max_vix": 30.0} for x in t])),
    ("vix_pod_25", "neotevirat, kdyz je VIX nad 25",
     lambda c: _tiers(c, lambda t: [{**x, "max_vix": 25.0} for x in t])),
    ("vix_bez_skoku", "neotevirat, kdyz VIX za 5 dni vzrostl o vic nez 5 bodu",
     lambda c: _tiers(c, lambda t: [{**x, "max_vix_rise": 5.0} for x in t])),
]


# ----------------------------------------------------------------------
# log
# ----------------------------------------------------------------------

def _fmt(ev: dict) -> str:
    parts = []
    if not ev:
        return "-"
    for k, (sel, test) in enumerate(SPLITS):
        e = ev.get(k)
        if e is None:
            parts.append(f"{test[0]}-{test[1] % 100:02d}: -")
            continue
        parts.append(f"{test[0]}-{test[1] % 100:02d}: **{e['test_cagr']:+.1%}** rocne, propad {e['test_dd']:.0%}, "
                     f"{e['test_wins_month']:.1f} ziskovych/mesic "
                     f"(marze {' / '.join(f'{x:.0%}' for x in e['shares'])})")
    return "; ".join(parts)


def log(lines: list[str]) -> None:
    if not LOG.exists():
        LOG.write_text("# Denik uceni modelu\n\n_Kazdy pokus o zlepseni: co se zkousi, vysledek ve dvou testovacich "
                       "obdobich (vyber velikosti vzdy jen na starsich datech) a rozhodnuti. Prijato jen, kdyz roste "
                       f"rocni vynos o >= {MIN_GAIN:.0%} v obou testech a propad se nezhorsi o vic nez {DD_SLACK:.0%}._\n\n",
                       encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    global PROFILE
    name = argv[argv.index("--profile") + 1] if "--profile" in argv else "max"
    PROFILE = PROFILES[name]
    CHAMPION = PROFILE["state"]
    state = json.loads(CHAMPION.read_text()) if CHAMPION.exists() else {"config": START, "eval": None, "tried": []}
    if "--status" in argv:
        print(json.dumps(state["config"], indent=1, ensure_ascii=False))
        print(LOG.read_text() if LOG.exists() else "(zatim zadny pokus)")
        return 0
    started = time.monotonic()
    if state["eval"] is None:
        state["eval"] = {str(k): v for k, v in evaluate(state["config"]).items()}
        log([f"## {date.today()} - profil {name}: vychozi sampion {state['config']['name']}", "",
             _fmt({int(k): v for k, v in state["eval"].items()}), ""])
    for exp, text, make in EXPERIMENTS:
        if exp in state["tried"]:
            continue
        champ_eval = {int(k): v for k, v in state["eval"].items()}
        cand = make(state["config"])
        cand["name"] = f"{state['config']['name']} + {exp}"
        ev = evaluate(cand)
        ok = better(ev, champ_eval)
        log([f"### {date.today()} - [{PROFILE['state'].stem}] {exp}: {'PRIJATO' if ok else 'zamitnuto'}", "", f"* {text}",
             f"* kandidat: {_fmt(ev)}", f"* sampion:  {_fmt(champ_eval)}", ""])
        print(f"{exp}: {'PRIJATO' if ok else 'zamitnuto'} | {_fmt(ev)} | {time.monotonic() - started:.0f} s", flush=True)
        state["tried"].append(exp)
        if ok:
            state["config"], state["eval"] = cand, {str(k): v for k, v in ev.items()}
        CHAMPION.write_text(json.dumps(state, indent=1, ensure_ascii=False, default=list))
    print(f"sampion: {state['config']['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
