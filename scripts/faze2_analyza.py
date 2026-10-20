"""Faze 2 (R-049): co zbyde ze sampionovych vysledku po korekci na vicenasobne testovani.

    python scripts/faze2_analyza.py sampioni            # rady mesicnich vynosu obou sampionu + DSR podle poctu pokusu
    python scripts/faze2_analyza.py varianty [--jader N]  # kazdy pokus z EXPERIMENTS aplikovany na sampiona + PBO (CSCV)
    python scripts/faze2_analyza.py zprava              # shrnuti z ulozenych vysledku (docs/FAZE2_TABULKY.md)

Pozorovani = mesic. Rada vynosu = mesicni vynosy uctu ve DVOU testovacich oknech brany (2019-2022 s marzemi vybranymi na
2012-2018, 2023 az 2026-09 s marzemi vybranymi na 2012-2022), tedy presne to, co brana videla pri rozhodovani. Data od
2026-10-01 jsou v trezoru (src/core/trezor.py) a sem se nedostanou. Mesicni vynos = vysledek uzavrenych obchodu v mesici /
kapital na zacatku jeho prvniho uzavreni (scripts/portfolio_sim.run_portfolio, 'month_returns').

Vysledky: learning/hygiena/faze2_vysledky.json (sledovano v gitu). Nic z toho nemeni sampiona ani brany.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import registr_pokusu as RP  # noqa: E402
import self_learn as SL  # noqa: E402
from src.core import ledger as LG  # noqa: E402
from src.core import statistika as ST  # noqa: E402
from src.core import trezor as TZ  # noqa: E402

OUT = PROJECT_ROOT / "learning" / "hygiena" / "faze2_vysledky.json"
TABLES = PROJECT_ROOT / "docs" / "FAZE2_TABULKY.md"
N_SENSITIVITY = (1, 10, 30, 100, 288, 332, 1000, 5000)       # how many independent trials the best result was picked from
LAST_MONTH = (2026, 9)                                       # the last full month before the vault (2026-10-01)


def window_months(years: tuple) -> list[str]:
    y0, y1 = years
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            if (y, m) <= LAST_MONTH:
                out.append(f"{y}-{m:02d}")
    return out


def monthly_series(cfg: dict) -> dict:
    """Walk-forward monthly returns of a configuration in the gate's two test windows, plus the numbers the gate shows."""
    base = SL.trade_lists(cfg)
    out = {"mesice": [], "vynosy": [], "okna": {}}
    for k, (sel, test) in enumerate(SL.SPLITS):
        lists = SL.split_lists(base, cfg, k)
        cagr, sh, _ = SL.fit_shares(lists, cfg, sel)
        if sh is None:
            out["okna"][str(k)] = None
            continue
        r = SL.run_pf(lists, sh, test, cfg)
        by_month = dict(zip(r["months"], r["month_returns"]))
        months = window_months(test)
        out["mesice"] += months
        out["vynosy"] += [float(by_month.get(m, 0.0)) for m in months]
        out["okna"][str(k)] = {"marze": list(sh), "rocne": float(r["cagr"]), "propad": float(r["max_dd"]),
                               "obchodu_rocne": float(r["n_year"]), "mesicu": len(months)}
    return out


def describe(series: dict, n_list=N_SENSITIVITY) -> dict:
    x = np.array(series["vynosy"], float)
    if len(x) < 24 or float(x.std()) == 0:
        return {"t": len(x), "pozn": "prazdna nebo konstantni rada"}
    base = ST.dsr_of_series(x, 1)
    rows = {str(n): ST.dsr_of_series(x, n) for n in n_list}
    return {"t": len(x), "sr_mesicni": base["sr"], "sr_rocni": base["sr"] * np.sqrt(12), "sikmost": base["skew"],
            "spicatost": base["kurt"], "psr0": base["psr0"], "prumer_mesicni": float(x.mean()),
            "sm_odchylka_mesicni": float(x.std(ddof=1)), "nejhorsi_mesic": float(x.min()),
            "dsr_podle_poctu_pokusu": {n: {"sr0": r["sr0"], "dsr": r["dsr"]} for n, r in rows.items()}}


def champion_cfg(profile: str) -> dict:
    return json.loads(SL.PROFILES[profile]["state"].read_text())["config"]


