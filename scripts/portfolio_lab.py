"""Portfolio of rules for the highest annual account return: many robust
systems combined (different signals, days and exits), chosen only on the
past and checked walk-forward.

    python scripts/portfolio_lab.py        # -> data/research/profit2/portfolio_greedy.md

REJECTED METHOD (docs/ROCNI_VYNOS_VYSLEDEK.md): weights fitted on the past
overfit badly (near-zero drawdown in the selection period, > 100 % later).
Kept for the record and for candidates(), used by scripts/portfolio_sim.py.

1. Candidates: every system of profit_lab2 (213 840) whose monthly result is
   positive with a monthly t >= T_MIN in each selection sub-period.
2. Greedy portfolio: components scaled to the same monthly risk, added one by
   one while the Sharpe ratio of the combined monthly result in the
   selection period grows (at most K_MAX components, correlation is what
   makes a component useful).
3. Walk-forward: select on 2012-2018 -> show 2019-2022 and 2023-2026; select
   on 2012-2022 -> show 2023-2026 (the period never used).
Account: total margin of all components scaled so the largest drawdown in
the selection period = DD_TARGET (simple sums by month, no compounding).
"""

import pickle
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import annual_lab as AL  # noqa: E402
import profit_lab2 as P  # noqa: E402

T_MIN = 2.0
K_MAX = 10
DD_TARGET = 0.20
POOL = 3000
YEAR_SPANS = {"2012-18": (0, 84), "2019-22": (84, 132), "2023-26": (132, AL.MONTHS)}


def tstat(x: np.ndarray, axis=-1) -> np.ndarray:
    m, s = x.mean(axis=axis), x.std(axis=axis)
    return np.where(s > 0, m / s * np.sqrt(x.shape[axis]), 0.0)


def candidates(sub_spans: list[tuple[int, int]]) -> list[dict]:
    """Systems with a positive monthly result and t >= T_MIN in every sub-span."""
    info = pickle.loads((P.OUT / "meta.pkl").read_bytes())
    out = []
    for en, _ in P.ENTRIES:
        B = P.load_block(en)
        S, N, W = AL.monthly(B)
        t_min = np.full(S.shape[0:1] + S.shape[2:], np.inf, dtype=np.float32)
        for a, b in sub_spans:
            t_min = np.minimum(t_min, tstat(S[:, a:b, :].transpose(0, 2, 1)))
        order = np.argsort(-t_min, axis=None)[:POOL]
        for flat in order:
            m, x = np.unravel_index(flat, t_min.shape)
            if t_min[m, x] < T_MIN:
                break
            out.append({"entry": en, "m": int(m), "x": int(x), "t": float(t_min[m, x]),
                        "name": P.describe(info["meta"], int(m), int(x), en),
                        "S": S[m, :, x].astype(np.float64), "N": N[m, :, x].astype(np.float64),
                        "W": W[m, :, x].astype(np.float64)})
        del S, N, W
    return sorted(out, key=lambda c: -c["t"])[:POOL]


def greedy(cands: list[dict], span: tuple[int, int]) -> list[tuple[dict, float]]:
    """Components and their weights (margin multiplier, unit monthly risk)."""
    a, b = span
    X = np.array([c["S"][a:b] for c in cands])
    sd = X.std(axis=1)
    keep = sd > 0
    weights = np.where(keep, 1 / np.where(keep, sd, 1), 0)
    Z = X * weights[:, None]
    chosen, total = [], np.zeros(b - a)
    best = -np.inf
    for _ in range(K_MAX):
        trial = total[None, :] + Z
        sharpe = trial.mean(axis=1) / np.maximum(trial.std(axis=1), 1e-12)
        sharpe[[i for i, _ in chosen]] = -np.inf
        k = int(np.argmax(sharpe))
        if sharpe[k] <= best + 0.005:
            break
        best = sharpe[k]
        chosen.append((k, weights[k]))
        total = total + Z[k]
    return [(cands[k], w) for k, w in chosen]


def combine(parts: list[tuple[dict, float]], span: tuple[int, int]) -> dict:
    """Monthly series of the portfolio, scaled to DD_TARGET on `span`."""
    S = sum(w * c["S"] for c, w in parts)
    N = sum(c["N"] for c, _ in parts)
    W = sum(c["W"] for c, _ in parts)
    a, b = span
    dd = AL.drawdown(S[a:b][None, :])[0] / 100
    scale = DD_TARGET / dd if dd > 0 else 0.0
    return {"S": S * scale / 100, "N": N, "W": W, "scale": scale}


def report_line(label: str, pf: dict, x: int, y: int) -> str:
    s, n, w = pf["S"][x:y], pf["N"][x:y], pf["W"][x:y]
    years = (y - x) / 12
    dd = AL.drawdown(s[None, :])[0]
    win_m = w.sum() / (y - x)
    return (f"| {label} | {n.sum() / years:.0f} | {w.sum() / max(n.sum(), 1):.0%} | {win_m:.1f} | {(w >= 2).mean():.0%} | "
            f"{(s > 0).mean():.0%} | **{s.sum() / years:+.0%}** | {dd:.0%} |")


def portfolio_table(pf: dict) -> list[str]:
    lines = ["| obdobi | obchodu/rok | uspesnost | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | "
             "**rocne** | max. propad |", "|---|---|---|---|---|---|---|---|"]
    for label, (x, y) in YEAR_SPANS.items():
        lines.append(report_line(label, pf, x, y))
    return lines


def main() -> int:
    started = time.monotonic()
    out = ["# Portfolio pravidel - nejvyssi rocni zhodnoceni", "",
           f"_Kandidati: systemy s kladnym mesicnim vysledkem a t >= {T_MIN} v kazdem vyberovem obdobi; portfolio "
           f"skladane hladove (max {K_MAX} slozek, kazda se stejnym mesicnim rizikem); celkova velikost tak, aby "
           f"nejvetsi propad ve vyberovem obdobi byl {DD_TARGET:.0%} uctu. Rocne = prosty soucet mesicu._", ""]
    results = {}
    for label, sel, subs in (("Vyber na 2012-2018", (0, 84), [(0, 42), (42, 84)]),
                             ("Vyber na 2012-2022", (0, 132), [(0, 84), (84, 132)])):
        cands = candidates(subs)
        parts = greedy(cands, sel)
        pf = combine(parts, sel)
        results[label] = (parts, pf)
        out += [f"## {label} ({len(cands)} kandidatu)", ""]
        out += portfolio_table(pf) + [""]
        out += ["| slozka | vaha (podil marze) |", "|---|---|"]
        for c, w in parts:
            out.append(f"| {c['name']} | {w * pf['scale']:.2%} uctu na obchod |")
        out += [""]
        print(f"{label}: {len(cands)} kandidatu, {len(parts)} slozek, {time.monotonic() - started:.0f} s", flush=True)
    pickle.dump({k: ([(c["entry"], c["m"], c["x"], c["name"], w) for c, w in parts], pf)
                 for k, (parts, pf) in results.items()}, open(P.OUT / "portfolio.pkl", "wb"))
    out += [f"_vypocet {time.monotonic() - started:.0f} s_"]
    (P.OUT / "portfolio_greedy.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
