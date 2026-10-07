"""Current signals of the self-learning champion for the 12 live pairs, in
Czech, for the dashboard (docs/NAVOD_PREHLED.md).

    python scripts/signals_live.py            # -> data/live/stav.json (+ learning/forward_trades.json)

Data: Yahoo Finance hourly quotes (last year; checked 2026-10-01 against the
FXCM hourly closes the model learned on: median difference 0.3-3 pips),
daily bars ending at the New York close; OECD 3-month rates from FRED with
the same two-month lag as in the backtest; VIX from FRED (information only).

The rule is the champion of scripts/self_learn.py (learning/champion_12_mesicne.json:
>= 2 winning trades a month). Signals count only at the Friday close; run
on Friday after 16:00 New York the last (still open) daily bar is the
decision bar - the "decide 1 h before the close" variant of the backtest.

Model forward test: every Friday signal is stored once in
learning/forward_trades.json and resolved later on the hourly path
(TP / SL / time, SL first when both in one hour), so the dashboard shows the
model's own live record.
"""

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fundamenty as F  # noqa: E402
import profit_lab2 as P  # noqa: E402
import research_factors as RF  # noqa: E402
import strategy_mining as SM  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402
from src.path_archive import trading_date  # noqa: E402
from src.sources.http import fetch  # noqa: E402

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")
DECIDE_H = 1                                   # the Friday decision 1 h before the 17:00 New York close (= Rule.decide_h)
LEARNING = PROJECT_ROOT / "learning"
CHAMPION = LEARNING / "champion_12_mesicne.json"
FORWARD = LEARNING / "forward_trades.json"
RISK_FILE = LEARNING / "riziko.json"        # stop-based sizing: tier weights + test table (scripts/riziko_lab.py --stupne)
OUT = PROJECT_ROOT / "data" / "live" / "stav.json"
YAHOO = {"EUR/USD": "EURUSD=X", "USD/JPY": "JPY=X", "GBP/USD": "GBPUSD=X", "USD/CHF": "CHF=X",
         "AUD/USD": "AUDUSD=X", "USD/CAD": "CAD=X", "NZD/USD": "NZDUSD=X", "EUR/JPY": "EURJPY=X",
         "GBP/JPY": "GBPJPY=X", "EUR/GBP": "EURGBP=X", "EUR/CHF": "EURCHF=X", "AUD/JPY": "AUDJPY=X"}
CZK = {"EUR": "EURCZK=X", "USD": "CZK=X", "GBP": "GBPCZK=X", "AUD": "AUDCZK=X", "NZD": "NZDCZK=X"}
REF_SL_MARGIN = 84.0
HOURLY_CACHE: dict = {}                         # the last run's hourly prices per pair (reused by scripts/heuristiky.py)
TIER_NAMES = ("silny", "silny", "stredni", "slaby", "slaby", "slaby")
CCY_CZ = {"USD": "americky dolar", "EUR": "euro", "JPY": "japonsky jen", "GBP": "britska libra",
          "CHF": "svycarsky frank", "AUD": "australsky dolar", "CAD": "kanadsky dolar", "NZD": "novozelandsky dolar"}


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------

def yahoo_hourly(symbol: str, span: str = "1y") -> dict:
    _, content, _ = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1h&range={span}",
                          retries=4)
    r = json.loads(content)["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    rows = [(t, o, h, l, c) for t, o, h, l, c in zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"])
            if None not in (o, h, l, c) and h >= l > 0]
    a = np.array(rows, dtype=float)
    a[:, 0] = a[:, 0] // 3600 * 3600                    # the last bar carries the current minute
    return {"ts": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4]}


def daily(hb: dict) -> dict:
    """Daily bars ending at the New York close (17:00 New York)."""
    days, first, last = [], [], []
    for k, t in enumerate(hb["ts"]):
        d = trading_date(int(t))
        if not days or d != days[-1]:
            days.append(d)
            first.append(k)
            last.append(k)
        else:
            last[-1] = k
    o = np.array([hb["o"][a] for a in first])
    c = np.array([hb["c"][b] for b in last])
    h = np.array([hb["h"][a:b + 1].max() for a, b in zip(first, last)])
    l_ = np.array([hb["l"][a:b + 1].min() for a, b in zip(first, last)])
    hours = np.array([b - a + 1 for a, b in zip(first, last)])
    keep = (hours >= 18) | (np.arange(len(days)) == len(days) - 1)        # the current day may be partial
    keep &= np.array([d.weekday() < 5 for d in days])   # a tick after the Friday close is no trading day (as FXCM)
    return {"days": [d for d, k in zip(days, keep) if k], "o": o[keep], "h": h[keep], "l": l_[keep], "c": c[keep],
            "last_ts": np.array([hb["ts"][b] for b in last])[keep]}