def bootstrap_sr(x, n=4000, seed=7) -> dict:
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    srs = np.array([ST.sharpe(rng.choice(x, len(x), replace=True)) for _ in range(n)])
    return {"p05": float(np.percentile(srs, 5)), "p50": float(np.percentile(srs, 50)), "p95": float(np.percentile(srs, 95)),
            "podil_zaporny": float(np.mean(srs <= 0))}


def run_champions() -> dict:
    out = {}
    for profile in SL.PROFILES:
        SL.PROFILE = SL.PROFILES[profile]
        t0 = time.monotonic()
        s = monthly_series(champion_cfg(profile))
        d = describe(s)
        d["sr_bootstrap_mesicni"] = bootstrap_sr(s["vynosy"])
        out[profile] = {"nazev": champion_cfg(profile)["name"], "rada": s, "popis": d, "sekund": round(time.monotonic() - t0, 1)}
        print(f"{profile}: T={d['t']} SR mesicni {d['sr_mesicni']:.3f} (rocni {d['sr_rocni']:.2f}), "
              f"DSR(N=332) {d['dsr_podle_poctu_pokusu']['332']['dsr']:.3f}", flush=True)
    return out


# ---------------------------------------------------------------- varianty (PBO)
def _variant_job(job):
    profile, name = job
    SL.PROFILE = SL.PROFILES[profile]
    try:
        make = {n: m for n, _, m in SL.EXPERIMENTS}[name]
        cfg = make(copy.deepcopy(champion_cfg(profile)))
        key = hashlib.sha256(json.dumps(cfg, sort_keys=True, default=repr).encode()).hexdigest()
        s = monthly_series(cfg)
        return profile, name, {"klic": key, "rada": s, "popis": describe(s)}
    except Exception as exc:                                  # a trial that cannot be applied to the champion
        return profile, name, {"chyba": f"{type(exc).__name__}: {exc}"}


def run_variants(cores: int) -> dict:
    import multiprocessing as mp
    names = [n for n, _, _ in SL.EXPERIMENTS]
    jobs = [(p, n) for p in SL.PROFILES for n in names]
    out = {p: {} for p in SL.PROFILES}
    started = time.monotonic()
    with mp.Pool(cores, maxtasksperchild=12) as pool:
        for k, (profile, name, res) in enumerate(pool.imap_unordered(_variant_job, jobs), 1):
            out[profile][name] = res
            if k % 10 == 0 or k == len(jobs):
                print(f"{k}/{len(jobs)} variant, {time.monotonic() - started:.0f} s", flush=True)
    return out


