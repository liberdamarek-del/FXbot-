"""Self-learning loop: the model keeps trying improvements on its own and
keeps only those that raise the annual return at the same risk on data the
choice did not see.

    python scripts/self_learn.py                      # profile "max": the largest annual return
    python scripts/self_learn.py --profile mesicne    # ... with >= 2 winning trades every month
    python scripts/self_learn.py --status             # champion and the learning log

State: learning/champion_12.json and learning/champion_12_mesicne.json (the
current best configuration per profile, tracked in git) and docs/UCENI_LOG.md
(every experiment, accepted or rejected, with numbers). The champion is
re-evaluated when the price data reach a new day (the weekly download), so a
candidate is always compared with the champion on the same data.

A configuration = trading rule (profit_deep.Rule fields) + tiers (overrides,
strongest first) + universe + sizing + portfolio limits. Its tier margins are
always re-fitted on the selection years only (largest annual return with the
max drawdown <= DD_MAX). Two walk-forward splits:
    select 2012-2018 -> test 2019-2022,   select 2012-2022 -> test 2023-2026.
Universe: the 12 pairs the bot follows live (DEFAULT_ACTIVE, FXCM hourly
2012-2026; the 41-pair runs of R-010 are kept in the log). Gate: a candidate replaces
the champion only if in BOTH test periods its annual return is higher by
>= MIN_GAIN and its drawdown stays within the risk budget (max(DD_MAX, the
champion's) + DD_SLACK), AND in the
last test period (2023-2026) its trades earn on average > 0 in each market
group separately (12 pairs: G1 = the 7 USD pairs, G2 = the 5 crosses). Note: each experiment looks at the same test years again, so a
small part of every accepted gain is luck; the forward test (ledger) stays
the final judge. Nothing here trades or touches the production database.
"""

import copy
from collections import defaultdict
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
from src.instruments import DEFAULT_ACTIVE  # noqa: E402

# learning profiles: "max" = the largest annual return; "mesicne" = the same, but only configurations that
# close >= 2 winning trades a month on average and >= 2 in at least 70 % of the months (the user's condition)
# since 2026-10-01 (user's decision) only the 12 pairs the bot follows live; the 41-pair states stay as
# champion.json / champion_mesicne.json for the record
LEARNING = PROJECT_ROOT / "learning"                     # tracked in git: survives between sessions
PROFILES = {"max": {"state": LEARNING / "champion_12.json", "min_wpm": 0.0, "min_m2": 0.0},
            "mesicne": {"state": LEARNING / "champion_12_mesicne.json", "min_wpm": 2.0, "min_m2": 0.7}}
PROFILE = PROFILES["max"]
LOG = PROJECT_ROOT / "docs" / "UCENI_LOG.md"
SPLITS = (((2012, 2018), (2019, 2022)), ((2012, 2022), (2023, 2026)))
DD_MAX = 0.20
MIN_GAIN = 0.01
DD_SLACK = 0.03
EVAL_VERSION = 2                     # 2: drawdown with open trades at daily closes, 2-year blocks in the test
BLOCKS = (((2019, 2020), (2021, 2022)), ((2023, 2024), (2025, 2026)))   # 2-year blocks of each test period
MIN_BLOCKS = 3                       # the candidate must be at least as good in >= 3 of the 4 blocks
SHARE_STEPS = (0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20)
REF_SL_MARGIN = 84.0                 # median stop of the champion in % of the margin (vol sizing anchor)

