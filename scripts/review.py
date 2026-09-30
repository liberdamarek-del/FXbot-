"""Review of locked predictions (module 82: review cadence).

    python scripts/review.py              # daily: last 24 h
    python scripts/review.py --weekly     # last 7 days: repeated mechanisms, regimes
    python scripts/review.py --monthly    # last 30 days: release-level view, decay
    python scripts/review.py --all        # whole forward test (everything locked so far)

Reads only the immutable ledger. A single event never changes a production
rule: the review lists change CANDIDATES (1 case = observation, 2 =
candidate, 3+ = active candidate) that must go through the change log and
the out-of-sample gate (src/stats/registry.py).
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import initialize_database  # noqa: E402  (loads .env first)
from src.prediction_ledger import initialize_ledger  # noqa: E402
from src.stats.errors import taxonomy_table  # noqa: E402
from src.stats.performance import breakdown, calibration, rolling, summarize  # noqa: E402
from src.stats.validation import paired_edge, unknown_bounds  # noqa: E402
from src.v78.run import change_candidates, ledger_controls, ledger_trades  # noqa: E402

UTC = timezone.utc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Review of locked predictions")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--monthly", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    initialize_database()
    initialize_ledger()
    days = 100000 if args.all else 30 if args.monthly else 7 if args.weekly else 1
    now = datetime.now(UTC)
    since = 0.0 if args.all else (now - timedelta(days=days)).timestamp()
    everything = ledger_trades()
    trades = [t for t in everything if t["t0"] >= since]
    label = {1: "DENNI", 7: "TYDENNI", 30: "MESICNI"}.get(days, "CELKOVA")

    print("=" * 78)
    period = "cely dopredny test" if args.all else f"poslednich {days} d"
    print(f"FXBOT - {label} REVIZE ({now:%Y-%m-%d %H:%M} UTC, {period})")
    print("=" * 78)
    print(summarize(trades, "obdobi").line())
    print(summarize(everything, "cela historie").line())
    print_control(trades, ledger_controls(since, now))

    if days >= 7:
        for name, key in (("par", "symbol"), ("rozhodnuti", "decision"), ("duvera", "confidence"),
                          ("setup", "setup_type"), ("model", "model_version")):
            print(f"-- podle: {name}")
            for summary in breakdown(trades, lambda t, k=key: t.get(k)):
                print("   " + summary.line())

    if days >= 30:
        print(f"KALIBRACE: {calibration(everything)['verdict']}")
        for window in (10, 20, 50):
            values = rolling(everything, window)
            if values:
                print(f"klouzava expectancy {window}: posledni {values[-1]:+.2f}R, minimum {min(values):+.2f}R")

    print("TAXONOMIE CHYB:")
    for key, count in taxonomy_table(trades).items():
        print(f"   {count}x {key}")

    print("KANDIDATI ZMEN (nic se nemeni automaticky):")
    for line in change_candidates(everything) or ["   zadni"]:
        print(f"   {line}")

    print("=" * 78)
    return 0


def print_control(trades: list[dict], controls: list[dict]) -> None:
    """Paired direction test of the forward period (module 74): every locked
    prediction against its mirrored plan on the same path."""
    edge = paired_edge(trades, controls)

    if edge.get("n", 0) < 2:
        print("KONTROLA SMERU: malo vyhodnocenych predikci pro parovy test")
    else:
        print(f"KONTROLA SMERU (anti-model na stejne ceste, n={edge['n']}): model {edge['model_r_per_decision']:+.3f} R,"
              f" nahodny smer {edge['random_r_per_decision']:+.3f} R na rozhodnuti -> edge {edge['edge']:+.3f} R"
              f" (95% IS {edge['low']:+.3f} .. {edge['high']:+.3f}) {edge['verdict']}")

    bounds = unknown_bounds(trades)

    if bounds.get("unknown"):
        print(f"PORADI NEZNAMO: {bounds['unknown']} obchodu - meze E {bounds['trade_worst']:+.3f} .. "
              f"{bounds['trade_best']:+.3f} R na obchod (nehada se)")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
