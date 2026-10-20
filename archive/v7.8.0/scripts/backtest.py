"""Backtest of the full model on the stored BID/ASK history.

    python scripts/backtest.py                          # 12 pairs, all stored history
    python scripts/backtest.py --from 2025-01-01 --to 2026-09-01
    python scripts/backtest.py --symbols EUR/USD,USD/JPY
    python scripts/backtest.py --ablation               # which layer adds what
    python scripts/backtest.py --robustness             # parameter perturbations
    python scripts/backtest.py --walkforward            # choose on the past, test on the future
    python scripts/backtest.py --save                   # store the trades (data/backtests/)

The same code as the live run decides at every H4 close, on closed bars
and on fundamental values that were public at that moment. Outcomes are
side-correct (BUY at ASK, exits at BID) with costs. The economic calendar
has no history, so the event layer is OFF in backtests (stated in the
output). Numbers from a backtest are NOT a promise for the future.
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_DIR  # noqa: E402  (loads .env first)
from src.engine.backtest import BacktestConfig, run  # noqa: E402
from src.engine.data import load_pair  # noqa: E402
from src.engine.params import DEFAULT_PARAMS  # noqa: E402
from src.instruments import parse_symbols  # noqa: E402
from src.stats import validation  # noqa: E402
from src.stats.errors import taxonomy_table  # noqa: E402
from src.stats.performance import calibration, summarize  # noqa: E402
from src.stats.registry import ensure_baseline  # noqa: E402

UTC = timezone.utc
LINE = "=" * 78


def _ts(text: str) -> int:
    return int(datetime.combine(date.fromisoformat(text), datetime.min.time(), tzinfo=UTC).timestamp())


def print_summary(label: str, summary) -> None:
    print(summary.line())

    if summary.win_ci:
        print(f"    win 95% IS {summary.win_ci[0] * 100:.0f}-{summary.win_ci[1] * 100:.0f}%", end="")
    if summary.expectancy_ci:
        print(f" | E 95% IS {summary.expectancy_ci[0]:+.3f} .. {summary.expectancy_ci[1]:+.3f}R", end="")
    print(f" | nezavislych situaci {summary.effective_n} | bez vstupu {summary.not_activated}"
          f" | poradi neznamo {summary.sequence_unknown} | diry {summary.unresolved}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Full-model backtest")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--from", dest="first", default=None)
    parser.add_argument("--to", dest="last", default=None)
    parser.add_argument("--cadence", default="4h", choices=("4h", "1h"))
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--robustness", action="store_true")
    parser.add_argument("--walkforward", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="KLIC=HODNOTA",
                        help="challenger parameter, e.g. --set atr_timeframe=4h --set horizon_hours=72")
    args = parser.parse_args(argv)

    symbols = parse_symbols(args.symbols)
    p = DEFAULT_PARAMS

    if args.set:
        changes = {}
        for item in args.set:
            key, _, value = item.partition("=")
            current = getattr(DEFAULT_PARAMS, key)          # AttributeError = unknown parameter
            changes[key] = type(current)(value) if not isinstance(current, bool) else value.lower() in ("1", "true", "ano")
        p = DEFAULT_PARAMS.with_changes(**changes)
        print(f"CHALLENGER parametry: {changes} -> {p.fingerprint} (vychozi {DEFAULT_PARAMS.fingerprint})")
    started = time.monotonic()
    print(LINE)
    print("FXBOT - BACKTEST CELEHO MODELU (V7.8.0 implementace)")
    print(LINE)
    preloaded = {}

    for symbol in symbols:
        series = load_pair(symbol, p)
        preloaded[symbol] = series

        if len(series.h1):
            print(f"  {symbol}: H1 {len(series.h1)} svicek {series.h1.time(0):%Y-%m-%d} .. "
                  f"{series.h1.time(len(series.h1) - 1):%Y-%m-%d}")
        else:
            print(f"  {symbol}: zadna historie (python scripts/download_history.py)")

    available = [s for s in symbols if len(preloaded[s].h1) >= 500]

    if not available:
        print("Nedostatek historie pro backtest.")
        return 1

    first_ts = min(preloaded[s].h1.ts[0] for s in available)
    last_ts = max(preloaded[s].h1.ts[-1] for s in available)
    start = _ts(args.first) if args.first else first_ts + 250 * 86400     # warm-up for D1 indicators
    end = _ts(args.last) if args.last else last_ts
    print(f"obdobi rozhodovani: {datetime.fromtimestamp(start, tz=UTC):%Y-%m-%d} .. "
          f"{datetime.fromtimestamp(end, tz=UTC):%Y-%m-%d} | kazdou {args.cadence} | parametry {p.fingerprint}")
    print("udalostni vrstva: VYPNUTA (kalendar nema historii) | naklady: spread z dat + "
          f"{p.broker_markup_pips} pip prirazka + {p.slippage_pips} pip skluz na stranu")
    config = BacktestConfig(available, start, end, p, cadence=args.cadence)
    result = run(config, preloaded, progress=lambda text: print("  " + text))
    print(f"rozhodnuti {result.decisions} | predikci {len(result.trades)} | zablokovane otoceni "
          f"{result.blocked_flips} | teze trva {result.kept} | cas {time.monotonic() - started:.0f} s")
    print(LINE)
    bench = validation.benchmark(result)
    print("VYSLEDEK vs KONTROLA (stejna rozhodnuti a geometrie; modul 74)")
    print_summary("model", bench["model"])
    print_summary("anti", bench["anti"])
    paired = bench["paired"]

    if paired.get("n", 0) >= 2:
        print(f"  na rozhodnuti: model {paired['model_r_per_decision']:+.3f}R | nahodny smer (ocekavani) "
              f"{paired['random_r_per_decision']:+.3f}R | n={paired['n']}")
        print(f"  EDGE SMERU vs nahoda (parovy test) {paired['edge']:+.3f}R (95% IS {paired['low']:+.3f} .. "
              f"{paired['high']:+.3f}) -> {paired['verdict']}")

    for label, b in (("model", bench["bounds_model"]), ("anti", bench["bounds_anti"])):
        if b.get("unknown"):
            print(f"  {label}: poradi neznamo u {b['unknown']} obchodu ({b['share'] * 100:.0f} %) -> E na obchod "
                  f"{b['trade_worst']:+.3f} (vse SL) .. {b['trade_best']:+.3f} (vse TP1)")

    print(LINE)
    print("KVALITA SMERU BEZ GEOMETRIE OBCHODU (pohyb mid ve smeru, ATR H1; nahoda = 0; modul 66)")

    for hours, row in validation.signal_study(result.trades).items():
        print(f"  {hours:>3} h: {row['mean_atr']:+.2f} ATR (IS {row['ci'][0]:+.2f}..{row['ci'][1]:+.2f},"
              f" prekryvy -> optimisticky), zasah {row['hit_rate'] * 100:.0f}% (n={row['n']})")

    print(LINE)
    print("ROZPAD (modul 73)")

    for name, rows in validation.regime_performance(result.trades).items():
        print(f"-- {name}")
        for summary in rows:
            print("   " + summary.line())

    cal = calibration(result.trades)
    print(f"KALIBRACE DUVERY (modul 72): {cal['verdict']}")
    print("TAXONOMIE CHYB (modul 69):")

    for key, count in list(taxonomy_table(result.trades).items())[:8]:
        print(f"   {count:>5}x {key}")

    print("DUVODY NEOBCHODOVAT (nejcastejsi):")

    for reason, count in sorted(result.no_trade_reasons.items(), key=lambda kv: -kv[1])[:8]:
        print(f"   {count:>6}x {reason}")

    print(f"SELHANE NOW BRANY: {result.gate_failures}")
    ensure_baseline(DEFAULT_PARAMS)

    if p is not DEFAULT_PARAMS:
        from src.stats.registry import register

        register(p, "challenger " + " ".join(args.set), "CHALLENGER",
                 "backtest; povyseni jen pres walk-forward OOS a promotion gate",
                 {"expectancy": bench["model"].expectancy, "paired_edge": bench["paired"].get("edge")})

    if args.ablation:
        print(LINE)
        print("ABLACE (modul 75)")
        for item in validation.ablation(config, preloaded, progress=lambda text: print("   " + text)):
            pe = item["paired"]
            if pe.get("n", 0) >= 2:
                print(f"      edge smeru {pe['edge']:+.3f}R (IS {pe['low']:+.3f}..{pe['high']:+.3f}) {pe['verdict']}")

    if args.robustness:
        print(LINE)
        print("ROBUSTNOST (modul 76)")
        validation.robustness(config, preloaded, bench["model"], progress=lambda text: print("   " + text))

    if args.walkforward:
        print(LINE)
        print("WALK-FORWARD OOS (modul 77)")
        wf = validation.walk_forward(available, start, end, p, list(validation.DEFAULT_GRID), preloaded,
                                     progress=lambda text: print("   " + text))
        print_summary("oos", wf["oos_chosen"])
        print_summary("oos", wf["oos_default"])
        d = wf["difference"]
        if d.get("difference") is not None:
            print(f"   rozdil {d['difference']:+.3f}R (95% IS {d['low']:+.3f} .. {d['high']:+.3f})"
                  f" -> {'vyznamny' if d['significant'] else 'nevyznamny: vychozi parametry zustavaji'}")

    if args.save:
        out = DATA_DIR / "backtests"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"backtest_{datetime.now(UTC):%Y%m%dT%H%M%SZ}_{p.fingerprint}.json"
        path.write_text(json.dumps({"params": p.to_dict(), "trades": result.trades, "placebo": result.placebo},
                                   default=str), encoding="utf-8")
        print(f"ulozeno: {path}")

    print(LINE)
    print("Backtest je historicky pokus, ne slib. n<20 jen popisne; OOS rozhoduje o zmene parametru.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
