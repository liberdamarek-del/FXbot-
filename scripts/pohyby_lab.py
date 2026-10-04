"""Why do the 12 pairs move so much every day? (descriptive research)

    python scripts/pohyby_lab.py        # -> docs/PROC_SE_TRHY_HYBOU.md

1. Size of the daily moves (close to close, high to low) in % of the price and in % of the margin
   at leverage 1:30, per pair and per year.
2. Hours of the day (New York time) in which the moves happen.
3. The largest days (top 5 % of |move| per pair): how many fall on a scheduled central bank decision
   (Fed, ECB, BoJ, BoE) or a US release (NFP, CPI, GDP, retail sales, PCE, PPI); "lift" = how much more
   often than on an ordinary day; in which hour the biggest hourly move of that day happened.
4. What moves together on the same day: correlation and R^2 of the daily FX move with the same-day
   change of S&P 500, VIX, gold, oil, copper, US 10y yield and the 2y yield difference of the pair.
5. Does anything predict tomorrow: correlation of today's change of those markets with tomorrow's
   FX move; clustering of large days.
Descriptive only: nothing here enters the model.
"""

import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fundamenty as F  # noqa: E402
import vyzkum_data as V  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
LEV = 30
CB_OF = F.CB_OF                             # one map of the four central banks (fundamenty)
X_NAMES = ["sp500", "vix", "zlato", "ropa_wti", "med", "us10y", "nikkei", "stoxx50"]
X_CZ = {"sp500": "akcie USA (S&P 500)", "vix": "strach (VIX)", "zlato": "zlato", "ropa_wti": "ropa WTI",
        "med": "med", "us10y": "US 10letý výnos", "nikkei": "akcie Japonsko", "stoxx50": "akcie Evropa",
        "sazby2y": "rozdíl 2letých výnosů páru", "dolar_index": "dolarový index"}