def refresh_rates() -> None:
    RF.FRED_DIR.mkdir(parents=True, exist_ok=True)
    ids = [i for ids in P.RATE_IDS.values() for i in ids] + list(P.EXTEND_IDS.values()) + ["VIXCLS"]
    for sid in sorted(set(ids)):
        try:
            _, content, _ = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", retries=3)
            if content.startswith(b"observation_date"):
                (RF.FRED_DIR / f"{sid}.csv").write_bytes(content)
        except Exception as exc:                         # keep the cached series
            print(f"FRED {sid}: {exc}", file=sys.stderr)


# ----------------------------------------------------------------------
# rule
# ----------------------------------------------------------------------

def champion() -> dict:
    state = json.loads(CHAMPION.read_text())
    return {"config": state["config"], "shares": list(state["eval"]["1"]["shares"]), "eval": state["eval"]}


def rsi_trigger(closes: np.ndarray, n: int, level: float, side: int) -> float:
    """Close of the decision day at which RSI(n) reaches `level` (BUY: falls
    below it, SELL: `100 - level` from below), from the state of the day before."""
    d = np.diff(closes, prepend=closes[0])
    ag = SM.wilder(np.clip(d, 0, None), n)[-1]
    al = SM.wilder(np.clip(-d, 0, None), n)[-1]
    if side > 0:
        move = (n - 1) * (ag * (100 - level) / level - al)
        return float(closes[-1] - max(0.0, move))
    hi = 100 - level
    move = (n - 1) * (al * hi / (100 - hi) - ag)
    return float(closes[-1] + max(0.0, move))


TP_LEVELS = (0.75, 1.0, 1.5)               # replaced by learning/pair_stats.json "tp_atr" when present


CB_OF = F.CB_OF                             # one map of the four central banks (fundamenty)
CB_LABEL = {"FED": "Fed", "ECB": "ECB", "BOJ": "BoJ", "BOE": "BoE"}
DAYS_CZ = ("po", "út", "st", "čt", "pá", "so", "ne")


def cb_decisions(pair: str, start: date, days: int = 28) -> list[date]:
    """Scheduled decisions of the pair's central banks from `start` for `days` days (learning/udalosti_historie.json)."""
    path = LEARNING / "udalosti_historie.json"
    if not path.exists():
        return []
    ev = json.loads(path.read_text())
    inst = get_instrument(pair)
    out = []
    for ccy in (inst.base, inst.quote):
        bank = CB_OF.get(ccy)
        for d in ev.get(bank, []) if bank else []:
            dd = date.fromisoformat(d)
            if start < dd <= start + timedelta(days=days):
                out.append((dd, CB_LABEL[bank]))
    return sorted(out)


def cb_exit_note(pair: str, start: date, base: dict) -> dict | None:
    """The champion closes a trade that is in profit at the New York close of the trading day before a
    scheduled decision of either currency's central bank (rule exit_before_cb = "zisk", R-021)."""
    if base.get("exit_before_cb") != "zisk":
        return None
    dates = cb_decisions(pair, start)
    when = ", ".join(f"{b} {DAYS_CZ[d.weekday()]} {d.day}. {d.month}." for d, b in dates)
    return {"pravidlo": "Když je obchod v zisku, zavři ho při zavření trhu (23:00 našeho času) den před rozhodnutím "
                        "centrální banky jeho měn. Ve ztrátě ho nech běžet dál k cíli nebo stop lossu.",
            "rozhodnuti": [{"den": d.isoformat(), "banka": b} for d, b in dates],
            "text": f"Rozhodnutí v příštích 4 týdnech: {when}" if dates else "V příštích 4 týdnech žádné rozhodnutí."}


def make_plan(side: int, entry: float, atr: float, base: dict, decimals: int, kind: str, lev: int) -> dict:
    """Entry, three targets and the stop for one trade (prices and % of the margin at the pair's leverage)."""
    stats_path = LEARNING / "pair_stats.json"
    levels = json.loads(stats_path.read_text()).get("tp_atr", TP_LEVELS) if stats_path.exists() else TP_LEVELS
    tps = [{"cislo": i + 1, "atr": L, "cena": round(entry + side * L * atr, decimals),
            "proc_marze": round(L * atr / entry * 100 * lev, 1)} for i, L in enumerate(levels)]
    return {"typ": kind, "vstup": round(entry, decimals), "tp": tps, "paka": lev,
            "sl": {"atr": base["sl"], "cena": round(entry - side * base["sl"] * atr, decimals),
                   "proc_marze": round(base["sl"] * atr / entry * 100 * lev, 1)}}


