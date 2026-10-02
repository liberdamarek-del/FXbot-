"""Do indicators that worked on a pair in the last months keep working for the
next 14 days / month / half year? (the user's question, 2026-10-02)

    python scripts/kratke_okno_lab.py          # -> docs/KRATKE_OKNO.md

Library of daily signals per pair, decided at the New York close with data known then:
- technical: momentum / reversal over 1, 5, 20, 60, 120 days, RSI(2) extremes (fade or follow),
  20-day z-score (fade or follow), 20-day breakout (follow or fade), SMA20 vs SMA50, price vs SMA200,
  a big day > 1.5 ATR (follow or fade the news-like move);
- fundamental: carry (OECD rate difference, 2 months back), its 3-month change, 5- and 20-day change of
  the 2-year yield difference (known with a one-day lag), a big move on a central bank / US release day
  (follow or fade);
- other markets: today's and 5-day change of S&P 500, VIX, gold, WTI oil, copper, US 10y yield,
  Nikkei, Euro Stoxx (both orientations).
Each signal x holding period (1, 5, 10, 20 days) gives a daily result series (staggered positions,
costs = half spread + slippage on every change of position), in % of the price.

Short-window test (walk-forward, nothing seen in advance): every M trading days (10 = ~14 days,
21 = month, 126 = half year) choose for each pair the signal with the best Sharpe ratio over the last
L days (63 / 126 / 252), if it is > 1, and trade it for the next M days. The out-of-sample result is
compared with random choices (500 runs) and with the "information coefficient" (rank correlation
between the last window's and the next window's results over all signals). Also pooled over all
pairs (the best signals of the whole sample). Descriptive research: nothing enters the model.
"""

import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_lab2 as P  # noqa: E402
import strategy_mining as SM  # noqa: E402
import vyzkum_data as V  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

HOLDS = (1, 5, 10, 20)
REBAL = {"14 dní": 10, "měsíc": 21, "půl roku": 126}
LOOKS = {"3 měsíce": 63, "6 měsíců": 126, "1 rok": 252}
CROSS = ["sp500", "vix", "zlato", "ropa_wti", "med", "us10y", "nikkei", "stoxx50"]
CB_OF = {"USD": "FED", "EUR": "ECB", "JPY": "BOJ", "GBP": "BOE"}
RNG = np.random.default_rng(7)
LEV = 30


def sgn(x):
    return np.nan_to_num(np.sign(x))


def roll_mean(x, n):
    out = np.full(len(x), np.nan)
    cs = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def roll_std(x, n):
    m = roll_mean(x, n)
    m2 = roll_mean(x * x, n)
    return np.sqrt(np.maximum(m2 - m * m, 0))


