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
EVAL_VERSION = 3                     # 2: drawdown with open trades at daily closes, 2-year blocks in the test
                                     # 3: blocks with drawdown; risk-adjusted gate (user's decision 2026-10-02)
MIN_CALMAR_GAIN = 0.10               # gate v3: return per drawdown (CAGR / max dd) better by >= 10 % in both tests
MIN_RETURN_KEEP = 0.85               # ... while keeping >= 85 % of the champion's annual return
DD_CAP = 0.30                        # ... and a test drawdown of at most 30 %
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
    if cfg.get("cluster"):
        cluster_sizing(out, cfg["cluster"])
    for addon in cfg.get("addons", []):                 # extra trade generators (their own margin share)
        if addon == "fomc":
            out.append([dict(t) for t in D.fomc_addon(symbols)])
    if cfg.get("scale_in"):                             # [k_atr, number of tiers]: scale-in orders join their tier
        k_atr, n_tiers = cfg["scale_in"]
        base = cfg["base"]
        for r in range(min(n_tiers, len(out))):
            key = ("scale", k_atr, json.dumps(base, sort_keys=True), r, len(out[r]), out[r][0]["t_in"] if out[r] else 0)
            if key not in _trades_cache:
                _trades_cache[key] = D.scale_addon(out[r], k_atr, base.get("tp", 0.75), base.get("sl", 4.0),
                                                   base.get("hold_days", 20), base.get("exit_before_cb", ""))
            adds = [dict(t) for t in _trades_cache[key]]
            if cfg["sizing"] == "vol":
                for t in adds:
                    t["size_mult"] = float(np.clip(REF_SL_MARGIN / t["sl_pct"], 0.5, 2.0))
            out[r] = sorted(out[r] + adds, key=lambda t: t["t_in"])
    return out


def cluster_sizing(lists: list[list[dict]], mode: str) -> None:
    """Several signals of one Friday that buy (or sell) the same currency are one bet on that currency
    (a trader sizes them as one): each trade's size is divided by the number of distinct pairs signalled
    at the same close that share its bought or its sold currency ("n") or by its square root ("sqrt")."""
    by_time = defaultdict(set)
    for tl in lists:
        for t in tl:
            by_time[t["t_in"]].add((t["pair"], t["side"]))
    for tl in lists:
        for t in tl:
            legs = [PS._legs({"pair": p, "side": sd}) for p, sd in by_time[t["t_in"]]]
            bought, sold = PS._legs(t)
            n = max(sum(1 for b, _ in legs if b == bought), sum(1 for _, q in legs if q == sold), 1)
            t["size_mult"] = t.get("size_mult", 1.0) / (n if mode == "n" else np.sqrt(n))


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
        r = PS.run_portfolio(lists, list(sh), years, cfg.get("max_ccy"), cfg.get("brake"))
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
        r_test = PS.run_portfolio(lists, list(sh), test, cfg.get("max_ccy"), cfg.get("brake"))
        g1 = group_one(cfg)
        e_g = {g: [t["margin_pct"] for t in r_test["trades"] if (t["pair"] in g1) == (g == "G1")] for g in ("G1", "G2")}
        out[k] = {"e_G1": float(np.mean(e_g["G1"])) if e_g["G1"] else 0.0,
                  "e_G2": float(np.mean(e_g["G2"])) if e_g["G2"] else 0.0,"shares": sh, "sel_cagr": cagr, "sel_dd": r_sel["max_dd"], "test_cagr": r_test["cagr"],
                  "test_dd": r_test["max_dd"], "test_n_year": r_test["n_year"], "test_win": r_test["win"],
                  "test_wins_month": r_test["wins_month"], "test_months_2wins": r_test["months_2wins"],
                  "blocks": [[r["cagr"], r["max_dd"]] for r in
                             (PS.run_portfolio(lists, list(sh), b, cfg.get("max_ccy"), cfg.get("brake")) for b in BLOCKS[k])]}
    return out


def calmar(cagr: float, dd: float) -> float:
    return cagr / max(dd, 0.05)