def sizing_table(champion_name: str) -> dict | None:
    """learning/riziko.json when it belongs to the live champion (else None: diagnostika warns, the dashboard falls
    back to the champion's own margins)."""
    if not RISK_FILE.exists():
        return None
    table = json.loads(RISK_FILE.read_text())
    return table if table.get("sampion") == champion_name else None


def risk_margin(risk: float, weight: float, sl_margin_pct: float) -> float:
    """Margin in % of the account so that the stop costs risk x weight of the account (sl_margin_pct = the stop in %
    of the margin). Stop-based sizing, docs/RIZIKO.md."""
    return risk * weight * 100.0 / (sl_margin_pct / 100.0)


def risk_view(sizing: dict | None, k: int, sl_margin: float, tp_margin: float) -> dict | None:
    """The trade at the dashboard's default risk: margin, loss at the stop and gain at the target in % of the account."""
    if not sizing or k >= len(sizing["vahy"]):
        return None
    w, r = sizing["vahy"][k], sizing["vychozi_riziko"]
    m = risk_margin(r, w, sl_margin)
    return {"vaha": w, "riziko_proc": round(r * 100, 1), "marze_proc_uctu": round(m, 1),
            "ztrata_sl_proc_uctu": round(m * sl_margin / 100, 2), "zisk_tp_proc_uctu": round(m * tp_margin / 100, 2)}


def decision_ready(day: date, last_bar_open: int, now: float | None = None) -> bool:
    """True when `day` is a Friday whose decision moment is reached: the hourly bars go
    to 15:00 New York or later (the close is 17:00) and the clock is past
    16:00 New York (the decision time, 1 hour before the close, as tested: decide_h=1).
    Earlier on Friday an RSI signal would come from a shorter part of the day than tested
    (the hourly updates run all Friday)."""
    if day.weekday() != 4:
        return False
    close = datetime(day.year, day.month, day.day, 17, tzinfo=NEW_YORK).timestamp()
    now = time.time() if now is None else now
    return close - (last_bar_open + 3600) <= 3600 and now >= close - 3600


def signal_parts(sig: str) -> list[tuple[int, float]]:
    """'D RSI2<5|D RSI3<15' -> [(2, 5.0), (3, 15.0)]: the RSI signals the live run implements. Anything else
    raises (diagnostika.live_unsupported reports it before a signal could differ from the tested rule)."""
    out = []
    for part in sig.split("|"):
        m = re.fullmatch(r"D RSI(\d+)<(\d+(?:\.\d+)?)", part.strip())
        if not m:
            raise ValueError(f"signal '{part}' neni v zivem vypoctu implementovan")
        out.append((int(m.group(1)), float(m.group(2))))
    return out


def decision_cut(day: date) -> int:
    """The tested decision moment of a Friday: 16:00 New York, 1 h before the close (profit_deep Rule.decide_h=1:
    the earlier days with their full closes, the Friday up to 16:00). Every run after it decides the same."""
    return int(datetime(day.year, day.month, day.day, 17 - DECIDE_H, tzinfo=NEW_YORK).timestamp())


def until(hb: dict, ts: int) -> dict:
    """Hourly bars that opened before `ts`."""
    keep = hb["ts"] < ts
    return {k: v[keep] for k, v in hb.items()}


def stale_rates(rates: dict, day: date) -> dict:
    """Currencies whose OECD 3-month rate is >= 2 months older than the model
    expects (the month 2 months back): their 3-month change is only carried
    forward (counts as about 0). {currency: last month 'YYYY-MM'}."""
    out = {}
    for ccy, series in rates.items():
        if series:
            y, m = max(series)
            if (day.year - y) * 12 + day.month - m - 2 >= 2:
                out[ccy] = f"{y}-{m:02d}"
    return out


def research_view(pair: str, D: dict, lock: dict | None) -> dict | None:
    """Weekly research (scripts/vyzkum_most.py) at the current daily bar: information only - the model does not
    trade it (the research variants did not pass the walk-forward gate, docs/CHANGE_LOG.md R-028)."""
    if not lock or pair not in lock:
        return None
    import vyzkum_most as VM
    try:
        return VM.live_view(lock[pair], {"o": D["o"], "h": D["h"], "l": D["l"], "c": D["c"]})
    except Exception:
        return None