def pbo_for(champion: dict, variants: dict, blocks=(8, 10, 12, 16)) -> dict:
    cols, labels, seen = [champion["rada"]["vynosy"]], ["__sampion__"], set()
    for name, v in sorted(variants.items()):
        if "chyba" in v or v["klic"] in seen or not any(v["rada"]["vynosy"]):
            continue                                           # not applicable, duplicate configuration, never trades
        seen.add(v["klic"])
        cols.append(v["rada"]["vynosy"])
        labels.append(name)
    n_months = min(len(c) for c in cols)
    m = np.array([c[:n_months] for c in cols], float).T          # (T x N)
    res = {"strategii": len(labels), "mesicu": n_months,
           "pbo": {str(s): ST.pbo_cscv(m, s) for s in blocks if n_months // s >= 4}}
    sr = [ST.sharpe(m[:, j]) for j in range(m.shape[1])]
    res["poradi_sampiona_podle_sr"] = int(1 + sum(1 for v in sr[1:] if v > sr[0]))
    res["pocet_lepsich_nez_sampion"] = int(sum(1 for v in sr[1:] if v > sr[0]))
    res["sr_mesicni_sampion"] = sr[0]
    res["sr_mesicni_nejlepsi_varianta"] = max(sr[1:]) if len(sr) > 1 else None
    res["sr_mesicni_median_variant"] = float(np.median(sr[1:])) if len(sr) > 1 else None
    res["rozptyl_sr_variant"] = float(np.var(sr[1:], ddof=1)) if len(sr) > 2 else None
    return res


def bootstrap_pbo(champion: dict, variants: dict, s=12, n=60, seed=11) -> dict:
    """Sampling variability of PBO: months are resampled with replacement within each block (the same for all strategies)."""
    cols = [champion["rada"]["vynosy"]] + [v["rada"]["vynosy"] for v in variants.values()
                                          if "chyba" not in v and any(v["rada"]["vynosy"])]
    m = np.array(cols, float).T
    size = m.shape[0] // s
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        idx = np.concatenate([b * size + rng.integers(0, size, size) for b in range(s)])
        vals.append(ST.pbo_cscv(m[idx], s)["pbo"])
    return {"p05": float(np.percentile(vals, 5)), "median": float(np.median(vals)), "p95": float(np.percentile(vals, 95)), "n": n}


def effective_trials(champion: dict, variants: dict) -> dict:
    """How many INDEPENDENT trials the registry's trials are worth: Bailey, Lopez de Prado 2014 (A.3): N = rho + (1 - rho) * M
    with M trials of average pairwise correlation rho. The variants are the registry's experiments applied to the champion;
    their Sharpe ratios also give an empirical variance of the trials (instead of the pure-noise 1 / (T - 1))."""
    cols, seen = [], set()
    for name, v in sorted(variants.items()):
        if "chyba" in v or v["klic"] in seen or not any(v["rada"]["vynosy"]):
            continue
        seen.add(v["klic"])
        cols.append(v["rada"]["vynosy"])
    m = np.array(cols, float)
    t = m.shape[1]
    corr = np.corrcoef(m)
    iu = np.triu_indices(len(cols), 1)
    rho = float(np.nanmean(corr[iu]))
    srs = np.array([ST.sharpe(r) for r in m])
    return {"variant": len(cols), "mesicu": t, "prumerna_korelace": rho, "efektivni_pocet_pokusu": rho + (1 - rho) * len(cols),
            "rozptyl_sr_variant": float(np.var(srs, ddof=1)), "sr_variant_p05": float(np.percentile(srs, 5)),
            "sr_variant_median": float(np.median(srs)), "sr_variant_p95": float(np.percentile(srs, 95)),
            "podil_variant_se_zapornym_sr": float(np.mean(srs <= 0))}


def verdicts(data: dict) -> dict:
    """DSR of each champion under the three readings of the number / spread of trials."""
    out = {}
    for profile, champ in data["sampioni"].items():
        x = np.array(champ["rada"]["vynosy"], float)
        t = len(x)
        eff = effective_trials(champ, data["varianty"][profile]) if "varianty" in data else None
        row = {"nominalne_332_sum": ST.dsr_of_series(x, 332)}
        if eff:
            n_eff = max(2, int(round(eff["efektivni_pocet_pokusu"])))
            row["nominalne_332_rozptyl_variant"] = ST.dsr_of_series(x, 332, eff["rozptyl_sr_variant"])
            row["efektivni_sum"] = ST.dsr_of_series(x, n_eff)
            row["efektivni_rozptyl_variant"] = ST.dsr_of_series(x, n_eff, eff["rozptyl_sr_variant"])
            row["efektivni"] = eff
        sd = float(x.std(ddof=1))
        for key, r in list(row.items()):
            if isinstance(r, dict) and "sr0" in r:
                r["po_korekci_rocne"] = (1 + max(r["sr"] - r["sr0"], 0.0) * sd) ** 12 - 1      # rough: excess Sharpe x volatility
        row["potrebne_sr_pro_dsr_095_pri_332"] = _needed_sr(t, x, 332)
        sk, ku = ST.skew_kurt(x)
        sr_defl = max(row["nominalne_332_sum"]["sr"] - row["nominalne_332_sum"]["sr0"], 0.0)
        row["novych_mesicu_pro_95_procent"] = {
            "kdyz_skutecny_sr_je_jako_namereny": _months_needed(row["nominalne_332_sum"]["sr"], sk, ku),
            "kdyz_skutecny_sr_je_0_30": _months_needed(0.30, sk, ku),
            "kdyz_skutecny_sr_je_po_korekci": _months_needed(sr_defl, sk, ku), "sr_po_korekci": sr_defl}
        out[profile] = row
    return out


def _months_needed(sr: float, skew: float, kurt: float, target: float = 0.95) -> int | None:
    """Months of NEW data after which a true monthly Sharpe `sr` (estimated exactly) would make PSR against 0 reach `target`."""
    if sr <= 0:
        return None
    for t in range(2, 2001):
        if ST.psr(sr, 0.0, t, skew, kurt) >= target:
            return t
    return None


def _needed_sr(t: int, x, n: int, target: float = 0.95) -> float:
    """Smallest monthly Sharpe ratio (skewness / kurtosis of the champion's series kept) that would give DSR >= target."""
    sk, ku = ST.skew_kurt(x)
    sr0 = ST.expected_max_sr(n, 1.0 / (t - 1))
    lo, hi = sr0, sr0 + 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if ST.psr(mid, sr0, t, sk, ku) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def render_tables(data: dict) -> str:
    L = ["# Fáze 2: tabulky DSR a PBO (generováno `scripts/faze2_analyza.py zprava`)", "",
         f"_Registr: {data['registr']['pokusu']} pokusů, poslední otisk `{str(data['registr']['posledni_hash'])[:16]}`; trezor od "
         f"{data['trezor']['od']} zavřený, data do {data['trezor']['posledni_mesic']}. Pozorování = měsíc (93 měsíců: "
         "2019-01 až 2022-12 a 2023-01 až 2026-09). DSR = pravděpodobnost, že skutečný Sharpe je větší než nejlepší ze N "
         "pokusů, který by vyšel čistým šumem._", ""]
    for profile, c in data["sampioni"].items():
        d = c["popis"]
        L += [f"## {profile}: {c['nazev']}", "", f"Sharpe měsíční {d['sr_mesicni']:.3f} (roční {d['sr_rocni']:.2f}), šikmost {d['sikmost']:.2f}, "
              f"špičatost {d['spicatost']:.2f}, průměr měsíčně {d['prumer_mesicni']:+.2%}, směrodatná odchylka {d['sm_odchylka_mesicni']:.2%}, "
              f"nejhorší měsíc {d['nejhorsi_mesic']:+.1%}; Sharpe 5–95% (bootstrap) {d['sr_bootstrap_mesicni']['p05']:.2f}–"
              f"{d['sr_bootstrap_mesicni']['p95']:.2f}.", "",
              "| počet pokusů N | práh SR0 (měsíčně) | DSR |", "|---|---|---|"]
        for n, r in d["dsr_podle_poctu_pokusu"].items():
            L.append(f"| {n} | {r['sr0']:.3f} | {r['dsr']:.3f} |")
        L.append("")
        v = data.get("posudek", {}).get(profile)
        if v and "efektivni" in v:
            e = v["efektivni"]
            L += [f"Odhad efektivního počtu nezávislých pokusů (Bailey, López de Prado 2014): {e['variant']} použitelných variant, průměrná korelace "
                  f"jejich měsíčních řad {e['prumerna_korelace']:.2f} → **{e['efektivni_pocet_pokusu']:.0f}** nezávislých pokusů; rozptyl Sharpe variant "
                  f"{e['rozptyl_sr_variant']:.4f} (čistý šum by dal {1 / (e['mesicu'] - 1):.4f}); Sharpe variant 5/50/95 %: "
                  f"{e['sr_variant_p05']:.2f} / {e['sr_variant_median']:.2f} / {e['sr_variant_p95']:.2f}.", "",
                  "| čtení | N | rozptyl | SR0 | DSR | zbývá ročně (hrubě) |", "|---|---|---|---|---|---|"]
            for key, label, n in (("nominalne_332_sum", "nominálně 332, rozptyl čistého šumu (pravidlo zadání)", 332),
                                  ("nominalne_332_rozptyl_variant", "nominálně 332, rozptyl variant", 332),
                                  ("efektivni_sum", "efektivní N, rozptyl čistého šumu", round(e["efektivni_pocet_pokusu"])),
                                  ("efektivni_rozptyl_variant", "efektivní N, rozptyl variant", round(e["efektivni_pocet_pokusu"]))):
                r = v[key]
                var = "1/(T-1)" if "sum" in key else f"{e['rozptyl_sr_variant']:.4f}"
                L.append(f"| {label} | {n} | {var} | {r['sr0']:.3f} | **{r['dsr']:.3f}** | {r['po_korekci_rocne']:+.1%} |")
            m = v["novych_mesicu_pro_95_procent"]
            L += ["", "Kolik NOVÝCH měsíců dat (mimo trezor, jeden předem daný test) by stačilo na 95% jistotu, že skutečný Sharpe je kladný: "
                  f"{m['kdyz_skutecny_sr_je_jako_namereny']} měsíců, kdyby byl skutečný Sharpe jako naměřený ({d['sr_mesicni']:.2f}); "
                  f"{m['kdyz_skutecny_sr_je_0_30']} měsíců, kdyby byl 0,30; {m['kdyz_skutecny_sr_je_po_korekci']} měsíců, kdyby byl jen "
                  f"takový, jaký zbývá po korekci ({m['sr_po_korekci']:.2f}).", ""]
            L += ["", f"Aby DSR při N = 332 dosáhl 0,95, musel by měsíční Sharpe být aspoň {v['potrebne_sr_pro_dsr_095_pri_332']:.3f} "
                  f"(roční {v['potrebne_sr_pro_dsr_095_pri_332'] * 12 ** 0.5:.2f}); sampion má {d['sr_mesicni']:.3f}.", ""]
    for profile, vs in data.get("varianty", {}).items():
        ok = {n: v for n, v in vs.items() if "chyba" not in v and "dsr_podle_poctu_pokusu" in v.get("popis", {})}
        rows = sorted(ok.items(), key=lambda kv: -kv[1]["popis"]["sr_mesicni"])
        bad = [n for n, v in vs.items() if "chyba" in v]
        passing = [n for n, v in ok.items() if v["popis"]["dsr_podle_poctu_pokusu"]["332"]["dsr"] >= 0.95]
        L += [f"## Výsledky jednotlivých pokusů aplikovaných na šampiona — {profile}", "",
              f"{len(vs)} pokusů z registru (`EXPERIMENTS`), každý jako změna dnešního šampiona; {len(bad)} nelze použít, "
              f"{len(passing)} má DSR(N = 332) ≥ 0,95. Top 12 podle měsíčního Sharpe (DSR podle zadání, N = 332):", "",
              "| pokus | Sharpe měsíčně | DSR (N = 332) | ročně 2023–26 |", "|---|---|---|---|"]
        for name, v in rows[:12]:
            w1 = v["rada"]["okna"].get("1") or {}
            L.append(f"| {name} | {v['popis']['sr_mesicni']:.3f} | {v['popis']['dsr_podle_poctu_pokusu']['332']['dsr']:.3f} | "
                     f"{w1.get('rocne', float('nan')):+.1%} |")
        L.append("")
    for profile, r in data.get("pbo", {}).items():
        L += [f"## PBO (CSCV) — {profile}", "", f"Strategií: {r['strategii']} (sampion + varianty registru použité na sampiona), {r['mesicu']} měsíců. "
              f"Variant lepších než sampion (podle Sharpe): {r['pocet_lepsich_nez_sampion']}; Sharpe sampiona {r['sr_mesicni_sampion']:.3f}, "
              f"medián variant {r['sr_mesicni_median_variant']:.3f}, nejlepší varianta {r['sr_mesicni_nejlepsi_varianta']:.3f}.", "",
              "| bloků S | kombinací | PBO |", "|---|---|---|"]
        for s_, p_ in r["pbo"].items():
            L.append(f"| {s_} | {p_['n_comb']} | **{p_['pbo']:.2f}** |")
        b = r.get("bootstrap_pbo_s12")
        if b:
            L += ["", f"Kolísání odhadu PBO (S = 12, {b['n']} přeskupení měsíců uvnitř bloků): 5 % {b['p05']:.2f}, medián {b['median']:.2f}, 95 % {b['p95']:.2f}.", ""]
    return "\n".join(L) + "\n"


def save(data: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old.update(data)
    old["vytvoreno"] = date.today().isoformat()
    old["registr"] = {"pokusu": RP.n_trials(), "posledni_hash": LG.verify(RP.REG).get("posledni_hash")}
    old["trezor"] = {"od": TZ.load()["od"], "otevreno": TZ.load()["otevreno"], "posledni_mesic": f"{LAST_MONTH[0]}-{LAST_MONTH[1]:02d}"}
    OUT.write_text(json.dumps(old, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "sampioni"
    if cmd == "sampioni":
        save({"sampioni": run_champions()})
    elif cmd == "varianty":
        cores = int(argv[argv.index("--jader") + 1]) if "--jader" in argv else 4
        res = run_variants(cores)
        data = json.loads(OUT.read_text()) if OUT.exists() else {}
        champs = data.get("sampioni") or run_champions()
        pbo = {p: pbo_for(champs[p], res[p]) for p in res}
        for p in pbo:
            pbo[p]["bootstrap_pbo_s12"] = bootstrap_pbo(champs[p], res[p])
        save({"sampioni": champs, "varianty": res, "pbo": pbo})
        for p, r in pbo.items():
            print(p, {s: round(v["pbo"], 3) for s, v in r["pbo"].items()}, "strategii", r["strategii"])
    elif cmd == "zprava":
        data = json.loads(OUT.read_text())
        data["posudek"] = verdicts(data)
        save({"posudek": data["posudek"]})
        TABLES.write_text(render_tables(data), encoding="utf-8")
        print(f"zapsano {TABLES.relative_to(PROJECT_ROOT)}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