def signals(pair: str, f: dict, markets: dict, ylds: dict, rates: dict, events: set) -> dict:
    c, h, l_ = f["c"], f["h"], f["l"]
    n = len(c)
    days = f["days"]
    inst = get_instrument(pair)
    S = {}
    r = np.zeros(n)
    r[1:] = c[1:] / c[:-1] - 1
    for k in (1, 5, 20, 60, 120):
        m = np.zeros(n)
        m[k:] = c[k:] / c[:-k] - 1
        S[f"trend {k} dní"] = sgn(m)
        S[f"obrat {k} dní"] = -sgn(m)
    rsi2 = np.nan_to_num(SM.rsi(c, 2), nan=50)
    S["RSI(2) obrat"] = np.where(rsi2 < 10, 1, np.where(rsi2 > 90, -1, 0))
    S["RSI(2) trend"] = -S["RSI(2) obrat"]
    z = (c - roll_mean(c, 20)) / np.where(roll_std(c, 20) > 0, roll_std(c, 20), np.nan)
    z = np.nan_to_num(z)
    S["z20 obrat"] = np.where(z < -2, 1, np.where(z > 2, -1, 0))
    S["z20 trend"] = -S["z20 obrat"]
    hi = np.array([c[max(0, i - 20):i].max() if i >= 20 else np.inf for i in range(n)])
    lo = np.array([c[max(0, i - 20):i].min() if i >= 20 else -np.inf for i in range(n)])
    S["průraz 20 dní"] = np.where(c > hi, 1, np.where(c < lo, -1, 0))
    S["průraz 20 dní obrat"] = -S["průraz 20 dní"]
    S["SMA20 nad SMA50"] = sgn(roll_mean(c, 20) - roll_mean(c, 50))
    S["SMA20 pod SMA50"] = -S["SMA20 nad SMA50"]
    S["cena nad SMA200"] = sgn(c - roll_mean(c, 200))
    S["cena pod SMA200"] = -S["cena nad SMA200"]
    atr = np.nan_to_num(SM.wilder(SM.true_range(h, l_, c), 14), nan=np.inf)
    move = np.zeros(n)
    move[1:] = c[1:] - c[:-1]
    big = np.abs(move) > 1.5 * np.r_[np.inf, atr[:-1]]
    S["velký den – následovat"] = np.where(big, sgn(move), 0)
    S["velký den – proti"] = -S["velký den – následovat"]
    ev = np.array([d in events for d in days])
    evbig = ev & (np.abs(move) > 0.5 * np.r_[np.inf, atr[:-1]])
    S["zpráva – následovat"] = np.where(evbig, sgn(move), 0)
    S["zpráva – proti"] = -S["zpráva – následovat"]
    # fundamentals (rates of the model: OECD, 2 months back)
    carry, mom = np.zeros(n), np.zeros(n)
    for i, d in enumerate(days):
        kb, kq = (P.rate_at(rates[x], d.year, d.month, 2) for x in (inst.base, inst.quote))
        ob, oq = (P.rate_at(rates[x], d.year, d.month, 5) for x in (inst.base, inst.quote))
        if None not in (kb, kq, ob, oq):
            carry[i] = kb - kq
            mom[i] = (kb - kq) - (ob - oq)
    S["carry"] = sgn(carry)
    S["proti carry"] = -S["carry"]
    S["sazby rostou (3 m)"] = np.where(np.abs(mom) >= 0.1, sgn(mom), 0)
    S["sazby rostou – proti"] = -S["sazby rostou (3 m)"]
    if inst.base in ylds and inst.quote in ylds:
        diff = np.full(n, np.nan)
        kb_, kq_ = ylds[inst.base], ylds[inst.quote]
        db, dq = sorted(kb_), sorted(kq_)
        import bisect
        for i, d in enumerate(days):                  # value of the previous calendar day (published by then)
            jb, jq = bisect.bisect_left(db, d) - 1, bisect.bisect_left(dq, d) - 1
            if jb >= 0 and jq >= 0:
                diff[i] = kb_[db[jb]] - kq_[dq[jq]]
        for k in (5, 20):
            ch = np.zeros(n)
            ch[k:] = diff[k:] - diff[:-k]
            S[f"2leté výnosy {k} dní"] = sgn(np.nan_to_num(ch))
            S[f"2leté výnosy {k} dní – proti"] = -S[f"2leté výnosy {k} dní"]
    for x in CROSS:
        ser = markets[x]
        ch1 = np.nan_to_num(V.aligned(ser, days, "pts" if x in V.LEVEL_CHANGE else "pct"))
        S[f"{x} dnes +"] = sgn(ch1)
        S[f"{x} dnes −"] = -sgn(ch1)
        keys = sorted(ser)
        idx = {d: k for k, d in enumerate(keys)}
        ch5 = np.zeros(n)
        for i, d in enumerate(days):
            k = idx.get(d)
            if k is not None and k >= 5:
                a, b = ser[keys[k - 5]], ser[d]
                ch5[i] = (b / a - 1) if x not in V.LEVEL_CHANGE else b - a
        S[f"{x} 5 dní +"] = sgn(ch5)
        S[f"{x} 5 dní −"] = -sgn(ch5)
    return S


def daily_pnl(sig: np.ndarray, ret_next: np.ndarray, hold: int, cost: float) -> np.ndarray:
    """Staggered positions: each day 1/hold of the capital follows that day's signal for `hold` days.
    Position decided at close t earns the move t -> t+1 (ret_next[t]); costs on every change."""
    pos = roll_mean(sig.astype(float), hold) if hold > 1 else sig.astype(float)
    pos = np.nan_to_num(pos)
    turn = np.abs(np.diff(np.r_[0.0, pos]))
    return pos * ret_next - turn * cost