def fmt(x, d=1):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def main() -> int:
    pairs = list(DEFAULT_ACTIVE)
    markets = {n: V.yahoo_daily(s) for n, s in V.MARKETS.items()}
    releases = V.us_release_dates()
    banks = V.cb_dates()
    ylds = V.yields()
    out = ["# Proč se měnové páry denně hýbou", "",
           "_12 párů, hodinová data FXCM 2012–2026 (střední ceny), denní svíčka končí v 17:00 New York. "
           "% marže = pohyb ceny × 30 (páka 1:30). Zprávy: rozhodnutí Fedu, ECB, BoJ, BoE a americké zprávy "
           "NFP, CPI, HDP, maloobchod, PCE, PPI (termíny z ALFRED). Jen popis, do modelu nic nepřechází._", ""]

    # ---------------------------------------------------------------- 1. size
    out += ["## 1. Jak velké jsou denní pohyby", "",
            "| pár | průměrný denní pohyb (zavření–zavření) | průměrný denní rozsah (max–min) | dní s rozsahem ≥ 1 % | "
            "dní s pohybem ≥ 1 % | rozsah v % marže |", "|---|---|---|---|---|---|"]
    data, yearly = {}, defaultdict(dict)
    for pair in pairs:
        f = V.fx(pair)
        c = f["c"]
        ret = np.full(len(c), np.nan)
        ret[1:] = (c[1:] / c[:-1] - 1) * 100
        rng = np.full(len(c), np.nan)
        rng[1:] = (f["h"][1:] - f["l"][1:]) / c[:-1] * 100
        data[pair] = (f, ret, rng)
        ok = ~np.isnan(ret)
        out.append(f"| {pair} | {np.mean(np.abs(ret[ok])):.2f} % | {np.mean(rng[ok]):.2f} % | {np.mean(rng[ok] >= 1):.0%} | "
                   f"{np.mean(np.abs(ret[ok]) >= 1):.0%} | {np.mean(rng[ok]) * LEV:.0f} % |")
        for y in range(2012, 2027):
            sel = np.array([d.year == y for d in f["days"]]) & ok
            if sel.any():
                yearly[pair][y] = np.mean(rng[sel])
    allr = np.concatenate([d[1][~np.isnan(d[1])] for d in data.values()])
    allg = np.concatenate([d[2][~np.isnan(d[2])] for d in data.values()])
    out += ["", f"Všech 12 párů: průměrný pohyb zavření–zavření **{np.mean(np.abs(allr)):.2f} %** "
            f"(= {np.mean(np.abs(allr)) * LEV:.0f} % marže), průměrný denní rozsah **{np.mean(allg):.2f} %** "
            f"(= {np.mean(allg) * LEV:.0f} % marže); rozsah aspoň 1 % má {np.mean(allg >= 1):.0%} dní, "
            f"pohyb zavření–zavření aspoň 1 % jen {np.mean(np.abs(allr) >= 1):.0%} dní.", "",
            "Průměrný denní rozsah podle let (%):", "",
            "| pár | " + " | ".join(str(y) for y in range(2012, 2027)) + " |", "|---|" + "---|" * 15]
    for pair in pairs:
        out.append(f"| {pair} | " + " | ".join(fmt(yearly[pair].get(y), 2) for y in range(2012, 2027)) + " |")

    # ---------------------------------------------------------------- 2. hours
    hour_abs = defaultdict(list)
    for pair in pairs:
        f = data[pair][0]
        ts, hc = f["ts"], f["hc"]
        r = np.abs(hc[1:] / hc[:-1] - 1) * 100
        good = (ts[1:] - ts[:-1]) == 3600
        hours = np.array([datetime.fromtimestamp(int(t), tz=NY).hour for t in ts[1:]])
        base = np.mean(r[good])
        for h in range(24):
            sel = good & (hours == h)
            if sel.any():
                hour_abs[h].append(np.mean(r[sel]) / base)
    out += ["", "## 2. V kterou hodinu se trh hýbe nejvíc", "",
            "Průměrný pohyb za hodinu vůči průměru dne (1,0 = průměr), čas New York (u nás +6 h):", "",
            "| hodina (New York) | " + " | ".join(f"{h:02d}" for h in range(24)) + " |", "|---|" + "---|" * 24,
            "| síla pohybu | " + " | ".join(fmt(np.mean(hour_abs[h]), 1) for h in range(24)) + " |", ""]
    top_hours = sorted(range(24), key=lambda h: -np.mean(hour_abs[h]))[:4]
    out.append("Nejsilnější hodiny: " + ", ".join(f"{h:02d}:00–{h + 1:02d}:00 New York (u nás {(h + 6) % 24:02d}:00)"
                                               for h in top_hours) + ". 08:30 New York = americké zprávy "
               "(NFP, CPI, HDP, maloobchod), 10:00 = další americká data, 14:00 = Fed, 02:00–04:00 = otevření "
               "Londýna a evropská data.")

    # ---------------------------------------------------------------- 3. largest days
    out += ["", "## 3. Největší dny: kolik z nich způsobily plánované zprávy", ""]
    kinds = ["centrální banka páru", "Fed", "ECB", "BoJ", "BoE"] + [f"USA: {k}" for k in releases] + ["jakákoli plánovaná zpráva"]
    big_hits, all_hits = Counter(), Counter()
    n_big, n_all = 0, 0
    top_hour_kind, share_top = Counter(), []
    per_pair_rows = []
    for pair in pairs:
        f, ret, rng = data[pair]
        inst = get_instrument(pair)
        ok = ~np.isnan(ret)
        thr = np.nanpercentile(np.abs(ret), 95)
        big = ok & (np.abs(ret) >= thr)
        pb, pa = Counter(), Counter()
        for i, d in enumerate(f["days"]):
            if not ok[i]:
                continue
            tags = set()
            for ccy in (inst.base, inst.quote):
                cb = CB_OF.get(ccy)
                if cb and d in banks[cb]:
                    tags |= {"centrální banka páru", {"FED": "Fed", "ECB": "ECB", "BOJ": "BoJ", "BOE": "BoE"}[cb]}
            if "USD" in (inst.base, inst.quote):
                for k, ds in releases.items():
                    if d in ds:
                        tags.add(f"USA: {k}")
            if tags:
                tags.add("jakákoli plánovaná zpráva")
            for t in tags:
                pa[t] += 1
                if big[i]:
                    pb[t] += 1
            if big[i]:
                a, b = f["first"][i], f["last"][i]
                hr = np.abs(f["hc"][a + 1:b + 1] / f["hc"][a:b] - 1) * 100
                if len(hr):
                    k = int(np.argmax(hr))
                    h = datetime.fromtimestamp(int(f["ts"][a + 1 + k]), tz=NY).hour
                    share_top.append(hr[k] / max(abs(ret[i]), 1e-9))
                    top_hour_kind[("08:00–09:00 (US data 8:30)" if h == 8 else "10:00–11:00 (US data 10:00)" if h == 10
                                   else "14:00–15:00 (Fed)" if h == 14 else "07:00–08:00 (ECB 7:45)" if h == 7
                                   else "02:00–06:00 (Evropa)" if 2 <= h <= 6 else "19:00–01:00 (Asie)" if h >= 19 or h <= 1
                                   else "jiná hodina")] += 1
        nb, na = int(big.sum()), int(ok.sum())
        n_big, n_all = n_big + nb, n_all + na
        big_hits.update(pb)
        all_hits.update(pa)
        any_b = pb["jakákoli plánovaná zpráva"] / nb if nb else 0
        any_a = pa["jakákoli plánovaná zpráva"] / na if na else 0
        per_pair_rows.append(f"| {pair} | {thr:.2f} % ({thr * LEV:.0f} % marže) | {any_b:.0%} | {any_a:.0%} | "
                             f"{any_b / any_a if any_a else 0:.1f}× |")
    out += ["Velký den = 5 % dní s největším pohybem zavření–zavření u daného páru.", "",
            "| pár | velký den od | velkých dní se zprávou | všech dní se zprávou | lift |", "|---|---|---|---|---|"]
    out += per_pair_rows
    out += ["", "Všech 12 párů dohromady (lift = kolikrát častěji je zpráva ve velkém dni než v obyčejném):", "",
            "| zpráva | ve velkých dnech | ve všech dnech | lift |", "|---|---|---|---|"]
    for k in kinds:
        if all_hits[k]:
            b, a = big_hits[k] / n_big, all_hits[k] / n_all
            out.append(f"| {k} | {b:.1%} | {a:.1%} | {b / a:.1f}× |")
    out += ["", "Ve které hodině se ve velkých dnech stal největší hodinový pohyb (čas New York):", "",
            "| hodina | podíl velkých dní |", "|---|---|"]
    for k, v in top_hour_kind.most_common():
        out.append(f"| {k} | {v / sum(top_hour_kind.values()):.0%} |")
    out += ["", f"Největší jediná hodina dělá u velkých dnů v mediánu **{np.median(share_top):.0%}** celodenního pohybu "
            "(zbytek se nasbírá postupně během dne)."]

    # ---------------------------------------------------------------- 4. same-day co-movement
    out += ["", "## 4. Co se hýbe spolu se měnami ve stejný den", "",
            "Korelace denního pohybu páru se stejnodenní změnou jiných trhů (1 = vždy stejně, −1 = vždy opačně, "
            "0 = žádný vztah). R² = jakou část denních pohybů páru vysvětlí všechny trhy dohromady.", "",
            "| pár | " + " | ".join(X_CZ[x] for x in X_NAMES + ["sazby2y"]) + " | R² všech |",
            "|---|" + "---|" * (len(X_NAMES) + 2)]
    lead_rows = []
    r2s = {}
    for pair in pairs:
        f, ret, _ = data[pair]
        inst = get_instrument(pair)
        days = f["days"]
        X = [V.aligned(markets[x], days, "pts" if x in V.LEVEL_CHANGE else "pct") for x in X_NAMES]
        yb = V.aligned(ylds[inst.base], days, "pts") if inst.base in ylds else np.zeros(len(days))
        yq = V.aligned(ylds[inst.quote], days, "pts") if inst.quote in ylds else np.zeros(len(days))
        X.append(yb - yq)
        X = np.column_stack(X)
        ok = ~np.isnan(ret) & ~np.isnan(X).any(axis=1)
        corrs = [np.corrcoef(X[ok, j], ret[ok])[0, 1] for j in range(X.shape[1])]
        A = np.column_stack([np.ones(ok.sum()), X[ok]])
        beta, *_ = np.linalg.lstsq(A, ret[ok], rcond=None)
        res = ret[ok] - A @ beta
        r2 = 1 - res.var() / ret[ok].var()
        r2s[pair] = r2
        out.append(f"| {pair} | " + " | ".join(f"{c:+.2f}" for c in corrs) + f" | **{r2:.0%}** |")
        # tomorrow
        nxt = np.full(len(ret), np.nan)
        nxt[:-1] = ret[1:]
        ok2 = ~np.isnan(nxt) & ~np.isnan(X).any(axis=1)
        lead = [np.corrcoef(X[ok2, j], nxt[ok2])[0, 1] for j in range(X.shape[1])]
        own = np.corrcoef(ret[ok2], nxt[ok2])[0, 1]
        lead_rows.append(f"| {pair} | " + " | ".join(f"{c:+.2f}" for c in lead) + f" | {own:+.2f} |")
    out += ["", f"V průměru vysvětlí stejnodenní pohyb akcií, VIX, zlata, ropy, mědi a výnosů **{np.mean(list(r2s.values())):.0%}** "
            "denních pohybů měn. Zbytek jsou zprávy a toky specifické pro danou měnu (a náhoda)."]

    # ---------------------------------------------------------------- 5. predicting tomorrow
    out += ["", "## 5. Předpovídá dnešek zítřek?", "",
            "Korelace dnešní změny trhu se ZÍTŘEJŠÍM pohybem páru (poslední sloupec = dnešní pohyb páru). "
            "Hodnoty kolem ±0,05 jsou prakticky nula.", "",
            "| pár | " + " | ".join(X_CZ[x] for x in X_NAMES + ["sazby2y"]) + " | sám pár |",
            "|---|" + "---|" * (len(X_NAMES) + 2)] + lead_rows
    clus = []
    for pair in pairs:
        _, ret, rng = data[pair]
        a = np.abs(ret)
        ok = ~np.isnan(a[1:]) & ~np.isnan(a[:-1])
        thr = np.nanpercentile(a, 90)
        big_t = a[:-1][ok] >= thr
        big_n = a[1:][ok] >= thr
        clus.append((np.corrcoef(a[:-1][ok], a[1:][ok])[0, 1], np.mean(big_n[big_t]), np.mean(big_n)))
    out += ["", "Shlukování: po velkém dni (horních 10 %) přijde další velký den s pravděpodobností "
            f"**{np.mean([c[1] for c in clus]):.0%}** (běžně {np.mean([c[2] for c in clus]):.0%}); korelace velikosti "
            f"dnešního a zítřejšího pohybu {np.mean([c[0] for c in clus]):+.2f}. Velikost pohybu se tedy předvídat dá "
            "(klidné a divoké období), směr skoro ne.", ""]
    text = "\n".join(out) + "\n"
    (PROJECT_ROOT / "docs" / "PROC_SE_TRHY_HYBOU.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