def evaluate_pair(pair: str, cfg: dict, shares: list, rates: dict, today: date, lock: dict | None = None,
                  hourly: dict | None = None) -> dict:
    inst = get_instrument(pair)
    sizing = sizing_table(cfg["name"])
    hb = yahoo_hourly(YAHOO[pair], "2y")                 # 2 years: the research conditions need 250+ daily bars
    if hourly is not None:
        hourly[pair] = hb                                # reused by the forward test (no second download)
    D = daily(hb)
    day = D["days"][-1]
    latest = float(D["c"][-1])
    is_friday = decision_ready(day, int(D["last_ts"][-1]))
    Dd = D
    if is_friday:                                        # the tested decision: the Friday up to 16:00 New York
        cut = decision_cut(day)
        Dd = daily(until(hb, cut))
        if Dd["days"][-1] != day or int(Dd["last_ts"][-1]) != cut - 3600:
            return {"par": pair, "den": day.isoformat(), "cena": round(latest, inst.decimals), "smer": "NIC",
                    "stupen": "-", "signal": None, "podminka": "nedostatek dat: chybi hodinova svicka 15-16 h New York",
                    "chyba": "chybi hodinova svicka pred patecnim rozhodnutim"}
    c, h, l_ = Dd["c"], Dd["h"], Dd["l"]
    atr = SM.wilder(SM.true_range(h, l_, c), 14)
    rsi2, rsi3 = SM.rsi(c, 2), SM.rsi(c, 3)
    kb, kq = (P.rate_at(rates[x], day.year, day.month, 2) for x in (inst.base, inst.quote))
    ob, oq = (P.rate_at(rates[x], day.year, day.month, 5) for x in (inst.base, inst.quote))
    carry = None if kb is None or kq is None else kb - kq
    mom = None if carry is None or ob is None or oq is None else carry - (ob - oq)
    nb, nq = (P.rate_at(rates[x], day.year, day.month, 1) for x in (inst.base, inst.quote))
    carry_fin = (nb - nq) if nb is not None and nq is not None else carry   # the swap uses the newer month, as the backtest
    base = cfg["base"]
    lev = P.leverage(pair)
    out = {"par": pair, "cena": round(latest, inst.decimals), "den": day.isoformat(), "paka": lev,
           "rsi2": round(float(rsi2[-1]), 1), "rsi3": round(float(rsi3[-1]), 1),
           "atr": round(float(atr[-1]), inst.decimals), "atr_proc": round(float(atr[-1] / c[-1] * 100), 3),
           "rozdil_sazeb": None if carry is None else round(carry, 2),
           "zmena_sazeb_3m": None if mom is None else round(mom, 2), "desetinna_mista": inst.decimals,
           "signal": None, "vyzkum": research_view(pair, D, lock),
           "rozdil_sazeb_swap": None if carry_fin is None else round(carry_fin, 2)}
    if is_friday:
        out["cena_rozhodnuti"] = round(float(c[-1]), inst.decimals)            # the 16:00 New York price
    stale = {c: m for c, m in stale_rates(rates, day).items() if c in (inst.base, inst.quote)}
    if stale or mom is None:        # missing data is not neutral data: no rate-based decision on this pair
        out["varovani"] = ("zastarala sazba " + ", ".join(f"{c} (posledni udaj {m})" for c, m in stale.items())
                           + " - zmenu sazeb nelze spocitat, model u tohoto paru nerozhoduje")
        out.update(smer="NIC", stupen="-", podminka="nedostatek dat: zastarala sazba, signal se nevyhodnocuje")
        return out
    # which direction and tier the fundamentals allow
    allowed = []
    for side in (1, -1):
        for k, tier in enumerate(cfg["tiers"]):
            if shares[k] <= 0:
                continue
            ok = side * mom >= tier["rates_thr"] - 1e-9
            if tier["fund"] == "rates_up+carry":
                ok = ok and np.sign(carry) == side
            if ok:
                allowed.append((side, k, tier))
                break
    if allowed:
        side, k, tier = max(allowed, key=lambda a: shares[a[1]])
        sig = tier.get("signal", base["signal"])
        out["smer"] = "KOUPIT" if side > 0 else "PRODAT"
        out["stupen"] = TIER_NAMES[k] if k < len(TIER_NAMES) else "slaby"
        out["marze_zaklad"] = shares[k]
        out["stupen_index"] = k
        if sizing and k < len(sizing["vahy"]):
            out["riziko_vaha"] = sizing["vahy"][k]
        prev = c[:-1]                                     # Wilder state up to the day before the decision bar
        parts = signal_parts(sig)
        trig = [rsi_trigger(prev, n, x, side) for n, x in parts]
        level = max(trig) if side > 0 else min(trig)     # the easier of the two signals
        out["spoustec"] = round(level, inst.decimals)
        out["plan"] = make_plan(side, level, float(atr[-1]), base, inst.decimals, "podminka", lev)
        note = cb_exit_note(pair, day, base)
        if note:
            out["plan"]["pred_rozhodnutim"] = note
        word, rel = ("KOUPIT", "pod") if side > 0 else ("PRODAT", "nad")
        if day.weekday() == 4:
            out["podminka"] = f"{word}, kdyz cena v 16:00 New York (obvykle 22:00 Praha) bude {rel} {level:.{inst.decimals}f}"
        else:
            out["podminka"] = (f"jen {word}; signal se vyhodnoti v patek (dnes by nastal pri cene {rel} "
                               f"{level:.{inst.decimals}f})")
        hits = [(SM.rsi(c, n)[-1] < x) if side > 0 else (SM.rsi(c, n)[-1] > 100 - x) for n, x in parts]
        hit_rsi2, hit_rsi3 = bool(hits[0]), any(hits[1:])
        if base.get("skip_holidays") and ((day.month == 12 and day.day >= 15) or (day.month == 1 and day.day <= 5)):
            is_friday = False                            # the tested rule opens no trade at the year end
            out["podminka"] = "konec roku (15. 12. - 5. 1.): model nove obchody neotevira"
        if base.get("max_atr_rank", 1.0) < 1.0:        # volatility shock of the pair (profit_deep.atr_rank)
            pct = atr / c
            rank = float(np.mean(pct[-250:] <= pct[-1])) if len(pct) >= 250 and not np.isnan(pct[-250:]).any() else np.nan
            out["atr_poradi"] = None if np.isnan(rank) else round(rank * 100)
            if not rank <= base["max_atr_rank"]:
                is_friday = False
                out["podminka"] = (f"volatilita paru je ted extremni (vyssi nez {base['max_atr_rank'] * 100:.0f} % "
                                   "poslednich 250 dni) - model nove obchody neotevira")
        out["rozhodovaci_den"] = is_friday
        out["v_pasmu"] = bool(hit_rsi2 or hit_rsi3)
        min_tp = base.get("min_tp_pct", P.MIN_TP_PCT) * (lev if base.get("min_tp_price") else P.LEVERAGE)  # % margin
        out["cil_ok"] = bool(base["tp"] * atr[-1] / c[-1] * 100 * lev >= min_tp - 1e-9)
        if is_friday and (hit_rsi2 or hit_rsi3):
            entry = float(c[-1])
            tp = entry + side * base["tp"] * atr[-1]
            sl = entry - side * base["sl"] * atr[-1]
            sl_margin = base["sl"] * atr[-1] / entry * 100 * lev
            tp_margin = base["tp"] * atr[-1] / entry * 100 * lev
            mult = float(np.clip(REF_SL_MARGIN / sl_margin, 0.5, 2.0)) if cfg.get("sizing") == "vol" else 1.0
            if cfg.get("notional_parity"):
                mult *= P.LEVERAGE / lev                 # the same position volume as a 1:30 pair (self_learn)
            if tp_margin >= min_tp - 1e-9:
                out["signal"] = {
                    "smer": out["smer"], "stupen": out["stupen"], "vstup": round(entry, inst.decimals),
                    "tp": round(tp, inst.decimals), "sl": round(sl, inst.decimals),
                    "marze_proc_uctu": round(shares[k] * mult * 100, 1),
                    "zisk_tp_proc_marze": round(tp_margin, 1), "ztrata_sl_proc_marze": round(sl_margin, 1),
                    "riziko": risk_view(sizing, k, sl_margin, tp_margin),
                    "zavrit_nejpozdeji": (day + timedelta(days=28)).isoformat(),
                    "vyzkum": research_votes(out["vyzkum"], side),
                    "paka": lev, "cas_rozhodnuti": decision_cut(day),
                    "plan": {**make_plan(side, entry, float(atr[-1]), base, inst.decimals, "trh", lev),
                             **({"pred_rozhodnutim": cb_exit_note(pair, day, base)} if cb_exit_note(pair, day, base) else {})},
                    "duvod": (f"RSI(2) {rsi2[-1]:.0f}{', RSI(3) %.0f' % rsi3[-1] if 'RSI3' in sig else ''} = prudky "
                              f"{'propad' if side > 0 else 'rust'}; rozdil sazeb {inst.base}-{inst.quote} se za 3 mesice "
                              f"zmenil o {mom:+.2f} p.b. ve prospech {'nakupu' if side > 0 else 'prodeje'}"
                              f"{', carry %+.2f %% ve smeru obchodu' % carry if tier['fund'] == 'rates_up+carry' else ''}")}
    else:
        out["smer"] = "NIC"
        out["stupen"] = "-"
        out["podminka"] = "fundamenty (sazby) ted nepodporuji zadny smer"
    return out


