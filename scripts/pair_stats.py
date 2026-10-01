"""Historical success of the champion rule per pair and tier, for ranking the
pairs on the dashboard ("which pair do you recommend most").

    python scripts/pair_stats.py      # -> learning/pair_stats.json (run again when the champion changes)

For every tier of learning/champion_12_mesicne.json and every one of the 12
pairs: trades 2012-2026 of that tier's rule (hourly path, costs, swap),
winners, average result in % of the margin. Small samples are shrunk toward
the tier's average over all 12 pairs (PRIOR_N pseudo-trades), so a pair with
3 lucky trades does not jump to the top:
    estimate = (winners + PRIOR_N x tier rate) / (trades + PRIOR_N)
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_deep as D  # noqa: E402
from src.instruments import DEFAULT_ACTIVE  # noqa: E402

LEARNING = PROJECT_ROOT / "learning"
PRIOR_N = 20


def main() -> int:
    state = json.loads((LEARNING / "champion_12_mesicne.json").read_text())
    cfg = state["config"]
    pairs = [p for p in DEFAULT_ACTIVE]
    out = {"pravidlo": cfg["name"], "prior_n": PRIOR_N, "stupne": []}
    for k, tier in enumerate(cfg["tiers"]):
        rule = replace(D.Rule("t"), **{**cfg["base"], **tier})
        trades = D.simulate(rule, pairs)
        x_all = np.array([t["margin_pct"] for t in trades])
        rate = float((x_all > 0).mean()) if len(x_all) else 0.0
        mean = float(x_all.mean()) if len(x_all) else 0.0
        per = {}
        for p in pairs:
            x = np.array([t["margin_pct"] for t in trades if t["pair"] == p])
            n, w = len(x), int((x > 0).sum())
            per[p] = {"n": n, "ziskovych": w,
                      "uspesnost": round(w / n * 100, 1) if n else None,
                      "prumer_proc_marze": round(float(x.mean()), 1) if n else None,
                      "odhad_uspesnosti": round((w + PRIOR_N * rate) / (n + PRIOR_N) * 100, 1),
                      "odhad_prumer": round((float(x.sum()) + PRIOR_N * mean) / (n + PRIOR_N), 1)}
        out["stupne"].append({"index": k, "obchodu": len(x_all), "uspesnost": round(rate * 100, 1),
                              "prumer_proc_marze": round(mean, 1), "pary": per})
        print(f"stupen {k}: {len(x_all)} obchodu, uspesnost {rate:.0%}, prumer {mean:+.1f} % marze")
    (LEARNING / "pair_stats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