def better(cand: dict, champ: dict) -> bool:
    """Gate v3 (user's decision 2026-10-02: compare return per risk, not raw return). In BOTH tests:
    CAGR / max drawdown better by >= MIN_CALMAR_GAIN, CAGR >= MIN_RETURN_KEEP x the champion's, drawdown
    <= DD_CAP, the profile's wins a month; at least as good (CAGR / dd) in >= MIN_BLOCKS of the 4 two-year
    blocks; positive average trade in both market groups in 2023-2026."""
    for k in range(len(SPLITS)):
        c, h = cand.get(k), champ.get(k)
        if c is None:
            return False
        if h is None:
            continue
        if c["test_cagr"] <= 0 or c["test_dd"] > DD_CAP:
            return False
        if calmar(c["test_cagr"], c["test_dd"]) < (1 + MIN_CALMAR_GAIN) * calmar(h["test_cagr"], h["test_dd"]):
            return False
        if c["test_cagr"] < MIN_RETURN_KEEP * h["test_cagr"]:
            return False
        if c["test_wins_month"] < 0.9 * PROFILE["min_wpm"]:
            return False
    pairs = [(calmar(*cb), calmar(*hb)) for k in range(len(SPLITS)) if champ.get(k) and cand.get(k)
             for cb, hb in zip(cand[k]["blocks"], champ[k]["blocks"])]
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
                 "be_atr", "stall_days", "exit_before_cb", "vix_size", "tp_parts", "knife_days",
                 "exit_before_us", "exit_friday_profit", "cb_all", "confirm_up", "tp_retrace", "decay_days", "decay_tp", "close_stop"):
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
    # round 10 (2026-10-02 evening): gate v3 (return per drawdown, user's decision) and a trader's logic
    ("v3_zavrit_pred_cb_zisk", "obchod v zisku zavrit den pred rozhodnutim centralni banky (znovu, brana v3)",
     lambda c: _with(c, exit_before_cb="zisk")),
    ("v3_zavrit_pred_cb_zisk_marze15", "totez s marzi nejvys 15 % na obchod (brana v3)",
     lambda c: {**_with(c, exit_before_cb="zisk"), "max_share": 0.15}),
    ("v3_polovina_pred_cb", "7 dni pred rozhodnutim centralni banky polovicni pozice (znovu, brana v3)",
     lambda c: _tiers(c, lambda t: [{**x, "cb_size": 0.5} for x in t])),
    ("tri_cile", "pozice na 3 casti s cili 0.75 / 1.0 / 1.5 ATR (vybrat zisk postupne)",
     lambda c: _with(c, tp_parts=(0.75, 1.0, 1.5))),
    ("tri_cile_nechat_bezet", "pozice na 3 casti s cili 0.75 / 1.5 / 3.0 ATR (cast nechat bezet)",
     lambda c: _with(c, tp_parts=(0.75, 1.5, 3.0))),
    ("padajici_nuz_20", "nekupovat zaviraci cenu, ktera je nejnizsi za 20 dni (neprodavat nejvyssi)",
     lambda c: _with(c, knife_days=20)),
    ("silny_stupen_denne", "nejsilnejsi stupen se vyhodnocuje kazdy den, ne jen v patek (vic obchodu)",
     lambda c: _tiers(c, lambda t: [{**t[0], "weekly": False}] + t[1:])),
    ("silne_stupne_denne", "oba silne stupne se vyhodnocuji kazdy den",
     lambda c: _tiers(c, lambda t: [{**x, "weekly": False} for x in t[:2]] + t[2:])),
    # round 11: take profit before other risk events (the exit before decisions worked)
    ("zavrit_pred_us_data_zisk", "pary s USD: obchod v zisku zavrit den pred zpravou NFP nebo CPI",
     lambda c: _with(c, exit_before_us=True)),
    ("zavrit_v_zisku_patek", "obchod v zisku zavrit v patek pri zavreni (riziko vikendove mezery)",
     lambda c: _with(c, exit_friday_profit=True)),
    # round 12 (2026-10-02 17:40 learning run): the accepted exit before decisions also for the Swiss (SNB,
    # quarterly) and Australian (RBA) central banks - CHF pairs (USD/CHF, EUR/CHF), AUD pairs (AUD/USD, AUD/JPY)
    ("zavrit_pred_cb_zisk_i_snb_rba", "obchod v zisku zavrit den pred rozhodnutim i SNB (CHF) a RBA (AUD)",
     lambda c: _with(c, exit_before_cb="zisk", cb_all=True)),
    # round 13 (2026-10-02 night, trader's logic; docs/OBCHODNIK.md: the losers have no common pattern at the entry
    # except weak rate support - the strongest rate change (> 0.35 p.b.) won 97-99 % in all three periods)
    ("dokup_15_atr", "dokoupit stejnou pozici, kdyz cena jde o dalsich 1.5 ATR proti (lepsi prumerna cena), "
     "cil dokupu 0.75 ATR, stop stejny", lambda c: _with(c, scale_in=[1.5, 4])),
    ("dokup_2_atr_silne", "jen silne stupne: dokoupit o 2 ATR niz, cil dokupu 0.75 ATR, stop stejny",
     lambda c: _with(c, scale_in=[2.0, 2])),
    ("potvrzeni_obratu_3d", "vstoupit az pri prvnim zavreni ve smeru obchodu (do 3 dni po signalu), ne do padajici ceny",
     lambda c: _with(c, confirm_up=3)),
    ("jedna_sazka_na_menu", "vic signalu stejneho dne na stejnou menu = jedna sazka: velikost deleno odmocninou poctu",
     lambda c: _with(c, cluster="sqrt")),
    ("stupen_sazby_04", "novy nejsilnejsi stupen: zmena sazeb >= 0.40 p.b. (99 % vyher), nejslabsi stupen (sazby >= 0) pryc",
     lambda c: _tiers(c, lambda t: [{**t[0], "fund": "rates_up", "rates_thr": 0.40}] + t[:-1])),
    # round 14: target, stop and holding again on top of the exit before decisions (the optimum may have moved;
    # the user accepts short trades with small profits)
    ("cil_06_atr", "cil 0.6 ATR misto 0.75 (rychlejsi mensi zisky, casteji)", lambda c: _with(c, tp=0.6)),
    ("cil_05_atr", "cil 0.5 ATR misto 0.75", lambda c: _with(c, tp=0.5)),
    ("stop_5_atr", "stop 5 ATR misto 4", lambda c: _with(c, sl=5.0)),
    ("drzeni_30_dni", "nejdele 30 obchodnich dni misto 20", lambda c: _with(c, hold_days=30)),
    ("cil_40_procent_poklesu", "cil = 40 % poklesu za 5 dni (0.5-1.5 ATR): po hlubsim propadu vetsi odraz",
     lambda c: _with(c, tp_retrace=0.4)),
    # round 15: the end-of-week effect (scratch analysis 2026-10-02: the strongest tier entered at a Thursday close
    # earned +0.18 / +0.08 / +0.10 R per trade in 2012-18 / 2019-22 / 2023-26, Friday +0.16 / +0.14 / +0.11,
    # Monday-Wednesday only +0.03..+0.14 and 82-91 % wins): position squaring before the weekend starts on Thursday
    ("ctvrtek_i_patek_silny", "nejsilnejsi stupen se vyhodnocuje ve ctvrtek i v patek (vic obchodu)",
     lambda c: _tiers(c, lambda t: [{**t[0], "weekdays": (3, 4)}] + t[1:])),
    ("ctvrtek_i_patek_silne", "oba silne stupne se vyhodnocuji ve ctvrtek i v patek",
     lambda c: _tiers(c, lambda t: [{**x, "weekdays": (3, 4)} for x in t[:2]] + t[2:])),
    # round 16 (champion's trades: the winners reach the target in 3.9 days (median), 90 % within 12.8; the
    # stop-loss trades first rose 0.33 ATR (median, a quarter > 0.52) and fell to the stop after 14 days):
    # a late bounce is taken smaller
    ("pozdni_cil_5d_035", "po 5 dnech bez cile se cil snizi na 0.35 ATR", lambda c: _with(c, decay_days=5, decay_tp=0.35)),
    ("pozdni_cil_10d_025", "po 10 dnech bez cile se cil snizi na 0.25 ATR", lambda c: _with(c, decay_days=10, decay_tp=0.25)),
    ("pozdni_cil_7d_01", "po 7 dnech bez cile vystoupit pri prvnim malem zisku (0.1 ATR)",
     lambda c: _with(c, decay_days=7, decay_tp=0.1)),
    # round 17: when the rates strongly support the trade (strongest tier: 95-100 % wins, +0.15..+0.19 R per trade
    # in every period), a trader lets it run further or also buys a breakout in the same direction
    ("silny_cil_1_atr", "nejsilnejsi stupen: cil 1.0 ATR misto 0.75", lambda c: _tiers(c, lambda t: [{**t[0], "tp": 1.0}] + t[1:])),
    ("silne_cil_1_atr", "oba silne stupne: cil 1.0 ATR", lambda c: _tiers(c, lambda t: [{**x, "tp": 1.0} for x in t[:2]] + t[2:])),
    ("silny_dve_casti", "nejsilnejsi stupen: pulka pozice s cilem 0.75 ATR, pulka 1.5 ATR",
     lambda c: _tiers(c, lambda t: [{**t[0], "tp_parts": (0.75, 1.5)}] + t[1:])),
    ("silny_i_pruraz", "nejsilnejsi stupen bere i pruraz 20denniho maxima ve smeru sazeb (Donchian 20)",
     lambda c: _tiers(c, lambda t: [{**t[0], "signal": t[0].get("signal", "D RSI2<5") + "|D Donchian20 pruraz"}] + t[1:])),
    ("silny_i_3_dny", "nejsilnejsi stupen bere i 3 dny poklesu za sebou",
     lambda c: _tiers(c, lambda t: [{**t[0], "signal": t[0].get("signal", "D RSI2<5") + "|D 3 dny dolu"}] + t[1:])),
    # round 18: one hypothesis from round 17 - with strong rate support the pair trends, so the strongest tier
    # behaves like a trend trader (buys dips AND breakouts, lets half of the position run to 1.5 ATR). Note: the two
    # parts were each tried alone in round 17 (each better in one test period), so this pair is chosen after seeing
    # them - the 2-year blocks and the forward test must confirm it
    ("silny_trend", "nejsilnejsi stupen jako trendovy obchodnik: propad i pruraz, pulka cil 0.75 ATR, pulka 1.5 ATR",
     lambda c: _tiers(c, lambda t: [{**t[0], "signal": t[0].get("signal", "D RSI2<5") + "|D Donchian20 pruraz",
                                     "tp_parts": (0.75, 1.5)}] + t[1:])),
    # round 19: quality of the rate signal (the only consistent driver, docs/OBCHODNIK.md). A divergence of monetary
    # policies lasts quarters; a 3-month change against a longer one can be a blip that reverses
    ("sazby_6m_potvrzeni", "vsechny stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem",
     lambda c: _tiers(c, lambda t: [{**x, "confirm_src": "oecd6"} for x in t])),
    ("sazby_6m_potvrzeni_slabe", "slabsi stupne: i zmena rozdilu sazeb za 6 mesicu ukazuje stejnym smerem",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "confirm_src": "oecd6"} for x in t[2:]])),
    ("sazby_12m_potvrzeni_slabe", "slabsi stupne: i zmena rozdilu sazeb za 12 mesicu ukazuje stejnym smerem",
     lambda c: _tiers(c, lambda t: t[:2] + [{**x, "confirm_src": "oecd12"} for x in t[2:]])),
    ("sazby_okno_6m", "zmena rozdilu sazeb se meri za 6 mesicu misto 3 (prahy stejne)",
     lambda c: _tiers(c, lambda t: [{**x, "rates_window": 6} for x in t])),
    # round 20: a trader trades smaller after a bad run (the losers come in clusters, docs/CHANGE_LOG.md R-024);
    # live: the model's own account from the forward test decides
    ("brzda_10_polovina", "kdyz je ucet modelu vic nez 10 % pod maximem, nove obchody polovicni",
     lambda c: _with(c, brake=[0.10, 0.5])),
    ("brzda_15_polovina", "kdyz je ucet modelu vic nez 15 % pod maximem, nove obchody polovicni",
     lambda c: _with(c, brake=[0.15, 0.5])),
    ("brzda_5_dvetretiny", "kdyz je ucet modelu vic nez 5 % pod maximem, nove obchody na 2/3",
     lambda c: _with(c, brake=[0.05, 0.67])),
    # round 21: a trader's stop on the daily close (a wick does not stop the trade), disaster stop beyond
    ("stop_na_zavreni_15", "stop 4 ATR plati jen pri zavreni dne (NY 17:00), behem dne jen nouzovy stop 6 ATR",
     lambda c: _with(c, close_stop=1.5)),
    ("stop_na_zavreni_125", "stop 4 ATR plati jen pri zavreni dne, behem dne nouzovy stop 5 ATR",
     lambda c: _with(c, close_stop=1.25)),
    ("stop_3_na_zavreni_2", "stop 3 ATR pri zavreni dne, behem dne nouzovy stop 6 ATR",
     lambda c: _with(c, sl=3.0, close_stop=2.0)),
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
                     + (f", po 2 letech {' / '.join(f'{b[0]:+.0%}' if isinstance(b, list) else f'{b:+.0%}' for b in e['blocks'])}"
                        if "blocks" in e else "")
                     + f", vynos/propad {calmar(e['test_cagr'], e['test_dd']):.2f}")
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
