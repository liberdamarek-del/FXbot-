"""Documented FX anomalies from the literature, re-tested on our data (2012-2026, costs included).

    python scripts/anomalie_lab.py       # -> docs/ANOMALIE.md

A. FOMC day (Mueller, Tahbaz-Salehi, Vedolin 2017, J. Finance): short USD against the G10 currencies
   from the New York close before a scheduled FOMC decision to the close of the decision day; also ECB,
   BoJ and BoE days for their currency.
B. Month-end equity rebalancing (bank research: BofA, UBS, BNY iFlow): when US equities outperformed the
   foreign market month-to-date, foreign investors sell USD into the last day's London 4 pm fix.
C. Intraday: dollar demand at the fixes (Krohn, Mueller, Whelan 2024, J. Finance: USD up before the
   Tokyo / ECB / London fixes, down after) and home-hours depreciation (Breedon, Ranaldo 2013).
D. Dollar carry (Lustig, Roussanov, Verdelhan 2014): short USD vs the basket when the average foreign
   short rate is above the US rate, else long USD; monthly, with interest.
E. Cross-section of the 8 currencies, monthly: momentum (3 / 12 months), carry, value proxy (5-year
   reversal), and their average: long the 2 best, short the 2 worst (USD = 0).
Returns in % of the notional (no leverage); "Sharpe" = annual return / annual volatility.
Research only - nothing enters the model without the walk-forward gate.
"""

import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_lab2 as P  # noqa: E402
import vyzkum_data as V  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
USD_PAIRS = [p for p in DEFAULT_ACTIVE if "USD" in p]
FOREIGN = {p: (get_instrument(p).quote if get_instrument(p).base == "USD" else get_instrument(p).base) for p in USD_PAIRS}
SIGN = {p: (-1 if get_instrument(p).base == "USD" else 1) for p in USD_PAIRS}   # +1 = pair up = foreign up vs USD
EQUITY = {"EUR": "^STOXX50E", "GBP": "^FTSE", "JPY": "^N225", "AUD": "^AXJO", "CAD": "^GSPTSE", "CHF": "^SSMI",
          "NZD": "^NZ50"}
PERIODS = ((2012, 2018), (2019, 2022), (2023, 2026))