START = {                            # CH-009 rule set as pre-registered (docs/CHANGE_LOG.md), on the 12 pairs
    "name": "CH-009 (12 paru)",
    "universe": "12",
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


def symbols_of(cfg: dict) -> list[str]:
    universe = cfg.get("universe", "12")
    if universe == "all":
        return U.universe_all()
    if universe == "fxcm":
        return U.universe()
    return [p for p in U.universe() if p in DEFAULT_ACTIVE]         # the 12 live pairs


def group_one(cfg: dict) -> set:
    """First of the two market groups of the gate: 12 pairs -> the 7 USD pairs
    (the 5 crosses are the second group); 41 pairs -> the 25 FXCM pairs."""
    if cfg.get("universe", "12") in ("all", "fxcm"):
        return set(U.universe())
    return {p for p in symbols_of(cfg) if "USD" in p}


def trade_lists(cfg: dict) -> list[list[dict]]:
    symbols = symbols_of(cfg)
    out = []
    for tier in cfg["tiers"]:
        fields = {**cfg["base"], **tier}
        syms = [p for p in symbols if p in fields.pop("pairs", symbols)]     # a tier may be limited to some pairs
        key = (tuple(syms), json.dumps(fields, sort_keys=True))
        if key not in _trades_cache:
            _trades_cache[key] = D.simulate(replace(D.Rule("cfg"), **fields), syms)
        trades = [dict(t) for t in _trades_cache[key]]
        if cfg["sizing"] == "vol":
            for t in trades:
                t["size_mult"] = float(np.clip(REF_SL_MARGIN / t["sl_pct"], 0.5, 2.0))
        out.append(trades)
    if cfg.get("recent"):
        out = recent_filter(out, *cfg["recent"])
    for addon in cfg.get("addons", []):                 # extra trade generators (their own margin share)
        if addon == "fomc":
            out.append([dict(t) for t in D.fomc_addon(symbols)])
    return out


def recent_filter(lists: list[list[dict]], months: float, floor: float) -> list[list[dict]]:
    """Short-window adaptation (user's idea 2026-10-02): skip a trade when the rule's trades on the same
    pair that CLOSED in the last `months` before this entry earned on average < floor % of the margin
    (at least 2 of them; only results known at the entry are used)."""
    closed = defaultdict(list)
    for tl in lists:
        for t in tl:
            closed[t["pair"]].append((t["t_out"], t["margin_pct"]))
    for v in closed.values():
        v.sort()
    span = months * 30.4 * 86400
    out = []
    for tl in lists:
        keep = []
        for t in tl:
            prev = [m for when, m in closed[t["pair"]] if t["t_in"] - span <= when <= t["t_in"]]
            if len(prev) >= 2 and np.mean(prev) < floor:
                continue
            keep.append(t)
        out.append(keep)
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
        if sh[0] > cfg.get("max_share", 1.0):         # optional risk cap on the margin per trade
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
        g1 = group_one(cfg)
        e_g = {g: [t["margin_pct"] for t in r_test["trades"] if (t["pair"] in g1) == (g == "G1")] for g in ("G1", "G2")}
        out[k] = {"e_G1": float(np.mean(e_g["G1"])) if e_g["G1"] else 0.0,
                  "e_G2": float(np.mean(e_g["G2"])) if e_g["G2"] else 0.0,"shares": sh, "sel_cagr": cagr, "sel_dd": r_sel["max_dd"], "test_cagr": r_test["cagr"],
                  "test_dd": r_test["max_dd"], "test_n_year": r_test["n_year"], "test_win": r_test["win"],
                  "test_wins_month": r_test["wins_month"], "test_months_2wins": r_test["months_2wins"],
                  "blocks": [PS.run_portfolio(lists, list(sh), b, cfg.get("max_ccy"))["cagr"] for b in BLOCKS[k]]}
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
    # robustness (from 2026-10-02, many more experiments a week): the gain must not come from one lucky
    # stretch - at least as good as the champion in >= MIN_BLOCKS of the 2-year blocks of the tests
    pairs = [(c, h) for k in range(len(SPLITS)) if champ.get(k) and "blocks" in champ[k]
             for c, h in zip(cand[k]["blocks"], champ[k]["blocks"])]
    if pairs and sum(c >= h for c, h in pairs) < MIN_BLOCKS:
        return False
    last = cand[len(SPLITS) - 1]
    return last["e_G1"] > 0 and last["e_G2"] > 0


# ----------------------------------------------------------------------
# experiments (each takes the current champion and returns a candidate)
# ----------------------------------------------------------------------

def _with(cfg, **changes):
    new = copy.deepcopy(cfg)
    for k, v in changes.items():
        if k in ("signal", "tp", "sl", "hold_days", "max_sl_margin", "min_tp_pct", "rates_lag", "limit_atr",
                 "be_atr", "stall_days", "exit_before_cb", "vix_size"):
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
    # round 3 (2026-10-01): exits, confirmation, crowding, trend for the weak tiers
    ("stop_na_vstup_05", "po pohybu 0.5 ATR ve smeru obchodu se stop posune na vstupni cenu",
     lambda c: _with(c, be_atr=0.5)),
    ("stop_na_vstup_06", "po pohybu 0.6 ATR ve smeru obchodu se stop posune na vstupni cenu",
     lambda c: _with(c, be_atr=0.6)),
    ("stoji_5_dni", "kdyz obchod po 5 obchodnich dnech neni v zisku, zavrit",
     lambda c: _with(c, stall_days=5)),
    ("stoji_10_dni", "kdyz obchod po 10 obchodnich dnech neni v zisku, zavrit",
     lambda c: _with(c, stall_days=10)),
    ("potvrzeni_sazeb_cb", "novy nejvyssi stupen: nejsilnejsi signal + sazby centralnich bank ukazuji stejnym smerem",
     lambda c: _tiers(c, lambda t: [{**t[0], "confirm_src": "policylag"}] + t)),
    ("cot_neprehustene", "neobchodovat, kdyz jsou spekulanti (COT) presyceni ve smeru obchodu (rozdil z > 1)",
     lambda c: _tiers(c, lambda t: [{**x, "max_cot": 1.0} for x in t])),
    ("trend_slabe_stupne", "slabsi stupne jen ve smeru trendu (SMA200)",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "trend": "sma200"} for x in t[2:]])),
    ("slabe_rsi3_i_r14", "slabsi stupne berou i signaly RSI(3) < 15 a %R14 < 10",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "signal": "D RSI2<5|D RSI3<15|D %R14<10"} for x in t[2:]])),
    ("druhy_stupen_rsi3", "druhy stupen (sazby >= 0.25 bez carry) bere i RSI(3) < 15",
     lambda c: _tiers(c, lambda t: t[:1] + [{**t[1], "signal": "D RSI2<5|D RSI3<15"}] + t[2:])),
    # round 4 (2026-10-02): news - scheduled central bank decisions, US data, news shocks (docs/ZPRAVY.md:
    # trades entered <= 7 days before a decision of either currency's central bank earned less in all periods)
    ("zpravy_cb_7_dni", "neotevirat, kdyz centralni banka jedne z men rozhoduje do 7 dni (Fed, ECB, BoJ, BoE)",
     lambda c: _tiers(c, lambda t: [{**x, "skip_cb_ahead": 7} for x in t])),
    ("zpravy_cb_5_dni", "neotevirat, kdyz centralni banka jedne z men rozhoduje do 5 dni",
     lambda c: _tiers(c, lambda t: [{**x, "skip_cb_ahead": 5} for x in t])),
    ("zpravy_cb_10_dni", "neotevirat, kdyz centralni banka jedne z men rozhoduje do 10 dni",
     lambda c: _tiers(c, lambda t: [{**x, "skip_cb_ahead": 10} for x in t])),
    ("zpravy_cb_7_slabe", "jen slabsi stupne: neotevirat 7 dni pred rozhodnutim centralni banky",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "skip_cb_ahead": 7} for x in t[2:]])),
    ("zpravy_us_data", "pary s USD: neotevirat v tydnu, kdy vysly NFP nebo CPI",
     lambda c: _tiers(c, lambda t: [{**x, "skip_us_data": True} for x in t])),
    ("zpravy_skok_075", "neotevirat po zpravovem skoku (hodina za posledni 2 dny > 0.75 ATR)",
     lambda c: _tiers(c, lambda t: [{**x, "max_jump_atr": 0.75} for x in t])),
    ("zpravy_cb_7_polovina", "7 dni pred rozhodnutim centralni banky jedne z men jen polovicni pozice (obchodu stejne)",
     lambda c: _tiers(c, lambda t: [{**x, "cb_size": 0.5} for x in t])),
    ("zpravy_cb_7_polovina_slabe", "jen slabsi stupne: 7 dni pred rozhodnutim centralni banky polovicni pozice",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "cb_size": 0.5} for x in t[2:]])),
    # round 5 (2026-10-02 morning): after a decision the uncertainty is gone (docs/ZPRAVY.md: trades entered in a
    # week with a decision earned at least as much in every period); carry pays the swap over 20 days
    ("zpravy_po_rozhodnuti_vetsi", "kdyz centralni banka jedne z men rozhodla v tydnu vstupu, pozice 1.5x vetsi",
     lambda c: _tiers(c, lambda t: [{**x, "cb_week_size": 1.5} for x in t])),
    ("slabe_stupne_s_carry", "slabsi stupne jen s kladnym urokovym rozdilem ve smeru obchodu (swap pro nas)",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "fund": "rates_up+carry"} for x in t[2:]])),
    ("zpravy_pred_polovina_po_vetsi", "pred rozhodnutim centralni banky polovicni pozice, po rozhodnuti 1.5x vetsi",
     lambda c: _tiers(c, lambda t: [{**x, "cb_size": 0.5, "cb_week_size": 1.5} for x in t])),
    # round 6 (2026-10-02, user's idea): indicators valid only for a short time -> trade a pair only while
    # the rule worked on it recently (closed trades of the last 3 / 6 / 12 months, average >= 0)
    ("adaptivni_par_3m", "par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 3 mesice",
     lambda c: _with(c, recent=[3, 0.0])),
    ("adaptivni_par_6m", "par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 6 mesicu",
     lambda c: _with(c, recent=[6, 0.0])),
    ("adaptivni_par_12m", "par se obchoduje, jen kdyz pravidlu na nem vychazelo poslednich 12 mesicu",
     lambda c: _with(c, recent=[12, 0.0])),
    # round 7 (2026-10-02 noon, from docs/KRATKE_OKNO.md / PROC_SE_TRHY_HYBOU.md): risk currencies revert against
    # the 5-day equity move; EUR/GBP is the most mean-reverting pair; event risk before a decision
    ("riziko_proti_akciim_5d", "rizikove meny (AUD, NZD, CAD proti JPY, CHF) kupovat jen po 5dennim poklesu S&P 500, "
     "prodavat jen po rustu", lambda c: _tiers(c, lambda t: [{**x, "risk_contra": 5} for x in t])),
    ("eurgbp_navrat_stupen", "novy slaby stupen jen pro EUR/GBP: navrat po propadu RSI(2) < 5 bez filtru sazeb",
     lambda c: _tiers(c, lambda t: t + [{"fund": None, "signal": "D RSI2<5|D RSI3<15", "pairs": ["EUR/GBP"]}])),
    ("zavrit_pred_cb_zisk", "obchod v zisku zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men",
     lambda c: _with(c, exit_before_cb="zisk")),
    ("zavrit_pred_cb_vzdy", "kazdy obchod zavrit pri zavreni dne pred rozhodnutim centralni banky jedne z men",
     lambda c: _with(c, exit_before_cb="vzdy")),
    # round 8 (2026-10-02 afternoon, literature, docs/ANOMALIE.md): FOMC-day dollar weakness (Mueller,
    # Tahbaz-Salehi, Vedolin 2017, J. Finance), volatility-managed sizing (Moreira, Muir 2017, J. Finance)
    ("fomc_doplnek", "doplnek: v den rozhodnuti Fedu proti dolaru (7 paru s USD), od zavreni den predem do zavreni",
     lambda c: {**copy.deepcopy(c), "addons": c.get("addons", []) + ["fomc"]}),
    ("velikost_podle_vix", "velikost pozice 17 / VIX (vic pri klidu, mene pri strachu, 0.5-1.5x)",
     lambda c: _with(c, vix_size=True)),
    ("zavrit_long_usd_pred_fomc", "obchod sazejici na dolar zavrit pri zavreni dne pred rozhodnutim Fedu",
     lambda c: _with(c, exit_before_cb="fed_long_usd")),
    ("zavrit_pred_cb_zisk_silne", "jen silne stupne: obchod v zisku zavrit den pred rozhodnutim centralni banky",
     lambda c: _tiers(c, lambda t: [{**x, "exit_before_cb": "zisk"} for x in t[:2]] + t[2:])),
    # the exit raises the return in both profiles, but the fitted margins grow to 20 % and the 2023-26
    # drawdown breaks the limit: the same exit with the margin per trade capped at today's level
    ("zavrit_pred_cb_zisk_marze15", "obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 15 % na obchod",
     lambda c: {**_with(c, exit_before_cb="zisk"), "max_share": 0.15}),
    ("zavrit_pred_cb_zisk_marze12", "obchod v zisku zavrit den pred rozhodnutim centralni banky; marze nejvys 12 % na obchod",
     lambda c: {**_with(c, exit_before_cb="zisk"), "max_share": 0.12}),
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
                     f"(marze {' / '.join(f'{x:.0%}' for x in e['shares'])})"
                     + (f", po 2 letech {' / '.join(f'{b:+.0%}' for b in e['blocks'])}" if "blocks" in e else ""))
    return "; ".join(parts)


def data_mark(cfg: dict) -> str:
    """Last trading day of the price data, last month of every rate series and
    the evaluation version: when one changes, the champion is evaluated again."""
    rates = P.monthly_rates()
    last_rates = ",".join(f"{c}{max(v)[0]}-{max(v)[1]:02d}" for c, v in sorted(rates.items()) if v)
    return f"{max(P.series(s)['days'][-1] for s in symbols_of(cfg))} | {last_rates} | v{EVAL_VERSION}"


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
    mark = data_mark(state["config"])
    if state["eval"] is None or state.get("data_do") != mark:
        state["eval"] = {str(k): v for k, v in evaluate(state["config"]).items()}
        state["data_do"] = mark
        log([f"## {date.today()} - profil {name}: sampion {state['config']['name']} na datech do {mark}", "",
             _fmt({int(k): v for k, v in state["eval"].items()}), ""])
        CHAMPION.write_text(json.dumps(state, indent=1, ensure_ascii=False, default=list))
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
