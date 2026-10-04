"""Historical success of the champion rule per pair and tier: ranking of the
pairs on the dashboard and the probabilities of the three profit targets.

    python scripts/pair_stats.py      # -> learning/pair_stats.json (run again when the champion changes)

For every tier of learning/champion_12_mesicne.json and every one of the 12
pairs, on the hourly path 2012-2026 with costs and swap:
- TP1 = the model's own target (tp ATR), TP2 / TP3 = 1.0 / 1.5 ATR further
  targets with the same stop and time limit;
- probability that each target is reached before the stop (and within the
  holding time), from the best move of each trade run without a target - on the
  same entries as the rule's own trades; it is a historical frequency on the years
  the rule was chosen on (in-sample), not a calibrated forecast: the forward test
  (learning/forward_trades.json) is the check;
- average result of the whole position closed at that target (or stop / time);
only trades whose TP1 is >= 10 % of the margin count (as in live trading).
Small samples are shrunk toward the tier's average over the 12 pairs
(PRIOR_N pseudo-trades): estimate = (hits + PRIOR_N x tier rate) / (n + PRIOR_N).
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
EXTRA_TPS = (1.0, 1.5)                 # TP2, TP3 in ATR (TP1 = the champion's own target)


def shrink(hits: float, n: int, prior: float) -> float:
    return (hits + PRIOR_N * prior) / (n + PRIOR_N)


def main() -> int:
    state = json.loads((LEARNING / "champion_12_mesicne.json").read_text())
    cfg = state["config"]
    pairs = list(DEFAULT_ACTIVE)
    tps = (cfg["base"]["tp"],) + EXTRA_TPS
    out = {"pravidlo": cfg["name"], "prior_n": PRIOR_N, "tp_atr": list(tps), "sl_atr": cfg["base"]["sl"], "stupne": []}
    for k, tier in enumerate(cfg["tiers"]):
        base_rule = replace(D.Rule("t"), **{**cfg["base"], **tier})
        tp1, sl = base_rule.tp, base_rule.sl
        # the rule's own trades (one position per pair, TP1, live validity: TP1 >= 10 % of the margin); the other
        # targets and the best move without a target are measured on exactly these entries (audit 2026-10-04:
        # separate runs had different entries because a longer trade blocks the pair longer)
        rule_trades = [t for t in D.simulate(replace(base_rule, min_tp_pct=0.0), pairs)
                       if t["sl_pct"] * tp1 / sl >= 10.0 - 1e-9]
        keys = {(t["pair"], t["day"], t["side"]) for t in rule_trades}

        def same_entries(rule):
            return [t for t in D.simulate(replace(rule, min_tp_pct=0.0, one_per_pair=False), pairs)
                    if (t["pair"], t["day"], t["side"]) in keys]
        free = same_entries(replace(base_rule, tp=1e6))                 # best move before stop / time
        runs = {L: (rule_trades if L == tp1 else same_entries(replace(base_rule, tp=L))) for L in tps}
        tier_out = {"index": k, "obchodu": len(runs[tp1]), "pary": {}, "tp": []}
        prior_hit = {L: float(np.mean([t["mfe_atr"] >= L for t in free])) if free else 0.0 for L in tps}
        prior_ev = {L: float(np.mean([t["margin_pct"] for t in runs[L]])) if runs[L] else 0.0 for L in tps}
        prior_win = float(np.mean([t["margin_pct"] > 0 for t in runs[tp1]])) if runs[tp1] else 0.0
        tier_out["tp"] = [{"atr": L, "pravdepodobnost": round(prior_hit[L] * 100, 1), "prumer_proc_marze": round(prior_ev[L], 1)}
                          for L in tps]
        tier_out["uspesnost"] = round(prior_win * 100, 1)
        for p in pairs:
            f = [t for t in free if t["pair"] == p]
            base_trades = [t for t in runs[tp1] if t["pair"] == p]
            n, w = len(base_trades), sum(1 for t in base_trades if t["margin_pct"] > 0)
            x = np.array([t["margin_pct"] for t in base_trades])
            levels = []
            for L in tps:
                hits = sum(1 for t in f if t["mfe_atr"] >= L)
                ev = [t["margin_pct"] for t in runs[L] if t["pair"] == p]
                levels.append({"atr": L, "n": len(f), "dosazeno": hits,
                               "pravdepodobnost": round(shrink(hits, len(f), prior_hit[L]) * 100, 1),
                               "prumer_proc_marze": round((sum(ev) + PRIOR_N * prior_ev[L]) / (len(ev) + PRIOR_N), 1)})
            tier_out["pary"][p] = {
                "n": n, "ziskovych": w, "uspesnost": round(w / n * 100, 1) if n else None,
                "prumer_proc_marze": round(float(x.mean()), 1) if n else None,
                "odhad_uspesnosti": round(shrink(w, n, prior_win) * 100, 1),
                "odhad_prumer": round((float(x.sum()) + PRIOR_N * prior_ev[tp1]) / (n + PRIOR_N), 1),
                "tp": levels,
                "prumer_rozdeleni_3": round(float(np.mean([lv["prumer_proc_marze"] for lv in levels])), 1)}
        out["stupne"].append(tier_out)
        print(f"stupen {k}: {tier_out['obchodu']} obchodu, uspesnost {prior_win:.0%}; "
              + ", ".join(f"TP {L} ATR: {prior_hit[L]:.0%} / {prior_ev[L]:+.1f} %" for L in tps))
    (LEARNING / "pair_stats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