def research_votes(view: dict | None, side: int) -> dict | None:
    if not view:
        return None
    pro, proti = (view["pro_rust"], view["pro_pokles"]) if side > 0 else (view["pro_pokles"], view["pro_rust"])
    return {"pro": len(pro), "proti": len(proti), "podminky_pro": pro, "podminky_proti": proti,
            "text": (f"Týdenní výzkum (jen informace, model to nepoužívá): {len(pro)} podmínek pro obchod, "
                     f"{len(proti)} proti (z {view['zamceno']} robustních podmínek páru).")}


def rank_pairs(pairs: list) -> None:
    """Attach the historical success of the applicable tier on each pair
    (learning/pair_stats.json) and sort: signal now first, then pairs the
    fundamentals allow, each by the estimated success and average result."""
    path = LEARNING / "pair_stats.json"
    stats = json.loads(path.read_text()) if path.exists() else {"stupne": []}
    for p in pairs:
        k = p.get("stupen_index")
        if k is None or k >= len(stats["stupne"]):
            continue
        st = stats["stupne"][k]["pary"].get(p["par"])
        if st:
            p.update(odhad_uspesnosti=st["odhad_uspesnosti"], odhad_prumer=st["odhad_prumer"],
                     uspesnost_hist=st["uspesnost"], n_hist=st["n"], prumer_hist=st["prumer_proc_marze"])
            levels = st.get("tp", [])
            for plan in (p.get("plan"), (p.get("signal") or {}).get("plan")):
                if not plan:
                    continue
                for tp, lv in zip(plan["tp"], levels):
                    tp["pravdepodobnost"] = lv["pravdepodobnost"]
                    tp["prumer_proc_marze"] = lv["prumer_proc_marze"]
                plan["pravdepodobnost_uspechu"] = levels[0]["pravdepodobnost"] if levels else None
                plan["prumer_rozdeleni_3"] = st.get("prumer_rozdeleni_3")
            if levels:
                p["pravdepodobnost_uspechu"] = levels[0]["pravdepodobnost"]
    for p in pairs:
        p["skupina"] = ("signal" if p.get("signal") else "pripraven" if p.get("v_pasmu") and p.get("cil_ok")
                        else "povoleny" if p.get("smer") in ("KOUPIT", "PRODAT") else "nic")
    order = {"signal": 3, "pripraven": 2, "povoleny": 1, "nic": 0}
    pairs.sort(key=lambda p: (order[p["skupina"]], p.get("pravdepodobnost_uspechu") or 0, p.get("odhad_prumer") or 0),
               reverse=True)
    for i, p in enumerate(pairs, 1):
        p["poradi"] = i