def sharpe(x):
    s = x.std()
    return 0.0 if s == 0 else x.mean() / s * np.sqrt(252)


def main() -> int:
    started = time.monotonic()
    pairs = list(DEFAULT_ACTIVE)
    markets = {n: V.yahoo_daily(s) for n, s in V.MARKETS.items()}
    ylds = V.yields()
    rates = P.monthly_rates()
    banks = V.cb_dates()
    releases = V.us_release_dates()
    names, pnl, meta = [], [], []
    common = None
    per_pair = {}
    for pair in pairs:
        f = V.fx(pair)
        inst = get_instrument(pair)
        ev = set()
        for ccy in (inst.base, inst.quote):
            if ccy in CB_OF:
                ev |= banks[CB_OF[ccy]]
        if "USD" in (inst.base, inst.quote):
            for ds in releases.values():
                ev |= ds
        S = signals(pair, f, markets, ylds, rates, ev)
        c = f["c"]
        ret_next = np.zeros(len(c))
        ret_next[:-1] = (c[1:] / c[:-1] - 1) * 100
        cost = (P.SPREAD_PIPS[pair] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip / np.median(c) * 100
        per_pair[pair] = (f["days"], S, ret_next, cost)
        days_set = set(f["days"])
        common = days_set if common is None else common & days_set
        print(f"{pair}: {len(S)} signalu, {time.monotonic() - started:.0f} s", flush=True)
    days = sorted(common)
    for pair, (pdays, S, ret_next, cost) in per_pair.items():
        idx = np.array([pdays.index(d) for d in days]) if len(pdays) != len(days) else np.arange(len(days))
        for name, sig in S.items():
            for hold in HOLDS:
                x = daily_pnl(sig, ret_next, hold, cost)[idx]
                pnl.append(x)
                names.append(f"{pair} | {name} | {hold} d")
                meta.append((pair, name, hold))
    pnl = np.array(pnl)                                     # combos x days, % of the price per day
    years = np.array([d.year for d in days])
    print(f"{pnl.shape[0]} kombinaci x {pnl.shape[1]} dni, {time.monotonic() - started:.0f} s", flush=True)
    out = ["# Krátkodobé ukazatele po párech: funguje to, co fungovalo posledně?", "",
           f"_12 párů, denní data 2012–2026 ({len(days)} společných obchodních dní), "
           f"{len({m[1] for m in meta})} signálů (technické, fundamentální, jiné trhy) × doby držení "
           f"{', '.join(str(h) for h in HOLDS)} dní = {pnl.shape[0]} kombinací pár × signál × držení. "
           "Výsledky po nákladech (spread + skluz), rozhoduje se při zavření v New Yorku jen z toho, co je tehdy "
           "známé. Sharpe = roční výnos / roční kolísání (0,5 slušné, 1 výborné). Jen výzkum – do modelu nic "
           "nepřechází._", ""]

    # ---------------------------------------------------------------- full sample per pair, stability
    periods = {"2012-18": (2012, 2018), "2019-22": (2019, 2022), "2023-26": (2023, 2026)}
    shp = {p: np.array([sharpe(x[(years >= a) & (years <= b)]) for x in pnl]) for p, (a, b) in periods.items()}
    stable = np.all([shp[p] > 0.3 for p in periods], axis=0)
    out += ["## 1. Pevné ukazatele za celé období (pro srovnání)", "",
            f"Kombinací se Sharpe > 0,3 ve všech třech obdobích: **{int(stable.sum())} z {pnl.shape[0]}** "
            f"(náhodou by se čekalo zhruba {pnl.shape[0] * 0.2 ** 3:.0f}–{pnl.shape[0] * 0.25 ** 3:.0f}).", "",
            "| pár | signál | držení | Sharpe 2012-18 | 2019-22 | 2023-26 | průměr na den v % marže |",
            "|---|---|---|---|---|---|---|"]
    order = np.argsort(-np.min([shp[p] for p in periods], axis=0))
    for k in order[:25]:
        pair, name, hold = meta[k]
        out.append(f"| {pair} | {name} | {hold} d | " + " | ".join(f"{shp[p][k]:+.2f}" for p in periods)
                   + f" | {pnl[k].mean() * LEV:+.2f} % |")

    # ---------------------------------------------------------------- information coefficient
    out += ["", "## 2. Pokračuje to, co fungovalo posledně? (informační koeficient)", "",
            "Pro každé datum: pořadí všech kombinací podle výsledku za posledních L dní a podle výsledku za "
            "dalších M dní. Korelace pořadí (IC) > 0 = co fungovalo, funguje dál; 0 = náhoda. t > 2 = spolehlivé.", "",
            "| zpětné okno | dalších 14 dní | další měsíc | dalšího půl roku |", "|---|---|---|---|"]
    cs = np.cumsum(np.c_[np.zeros(pnl.shape[0]), pnl], axis=1)
    cs2 = np.cumsum(np.c_[np.zeros(pnl.shape[0]), pnl * pnl], axis=1)

    def window_sharpe(a, b):
        nn = b - a
        m = (cs[:, b] - cs[:, a]) / nn
        v = (cs2[:, b] - cs2[:, a]) / nn - m * m
        return np.where(v > 0, m / np.sqrt(np.maximum(v, 1e-18)) * np.sqrt(252), 0.0)

    def rank(x):
        r = np.empty(len(x))
        r[np.argsort(x)] = np.arange(len(x))
        return r
    ic_rows = {}
    for lname, L in LOOKS.items():
        cells = []
        for mname, M in REBAL.items():
            ics = []
            for t in range(L, len(days) - M, M):
                past = window_sharpe(t - L, t)
                fut = (cs[:, t + M] - cs[:, t]) / M
                ics.append(np.corrcoef(rank(past), rank(fut))[0, 1])
            ics = np.array(ics)
            tstat = ics.mean() / ics.std() * np.sqrt(len(ics)) if ics.std() > 0 else 0
            ic_rows[(lname, mname)] = (ics.mean(), tstat)
            cells.append(f"{ics.mean():+.3f} (t {tstat:+.1f})")
        out.append(f"| {lname} | " + " | ".join(cells) + " |")

    # ---------------------------------------------------------------- walk-forward selection
    out += ["", "## 3. Strategie „vyber nejlepší ukazatel za poslední období a obchoduj ho dál“", "",
            "Pro každý pár zvlášť: každých M dní vyber kombinaci s nejlepším Sharpe za posledních L dní (jen když "
            "je > 1), obchoduj ji dalších M dní; 12 párů se stejnou vahou. Výsledek jen na datech, která výběr "
            "neviděl (2013–2026). Náhodný výběr = 500 běhů, kdy se místo nejlepší vybere náhodná kombinace "
            "téhož páru; p = podíl náhodných běhů, které dopadly stejně nebo lépe.", "",
            "| zpětné okno | obnova | Sharpe | roční výnos (% ceny, bez páky) | dní v obchodu | 2013-18 | 2019-22 | 2023-26 | "
            "náhodný výběr (průměr) | p |", "|---|---|---|---|---|---|---|---|---|---|"]
    pair_idx = defaultdict(list)
    for k, m in enumerate(meta):
        pair_idx[m[0]].append(k)
    best_cfg = None
    yrs = years
    for lname, L in LOOKS.items():
        for mname, M in REBAL.items():
            starts = list(range(L, len(days) - 1, M))
            sel = np.zeros(len(days))
            active = np.zeros(len(days))
            rnd = np.zeros((500, len(days)))
            for t in starts:
                e = min(t + M, len(days))
                past = window_sharpe(t - L, t)
                for pair, ks in pair_idx.items():
                    ks = np.array(ks)
                    best = ks[np.argmax(past[ks])]
                    if past[best] > 1.0:
                        sel[t:e] += pnl[best, t:e] / len(pair_idx)
                        active[t:e] += 1 / len(pair_idx)
                        picks = RNG.choice(ks, 500)
                        rnd[:, t:e] += pnl[picks, t:e] / len(pair_idx)
            span = slice(LOOKS["1 rok"], len(days))            # same evaluation period for every row
            s_sel = sharpe(sel[span])
            s_rnd = np.array([sharpe(r[span]) for r in rnd])
            per = [sharpe(sel[span][(yrs[span] >= a) & (yrs[span] <= b)])
                   for a, b in ((2013, 2018), (2019, 2022), (2023, 2026))]
            p = float(np.mean(s_rnd >= s_sel))
            out.append(f"| {lname} | {mname} | **{s_sel:+.2f}** | {sel[span].mean() * 252:+.1f} % | "
                       f"{active[span].mean():.0%} | " + " | ".join(f"{x:+.2f}" for x in per)
                       + f" | {s_rnd.mean():+.2f} | {p:.2f} |")
            if best_cfg is None or s_sel > best_cfg[0]:
                best_cfg = (s_sel, lname, mname, p, per)

    # ---------------------------------------------------------------- per pair walk-forward
    out += ["", "## 4. Po jednotlivých párech (výběr za posledních 6 měsíců, obnova každý měsíc)", "",
            "| pár | Sharpe mimo vzorek | 2013-18 | 2019-22 | 2023-26 | nejčastěji vybraný signál |", "|---|---|---|---|---|---|"]
    L, M = LOOKS["6 měsíců"], REBAL["měsíc"]
    for pair, ks in pair_idx.items():
        ks = np.array(ks)
        sel = np.zeros(len(days))
        chosen = defaultdict(int)
        for t in range(L, len(days) - 1, M):
            e = min(t + M, len(days))
            past = window_sharpe(t - L, t)
            best = ks[np.argmax(past[ks])]
            if past[best] > 1.0:
                sel[t:e] = pnl[best, t:e]
                chosen[meta[best][1] + f" ({meta[best][2]} d)"] += 1
        span = slice(LOOKS["1 rok"], len(days))
        per = [sharpe(sel[span][(yrs[span] >= a) & (yrs[span] <= b)]) for a, b in ((2013, 2018), (2019, 2022), (2023, 2026))]
        top = max(chosen.items(), key=lambda kv: kv[1]) if chosen else ("-", 0)
        out.append(f"| {pair} | **{sharpe(sel[span]):+.2f}** | " + " | ".join(f"{x:+.2f}" for x in per)
                   + f" | {top[0]} ({top[1]}×) |")

    # ---------------------------------------------------------------- pooled
    out += ["", "## 5. Celý vzorek najednou (nejlepších 5 kombinací ze všech párů)", "",
            "| zpětné okno | obnova | Sharpe mimo vzorek | 2013-18 | 2019-22 | 2023-26 |", "|---|---|---|---|---|---|"]
    for lname, L in LOOKS.items():
        for mname, M in REBAL.items():
            sel = np.zeros(len(days))
            for t in range(L, len(days) - 1, M):
                e = min(t + M, len(days))
                past = window_sharpe(t - L, t)
                top = np.argsort(-past)[:5]
                top = top[past[top] > 1.0]
                if len(top):
                    sel[t:e] = pnl[top, t:e].mean(axis=0)
            span = slice(LOOKS["1 rok"], len(days))
            per = [sharpe(sel[span][(yrs[span] >= a) & (yrs[span] <= b)]) for a, b in ((2013, 2018), (2019, 2022), (2023, 2026))]
            out.append(f"| {lname} | {mname} | **{sharpe(sel[span]):+.2f}** | " + " | ".join(f"{x:+.2f}" for x in per) + " |")

    # ---------------------------------------------------------------- the S&P lead found in docs/PROC_SE_TRHY_HYBOU.md
    out += ["", "## 6. Dnešní akcie USA → zítřejší měna (nález z analýzy pohybů)", "",
            "| pár | signál | držení | Sharpe 2012-18 | 2019-22 | 2023-26 | průměr na den v % marže |", "|---|---|---|---|---|---|---|"]
    for k, (pair, name, hold) in enumerate(meta):
        if name.startswith("sp500 dnes") and hold == 1 and pair in ("EUR/USD", "GBP/USD", "USD/CHF", "USD/JPY", "AUD/USD"):
            if (pair in ("EUR/USD", "GBP/USD", "AUD/USD")) == name.endswith("+"):
                out.append(f"| {pair} | {name} | {hold} d | " + " | ".join(f"{shp[p][k]:+.2f}" for p in periods)
                           + f" | {pnl[k].mean() * LEV:+.3f} % |")
    out += ["", f"_výpočet {time.monotonic() - started:.0f} s_"]
    text = "\n".join(out) + "\n"
    (PROJECT_ROOT / "docs" / "KRATKE_OKNO.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