def cost_pct(pair: str, price: float) -> float:
    """One side (half spread + half slippage) in % of the price."""
    inst = get_instrument(pair)
    return (P.SPREAD_PIPS[pair] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip / price * 100


def stats(x: np.ndarray, per_year: float) -> str:
    if len(x) < 3:
        return "-"
    t = x.mean() / x.std() * np.sqrt(len(x)) if x.std() > 0 else 0
    return f"{len(x)} | {x.mean():+.3f} % | {np.mean(x > 0):.0%} | t {t:+.1f} | Sharpe {x.mean() / x.std() * np.sqrt(per_year) if x.std() > 0 else 0:+.2f}"


def period_rows(name: str, items: list[tuple[date, float]], per_year: float) -> list[str]:
    rows = []
    for a, b in PERIODS:
        x = np.array([v for d, v in items if a <= d.year <= b])
        rows.append(stats(x, per_year))
    allx = np.array([v for _, v in items])
    return [f"| {name} | " + " | ".join(rows) + f" | {stats(allx, per_year)} |"]


HEAD = ("| strategie | 2012-18 (obchodů / průměr / úspěšnost / t / Sharpe) | 2019-22 | 2023-26 | celkem |", "|---|---|---|---|---|")


def main() -> int:
    fx = {p: V.fx(p) for p in DEFAULT_ACTIVE}
    banks = V.cb_dates()
    out = ["# Zdokumentované jevy na měnovém trhu – přetestováno na našich datech", "",
           "_Zdroje: Mueller, Tahbaz-Salehi, Vedolin (2017, Journal of Finance) – den FOMC; Krohn, Mueller, Whelan "
           "(2024, Journal of Finance) – fixingy; Breedon, Ranaldo (2013) – domácí hodiny; Lustig, Roussanov, "
           "Verdelhan (2014) – dolarový carry; Menkhoff a kol. (2012) – momentum a hodnota měn; analýzy bank "
           "(BofA, UBS, BNY) – vyvažování na konci měsíce. Data: 12 párů FXCM 2012–2026 (hodinové střední ceny), "
           "po nákladech (spread + skluz). Výnosy v % nominálu bez páky; × 30 = % marže._", ""]

    # ---------------------------------------------------------------- A. central bank days
    out += ["## A. Den rozhodnutí centrální banky", "", HEAD[0], HEAD[1]]

    def cb_day_returns(bank_dates, pairs, sign_of):
        items = []
        for d in sorted(bank_dates):
            vals = []
            for p in pairs:
                f = fx[p]
                try:
                    i = f["days"].index(d)
                except ValueError:
                    continue
                if i == 0:
                    continue
                r = (f["c"][i] / f["c"][i - 1] - 1) * 100 * sign_of(p) - 2 * cost_pct(p, f["c"][i])
                vals.append(r)
            if vals and date(2012, 1, 1) <= d <= date(2026, 12, 31):
                items.append((d, float(np.mean(vals))))
        return items
    fomc = cb_day_returns(banks["FED"], USD_PAIRS, lambda p: SIGN[p])
    out += period_rows("FOMC: proti dolaru (7 párů s USD), den rozhodnutí", fomc, 8)
    for bank, ccy in (("ECB", "EUR"), ("BOJ", "JPY"), ("BOE", "GBP")):
        p = [x for x in USD_PAIRS if FOREIGN[x] == ccy][0]
        out += period_rows(f"{bank}: {ccy} proti dolaru, den rozhodnutí", cb_day_returns(banks[bank], [p], lambda q: SIGN[q]), 8)
    # day before FOMC, day after
    shifted = []
    for d in sorted(banks["FED"]):
        f = fx["EUR/USD"]
        if d not in f["days"]:
            continue
        i = f["days"].index(d)
        for lab, k in (("před", i - 1), ("po", i + 1)):
            if 1 <= k < len(f["days"]):
                vals = [(fx[p]["c"][fx[p]["days"].index(f["days"][k])] / fx[p]["c"][fx[p]["days"].index(f["days"][k]) - 1] - 1)
                        * 100 * SIGN[p] - 2 * cost_pct(p, fx[p]["c"][-1]) for p in USD_PAIRS if f["days"][k] in fx[p]["days"]]
                shifted.append((lab, f["days"][k], float(np.mean(vals))))
    out += period_rows("FOMC: proti dolaru, den PŘED rozhodnutím", [(d, v) for lab, d, v in shifted if lab == "před"], 8)
    out += period_rows("FOMC: proti dolaru, den PO rozhodnutí", [(d, v) for lab, d, v in shifted if lab == "po"], 8)
    allday = []
    f0 = fx["EUR/USD"]
    fomc_set = set(banks["FED"])
    for i in range(1, len(f0["days"])):
        d = f0["days"][i]
        if d in fomc_set:
            continue
        vals = [(fx[p]["c"][j] / fx[p]["c"][j - 1] - 1) * 100 * SIGN[p] for p in USD_PAIRS
                for j in [fx[p]["days"].index(d)] if j > 0] if all(d in fx[p]["days"] for p in USD_PAIRS) else []
        if vals:
            allday.append((d, float(np.mean(vals))))
    out += period_rows("pro srovnání: proti dolaru v ostatní dny (bez nákladů)", allday, 252)

    # ---------------------------------------------------------------- B. month end
    out += ["", "## B. Konec měsíce: vyvažování podle akcií", "",
            "Signál 2 obchodní dny před koncem měsíce (zavření New York): výnos S&P 500 od začátku měsíce minus výnos "
            "domácího indexu měny. USA lepší → nákup měny proti dolaru, horší → prodej. Výstup v 16:00 Londýn "
            "posledního obchodního dne (fixing WM/R) nebo při zavření New York.", "", HEAD[0], HEAD[1]]
    sp = V.yahoo_daily("^GSPC")
    eq = {c: V.yahoo_daily(s) for c, s in EQUITY.items()}

    def mtd(series, start, upto):
        keys = sorted(series)
        a = [k for k in keys if k < start]
        b = [k for k in keys if k <= upto]
        if not a or not b:
            return None
        return series[b[-1]] / series[a[-1]] - 1

    for exit_kind in ("fix", "close"):
        for lead in (2, 1):
            per_pair, basket = defaultdict(list), defaultdict(list)
            for p in USD_PAIRS:
                f = fx[p]
                days = f["days"]
                months = defaultdict(list)
                for i, d in enumerate(days):
                    months[(d.year, d.month)].append(i)
                for (y, m), idx in sorted(months.items()):
                    if len(idx) < 10:
                        continue
                    last, sig_i = idx[-1], idx[-1 - lead]
                    start = date(y, m, 1)
                    a, b = mtd(sp, start, days[sig_i]), mtd(eq[FOREIGN[p]], start, days[sig_i])
                    if a is None or b is None or a == b:
                        continue
                    side = np.sign(a - b) * SIGN[p]          # +1 = buy the pair
                    entry = f["c"][sig_i]
                    if exit_kind == "close":
                        exitp = f["c"][last]
                    else:
                        d_last = days[last]
                        fix = datetime(d_last.year, d_last.month, d_last.day, 16, tzinfo=LONDON).timestamp()
                        k = np.searchsorted(f["ts"], fix - 3600)     # bar 15:00-16:00 London
                        if k >= len(f["ts"]) or abs(f["ts"][k] - (fix - 3600)) > 1:
                            continue
                        exitp = f["hc"][k]
                    r = side * (exitp / entry - 1) * 100 - 2 * cost_pct(p, entry)
                    per_pair[p].append((days[last], r))
                    basket[days[last]].append(r)
            label = f"vstup {lead} d před koncem, výstup {'ve fixingu 16:00 Londýn' if exit_kind == 'fix' else 'při zavření NY'}"
            out += period_rows(f"7 párů dohromady, {label}", [(d, float(np.mean(v))) for d, v in sorted(basket.items())], 12)
            if exit_kind == "fix" and lead == 2:
                for p in USD_PAIRS:
                    out += period_rows(f"&nbsp;&nbsp;{p}", per_pair[p], 12)

    # ---------------------------------------------------------------- C. intraday
    out += ["", "## C. Hodinové vzorce", "",
            "Dolar proti 7 měnám (průměr), výnos v daném okně každý obchodní den, po nákladech na jeden obchod "
            "(vstup + výstup). Časy jsou londýnské / tokijské místní.", "", HEAD[0], HEAD[1]]

    def window_items(pairs, sign_of, tz, h1, h2, cost=True):
        """Return per day of the move from local time h1 to h2 (bars closing at those hours)."""
        items = defaultdict(list)
        for p in pairs:
            f = fx[p]
            ts, hc = f["ts"], f["hc"]
            pos = {int(t): k for k, t in enumerate(ts)}
            for d in f["days"]:
                t1 = datetime(d.year, d.month, d.day, h1, tzinfo=tz).timestamp() - 3600   # bar ending at h1
                t2 = datetime(d.year, d.month, d.day, h2, tzinfo=tz).timestamp() - 3600
                k1, k2 = pos.get(int(t1)), pos.get(int(t2))
                if k1 is None or k2 is None:
                    continue
                r = (hc[k2] / hc[k1] - 1) * 100 * sign_of(p) - (2 * cost_pct(p, hc[k1]) if cost else 0)
                items[d].append(r)
        return [(d, float(np.mean(v))) for d, v in sorted(items.items()) if len(v) >= len(pairs) // 2]
    usd_long = lambda p: -SIGN[p]                                  # noqa: E731  (+ = USD up)
    for lab, tz, h1, h2, sgn in (("Londýn 14→16 h: koupit dolar před fixingem", LONDON, 14, 16, usd_long),
                                 ("Londýn 16→18 h: prodat dolar po fixingu", LONDON, 16, 18, lambda p: SIGN[p]),
                                 ("Londýn 16→20 h: prodat dolar po fixingu", LONDON, 16, 20, lambda p: SIGN[p]),
                                 ("Tokio 8→10 h: koupit dolar před fixingem 9:55", ZoneInfo("Asia/Tokyo"), 8, 10, usd_long),
                                 ("Tokio 10→13 h: prodat dolar po fixingu", ZoneInfo("Asia/Tokyo"), 10, 13, lambda p: SIGN[p])):
        out += period_rows(lab, window_items(USD_PAIRS, sgn, tz, h1, h2), 252)
        out += period_rows("&nbsp;&nbsp;totéž bez nákladů", window_items(USD_PAIRS, sgn, tz, h1, h2, cost=False), 252)
    for lab, pair, tz, h1, h2, sgn in (
            ("EUR/USD: prodat euro v evropských hodinách (Londýn 8→13 h)", "EUR/USD", LONDON, 8, 13, -1),
            ("EUR/USD: koupit euro v amerických hodinách (New York 8→16 h)", "EUR/USD", NY, 8, 16, 1),
            ("USD/JPY: koupit dolar v tokijských hodinách (Tokio 9→15 h)", "USD/JPY", ZoneInfo("Asia/Tokyo"), 9, 15, 1),
            ("GBP/USD: prodat libru v londýnských hodinách (8→13 h)", "GBP/USD", LONDON, 8, 13, -1)):
        out += period_rows(lab, window_items([pair], lambda p, s=sgn: s, tz, h1, h2), 252)
        out += period_rows("&nbsp;&nbsp;totéž bez nákladů", window_items([pair], lambda p, s=sgn: s, tz, h1, h2, cost=False), 252)

    # ---------------------------------------------------------------- D/E. monthly currency portfolios
    rates = P.monthly_rates()
    ccys = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
    pair_of = {FOREIGN[p]: p for p in USD_PAIRS}
    month_ends = []
    f0 = fx["EUR/USD"]
    for i in range(1, len(f0["days"])):
        if f0["days"][i].month != f0["days"][i - 1].month:
            month_ends.append(f0["days"][i - 1])
    month_ends.append(f0["days"][-1])

    def level(ccy, d):
        """USD value of one unit of the currency at the close of day d (last close on or before d)."""
        p = pair_of[ccy]
        f = fx[p]
        k = int(np.searchsorted(np.array([x.toordinal() for x in f["days"]]), d.toordinal(), side="right")) - 1
        c = f["c"][k]
        return c if SIGN[p] > 0 else 1 / c

    lv = {c: np.array([level(c, d) for d in month_ends]) for c in ccys}
    fwd = {c: np.r_[lv[c][1:] / lv[c][:-1] - 1, np.nan] * 100 for c in ccys}          # next month spot return vs USD
    rate = {c: np.array([P.rate_at(rates[c], d.year, d.month, 2) or np.nan for d in month_ends]) for c in ccys + ["USD"]}
    leg_cost = {c: 2 * cost_pct(pair_of[c], fx[pair_of[c]]["c"][-1]) for c in ccys}
    out += ["", "## D. Dolarový carry a E. pořadí měn (měsíčně)", "",
            "Výnos za měsíc včetně úrokového rozdílu (sazby OECD, zpoždění 2 měsíce) a nákladů.", "", HEAD[0], HEAD[1]]
    items = defaultdict(list)
    for k in range(len(month_ends) - 1):
        d = month_ends[k + 1]
        avg_f = np.nanmean([rate[c][k] for c in ccys])
        side = 1 if avg_f > rate["USD"][k] else -1                  # +1 = long the basket vs USD
        basket = np.mean([fwd[c][k] + (rate[c][k] - rate["USD"][k]) / 12 for c in ccys])
        items["D. dolarový carry"].append((d, side * basket - np.mean(list(leg_cost.values()))))
        # cross-sectional scores (USD included with 0 return and its own rate)
        scores = {}
        for name, look in (("momentum 3 měsíce", 3), ("momentum 12 měsíců", 12), ("hodnota (obrat 5 let)", 60)):
            if k < look:
                continue
            sc = {c: lv[c][k] / lv[c][k - look] - 1 for c in ccys}
            sc["USD"] = 0.0
            if name.startswith("hodnota"):
                sc = {c: -v for c, v in sc.items()}
            scores[name] = sc
        sc = {c: rate[c][k] for c in ccys + ["USD"]}
        if not any(np.isnan(v) for v in sc.values()):
            scores["carry (sazby)"] = sc
        for name, sc in scores.items():
            order = sorted(sc, key=lambda c: sc[c])
            longs, shorts = order[-2:], order[:2]

            def ret(c):
                return 0.0 if c == "USD" else fwd[c][k] + (rate[c][k] - rate["USD"][k]) / 12
            r = 0.5 * sum(ret(c) for c in longs) - 0.5 * sum(ret(c) for c in shorts)
            r -= 0.5 * sum(leg_cost.get(c, 0) for c in longs + shorts)
            items[name].append((d, r))
    combo = defaultdict(list)
    for name in ("momentum 12 měsíců", "carry (sazby)", "hodnota (obrat 5 let)"):
        for d, v in items[name]:
            combo[d].append(v)
    items["E. kombinace carry + momentum 12 m + hodnota"] = [(d, float(np.mean(v))) for d, v in sorted(combo.items()) if len(v) == 3]
    for name, it in items.items():
        if np.isnan([v for _, v in it]).any():
            it = [(d, v) for d, v in it if not np.isnan(v)]
        out += period_rows(name, it, 12)
    text = "\n".join(out) + "\n"
    (PROJECT_ROOT / "docs" / "ANOMALIE.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