# ----------------------------------------------------------------------
# model forward test
# ----------------------------------------------------------------------

def rates_turned(pair: str, day: date, side: int, rates: dict | None) -> bool:
    """The rate-difference change over 3 months (known at `day`, the model's lag) points against the trade
    (profit_deep.Rule.exit_rates_flip). Missing rates: no exit (nothing is known to have changed)."""
    if not rates:
        return False
    b, q = pair.split("/")
    kb, kq, ob, oq = (P.rate_at(rates[x], day.year, day.month, lag) for lag in (2, 5) for x in (b, q))
    if None in (kb, kq, ob, oq):
        return False
    return side * ((kb - kq) - (ob - oq)) < 0


def resolve_forward(trades: list, hourly_cache: dict, rates: dict | None = None) -> None:
    """Close open model trades on the hourly path exactly as the backtest does (scripts/profit_deep.simulate):
    costs (half the spread + slippage on entry and exit), per hour the stop first, then the target, then at the
    New York close bar the exit in profit before a central bank decision, the time exit after the rule's
    holding period (20 trading days = 480 hours, as profit_deep.simulate),
    and the swap (rate difference -/+ 1 % p.a.). Results in % of the margin at the pair's leverage."""
    for t in trades:
        if t["stav"] != "otevreny":
            continue
        hb = hourly_cache.get(t["par"])
        if hb is None:
            continue
        inst = get_instrument(t["par"])
        half = (P.SPREAD_PIPS[t["par"]] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip
        side = 1 if t["smer"] == "KOUPIT" else -1
        entry = t["vstup"] + side * half                  # bought at the ask / sold at the bid
        after = hb["ts"] >= t["cas_vstupu"]               # from the first hour after the entry moment
        ts, hh, ll, cc = hb["ts"][after], hb["h"][after], hb["l"][after], hb["c"][after]
        decisions = {d for d, _ in cb_decisions(t["par"], date.fromisoformat(t["den"]), 40)} if t.get("cb_vystup") else set()
        hold = t.get("drzeni_dni", 20)
        n_bars = P.HOLD_BARS.get(hold, 24 * hold)        # the backtest's time exit: the close of the n-th hour
        exit_px = None
        for j in range(len(ts)):
            if (side > 0 and ll[j] - half <= t["sl"]) or (side < 0 and hh[j] + half >= t["sl"]):
                exit_px, why = t["sl"], "SL"
            elif (side > 0 and hh[j] - half >= t["tp"]) or (side < 0 and ll[j] + half <= t["tp"]):
                exit_px, why = t["tp"], "TP"
            else:
                bar = datetime.fromtimestamp(int(ts[j]), tz=NEW_YORK)
                nxt = bar.date() + timedelta(days=3 if bar.weekday() == 4 else 1)
                close_px = float(cc[j]) - side * half
                if decisions and bar.hour == 16 and nxt in decisions and side * (close_px - entry) > 0:
                    exit_px, why = close_px, "pred rozhodnutim CB"
                elif t.get("vystup_sazby") and bar.hour == 16 and j > 0 and rates_turned(t["par"], bar.date(), side, rates):
                    exit_px, why = close_px, "sazby se otocily proti obchodu"
                elif j >= n_bars - 1:
                    exit_px, why = close_px, "cas"
            if exit_px is not None:
                t.update(stav="uzavreny", vystup=float(exit_px), duvod_vystupu=why, cas_vystupu=int(ts[j]) + 3600)
                break
        lev = P.leverage(t["par"])
        if t["stav"] == "uzavreny":
            days = (t["cas_vystupu"] - t["cas_vstupu"]) / 86400
            fin = t.get("swap_proc_rocne", 0.0) / 100 / 365 * days * entry
            t["vysledek_proc_marze"] = round((side * (t["vystup"] - entry) + fin) / entry * 100 * lev, 1)
        elif len(cc):
            t["prubezne_proc_marze"] = round(side * (float(cc[-1]) - side * half - entry) / entry * 100 * lev, 1)


def main() -> int:
    started = time.monotonic()
    refresh_rates()
    rates = P.monthly_rates()
    ch = champion()
    cfg, shares = ch["config"], ch["shares"]
    today = datetime.now(UTC).date()
    pairs, cache = [], {}
    research_error = None
    try:
        import vyzkum_most as VM
        lock = VM.live_lock(list(DEFAULT_ACTIVE))
    except Exception as exc:                              # research is information only: never blocks the signals,
        research_error = f"{type(exc).__name__}: {exc}"   # but the failure is shown (stav vyzkum_chyba)
        print(f"vyzkum nedostupny: {research_error}", file=sys.stderr)
        lock = None
    for pair in DEFAULT_ACTIVE:
        try:
            pairs.append(evaluate_pair(pair, cfg, shares, rates, today, lock, cache))
        except Exception as exc:
            pairs.append({"par": pair, "chyba": f"data nedostupna: {type(exc).__name__}"})
    rank_pairs(pairs)
    HOURLY_CACHE.clear()
    HOURLY_CACHE.update(cache)
    czk = {}
    for ccy, sym in CZK.items():
        try:
            czk[ccy] = round(float(yahoo_hourly(sym, "5d")["c"][-1]), 4)
        except Exception:
            czk[ccy] = None
    # forward test bookkeeping
    LEARNING.mkdir(exist_ok=True)
    forward = json.loads(FORWARD.read_text()) if FORWARD.exists() else []
    now = int(time.time())
    for p in pairs:
        s = p.get("signal")
        if not s:
            continue
        key = f"{p['den']}_{p['par'].replace('/', '')}"
        if any(t["id"] == key for t in forward):
            continue
        if now > s.get("cas_rozhodnuti", now) + DECIDE_H * 3600:
            continue                                     # only signals published before the close (no back-dating)
        forward.append({"id": key, "par": p["par"], "smer": s["smer"], "stupen": s["stupen"], "den": p["den"],
                        "cas_vstupu": s.get("cas_rozhodnuti", now), "vstup": s["vstup"], "tp": s["tp"], "sl": s["sl"],
                        "marze_proc_uctu": s["marze_proc_uctu"], "stav": "otevreny",
                        "riziko_vaha": p.get("riziko_vaha"), "ztrata_sl_proc_marze": s["ztrata_sl_proc_marze"],
                        "cb_vystup": cfg["base"].get("exit_before_cb") == "zisk", "drzeni_dni": cfg["base"]["hold_days"],
                        **({"vystup_sazby": True} if cfg["base"].get("exit_rates_flip") else {}),
                        "swap_proc_rocne": round((1 if s["smer"] == "KOUPIT" else -1) * p["rozdil_sazeb_swap"] - P.FIN_MARKUP, 2),
                        **({"vyzkum_pro": s["vyzkum"]["pro"], "vyzkum_proti": s["vyzkum"]["proti"]}
                           if s.get("vyzkum") else {})})
    resolve_forward(forward, cache, rates)
    FORWARD.write_text(json.dumps(forward, indent=1, ensure_ascii=False))
    closed = [t for t in forward if t["stav"] == "uzavreny"]
    # fundamentals per currency
    day = max(date.fromisoformat(p["den"]) for p in pairs if "den" in p)
    fund = []
    stale = stale_rates(rates, day)
    for ccy in ("USD", "EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"):
        now_r, old_r = P.rate_at(rates[ccy], day.year, day.month, 2), P.rate_at(rates[ccy], day.year, day.month, 5)
        fund.append({"mena": ccy, "nazev": CCY_CZ[ccy], "sazba_3m": None if now_r is None else round(now_r, 2),
                     "zmena_3m": None if now_r is None or old_r is None else round(now_r - old_r, 2),
                     "zastarale": stale.get(ccy),
                     "doplneno": "%d-%02d" % P.EXTENDED[ccy] if ccy in P.EXTENDED else None})
    vix_rows = RF._csv("VIXCLS")
    ev = ch["eval"]
    state = {
        "aktualizovano": datetime.now(UTC).isoformat(timespec="minutes"),
        "den_dat": day.isoformat(), "je_patek": any(p.get("rozhodovaci_den") for p in pairs),
        "trh_zavren": any(p.get("rozhodovaci_den") for p in pairs) and now > decision_cut(day) + DECIDE_H * 3600,
        "pravidlo": cfg["name"],
        "pravidlo_popis": {"tp_atr": cfg["base"]["tp"], "sl_atr": cfg["base"]["sl"], "drzeni_dni": cfg["base"]["hold_days"],
                           "vystup_pred_cb": cfg["base"].get("exit_before_cb") == "zisk",
                           "stupne": [{"jmeno": TIER_NAMES[k] if k < len(TIER_NAMES) else "slaby",
                                       "marze_proc_uctu": round(s * 100, 1), "prah_sazeb": t["rates_thr"],
                                       "carry": t["fund"] == "rates_up+carry",
                                       "signal": t.get("signal", cfg["base"]["signal"]).replace("D ", "")}
                                      for k, (t, s) in enumerate(zip(cfg["tiers"], shares))]},
        "backtest": {"test_2019_22": {"rocne": round(ev["0"]["test_cagr"] * 100, 1), "propad": round(ev["0"]["test_dd"] * 100, 1)},
                     "test_2023_26": {"rocne": round(ev["1"]["test_cagr"] * 100, 1), "propad": round(ev["1"]["test_dd"] * 100, 1),
                                      "ziskovych_mesicne": round(ev["1"]["test_wins_month"], 1)}},
        "pary": pairs,
        "vyzkum_pravidla": (lock or {}).get("_pravidla", []),
        "vyzkum_chyba": research_error,
        "signaly": [dict(par=p["par"], odhad_uspesnosti=p.get("odhad_uspesnosti"), uspesnost_hist=p.get("uspesnost_hist"),
                         n_hist=p.get("n_hist"), pravdepodobnost_uspechu=p.get("pravdepodobnost_uspechu"),
                         varovani=p.get("varovani"), **p["signal"])
                    for p in pairs if p.get("signal")],
        "razeni": "signal, pak pripravene ke vstupu, pak ostatni povolene, nakonec bez smeru; uvnitr podle odhadu uspesnosti",
        "riziko": sizing_table(cfg["name"]),
        "fundamenty": fund,
        "varovani": [f"Sazba {CCY_CZ[c]} ({c}) z OECD ma posledni udaj za {m}; zmenu sazeb u paru s {c} nelze "
                     "spocitat, proto je model u tech paru nevyhodnocuje (chybejici udaj se nedoplnuje odhadem)."
                     for c, m in stale.items() if c in CCY_CZ],
        "vix": {"hodnota": vix_rows[-1][1], "den": vix_rows[-1][0].isoformat()},
        "czk": czk,
        "model": {"obchody": forward[-200:],
                  "uzavrenych": len(closed),
                  "ziskovych": sum(1 for t in closed if t["vysledek_proc_marze"] > 0),
                  "prumer_proc_marze": round(float(np.mean([t["vysledek_proc_marze"] for t in closed])), 1) if closed else None},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=1, ensure_ascii=False, default=str))
    sig = state["signaly"]
    print(f"{state['aktualizovano']} | data do {state['den_dat']} | signalu {len(sig)} | "
          f"model: uzavreno {len(closed)} | {time.monotonic() - started:.0f} s")
    for p in pairs:
        print(f"  {p['par']:8} {p.get('smer', '-'):7} {p.get('stupen', '-'):8} RSI2 {p.get('rsi2', '-')} "
              f"{p.get('podminka', p.get('chyba', ''))}")
    for s in sig:
        rv = s.get("riziko") or {}
        print(f"  SIGNAL {s['par']} {s['smer']} vstup {s['vstup']} TP {s['tp']} SL {s['sl']} marze {s['marze_proc_uctu']} % "
              f"(podle rizika {rv.get('riziko_proc', '-')} %: marze {rv.get('marze_proc_uctu', '-')} %, "
              f"ztrata pri SL {rv.get('ztrata_sl_proc_uctu', '-')} % uctu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
