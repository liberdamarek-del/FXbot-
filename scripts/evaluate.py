"""Full evaluation of the model on the archived history -> Markdown report.

    python scripts/evaluate.py                       # all stored history, report to docs/BACKTEST_REPORT.md
    python scripts/evaluate.py --quick               # without robustness / walk-forward
    python scripts/evaluate.py --out data/eval.md

Runs, on exactly the same decisions, costs and coverage rules:
  1. champion backtest + paired anti-model control (module 74)
  2. direction-only signal study (module 66)
  3. breakdown by regime, pair, setup, evidence class; calibration (72, 73)
  4. error taxonomy (69)
  5. ablation of layers (75)
  6. robustness / sensitivity (76)
  7. walk-forward out-of-sample (77) and the promotion gate (78, 144)

The report states the sample class of every number (module 70). It is a
historical experiment on public ECN prices with modelled costs - not a
promise and not broker-verified.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.backtest import BacktestConfig, run  # noqa: E402  (loads .env first)
from src.engine.data import CANONICAL_SOURCE, load_pair  # noqa: E402
from src.engine.params import DEFAULT_PARAMS  # noqa: E402
from src.instruments import parse_symbols  # noqa: E402
from src.stats import validation  # noqa: E402
from src.stats.errors import taxonomy_table  # noqa: E402
from src.stats.performance import calibration, summarize  # noqa: E402
from src.stats.registry import promotion_gate  # noqa: E402

UTC = timezone.utc


def row(summary) -> str:
    def f(value, fmt):
        return "-" if value is None else format(value, fmt)

    ci = f"{summary.expectancy_ci[0]:+.3f} .. {summary.expectancy_ci[1]:+.3f}" if summary.expectancy_ci else "-"
    win = f"{summary.win_rate * 100:.0f} %" if summary.win_rate is not None else "-"
    direction = f"{summary.direction_accuracy * 100:.0f} %" if summary.direction_accuracy is not None else "-"
    return (f"| {summary.label} | {summary.predictions} | {summary.triggered} | {win} | {direction} | "
            f"{f(summary.expectancy, '+.3f')} | {ci} | {f(summary.profit_factor, '.2f')} | "
            f"{f(summary.max_drawdown_r, '+.1f')} | {summary.effective_n} | {summary.sample} |")


HEADER = ("| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |\n"
          "|---|---|---|---|---|---|---|---|---|---|---|")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Full evaluation -> Markdown")
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "docs" / "BACKTEST_REPORT.md"))
    parser.add_argument("--warmup-days", type=int, default=120)
    parser.add_argument("--label", default=None, help="text in the title (e.g. OUT-OF-SAMPLE period)")
    args = parser.parse_args(argv)
    started = time.monotonic()
    p = DEFAULT_PARAMS
    symbols = parse_symbols(args.symbols)
    preloaded = {s: load_pair(s, p) for s in symbols}
    available = [s for s in symbols if len(preloaded[s].h1) >= 500]

    if not available:
        print("Nedostatek historie.")
        return 1

    first = min(preloaded[s].h1.ts[0] for s in available)
    last = max(preloaded[s].h1.ts[-1] for s in available)
    start = first + args.warmup_days * 86400
    config = BacktestConfig(available, start, last, p)
    title = f"# Vyhodnoceni modelu na historii{' - ' + args.label if args.label else ''}"
    out = [title, "", f"_vygenerovano {datetime.now(UTC):%Y-%m-%d %H:%M} UTC_", ""]
    out.append(f"- pary: {', '.join(available)}")
    out.append(f"- rozhodnuti: {datetime.fromtimestamp(start, tz=UTC):%Y-%m-%d} .. "
               f"{datetime.fromtimestamp(last, tz=UTC):%Y-%m-%d}, kazdou H4 svicku; zahrati indikatoru "
               f"{args.warmup_days} dni")
    out.append(f"- parametry (champion): `{p.fingerprint}`; naklady: spread z dat + {p.broker_markup_pips} pip "
               f"prirazka + {p.slippage_pips} pip skluz na stranu")
    if CANONICAL_SOURCE == "fxcm":
        out.append("- ceny: FXCM BID/ASK (hodinove svicky, minutove pro poradi v nejasne hodine; samostatny "
                   "vyzkumny archiv) - verejne ceny, ne ceny vaseho brokera")
    else:
        out.append("- ceny: Dukascopy BID/ASK (hodinove svicky; minutove kde jsou archivovane, jinak FXCM minuty jen "
                   "pro poradi v nejasne hodine) - verejne ceny, ne ceny vaseho brokera")
    out.append("- udalostni vrstva (kalendar) VYPNUTA - volny kalendar nema historii")
    out.append("")

    result = run(config, preloaded)
    bench = validation.benchmark(result)
    out += ["## 1. Model vs kontrola (modul 74)", "", HEADER, row(bench["model"]), row(bench["anti"]), ""]
    paired = bench["paired"]

    if paired.get("n", 0) >= 2:
        out.append(f"Na jedno rozhodnuti (neaktivovany limit = 0 R): model **{paired['model_r_per_decision']:+.3f} R**,"
                   f" nahodny smer (presne ocekavani = prumer modelu a anti-modelu) "
                   f"**{paired['random_r_per_decision']:+.3f} R**, n = {paired['n']}.")
        out.append(f"**Edge smeru vs nahoda (parovy test): {paired['edge']:+.3f} R "
                   f"(95% IS {paired['low']:+.3f} .. {paired['high']:+.3f}) -> "
                   f"{paired['verdict']}.**")
    out.append("")

    for label, b in (("model", bench["bounds_model"]), ("anti-model", bench["bounds_anti"])):
        if b.get("unknown"):
            out.append(f"- {label}: **poradi neznamo** u {b['unknown']} obchodu ({b['share'] * 100:.0f} %; SL/TP a vstup "
                       f"ve stejne hodinove svicce bez minutovych dat). Meze E na obchod: "
                       f"**{b['trade_worst']:+.3f} R** (vse SL) .. **{b['trade_best']:+.3f} R** (vse TP1); "
                       f"na rozhodnuti {b['decision_worst']:+.3f} .. {b['decision_best']:+.3f} R. Neznamy vysledek se "
                       f"nehada (modul 61) - zuzi ho jen minutova data.")

    resolved_by = {}

    for t in result.trades:
        if t.get("outcome_state") in ("TP1_BEFORE_SL", "SL_BEFORE_TP1", "NOT_ACTIVATED", "EXPIRED"):
            g = t.get("granularity") or "-"
            same = "1 min FXCM (stejny zdroj)" if CANONICAL_SOURCE == "fxcm" else "1 min Dukascopy"
            label = ("1 min FXCM (druhy zdroj, stejne udalosti)" if "FXCM" in g else
                     same if g.startswith("1min") else "hodinove svicky")
            resolved_by[label] = resolved_by.get(label, 0) + 1

    if resolved_by:
        out.append("- model, cim byl vysledek rozhodnut: " +
                   ", ".join(f"{k} {v}" for k, v in sorted(resolved_by.items(), key=lambda kv: -kv[1])))

    out.append("")
    out += ["## 2. Kvalita smeru bez geometrie obchodu (modul 66)", "",
            "Prumerny pohyb mid ceny ve smeru modelu (v ATR H1 v case rozhodnuti); nahodny smer = 0.", "",
            "| horizont | pohyb [ATR] | 95% IS (optimisticky, prekryvy) | zasah | n |", "|---|---|---|---|---|"]

    for hours, s in validation.signal_study(result.trades).items():
        out.append(f"| {hours} h | {s['mean_atr']:+.2f} | {s['ci'][0]:+.2f} .. {s['ci'][1]:+.2f} | "
                   f"{s['hit_rate'] * 100:.0f} % | {s['n']} |")

    out += ["", "## 3. Rozpad (modul 73) a kalibrace (modul 72)", ""]

    for name, rows in validation.regime_performance(result.trades).items():
        out += [f"### {name}", "", HEADER] + [row(s) for s in rows] + [""]

    out.append(f"Kalibrace trid duvery: **{calibration(result.trades)['verdict']}**")
    out += ["", "## 4. Taxonomie chyb (modul 69)", "", "| pocet | rodina: pripad |", "|---|---|"]
    out += [f"| {count} | {key} |" for key, count in taxonomy_table(result.trades).items()]
    out += ["", "Nejcastejsi duvody NEOBCHODOVAT:", ""]
    out += [f"- {count}x {reason}" for reason, count in sorted(result.no_trade_reasons.items(), key=lambda kv: -kv[1])[:10]]
    out += ["", "## 5. Ablace vrstev (modul 75)", "",
            "| varianta | predikci | vstupu | E na obchod [R] | meze E (neznamo) | edge smeru vs nahoda [R/rozhodnuti] | 95% IS |",
            "|---|---|---|---|---|---|---|"]

    for item in validation.ablation(config, preloaded):
        s_, pe, b = item["summary"], item["paired"], item["bounds"]
        bounds_text = f"{b['trade_worst']:+.3f} .. {b['trade_best']:+.3f}" if b.get("unknown") else "-"
        edge = f"{pe['edge']:+.3f}" if pe.get("n", 0) >= 2 else "-"
        ci = f"{pe['low']:+.3f} .. {pe['high']:+.3f}" if pe.get("n", 0) >= 2 else "-"
        out.append(f"| {item['label']} | {s_.predictions} | {s_.triggered} | "
                   f"{'-' if s_.expectancy is None else format(s_.expectancy, '+.3f')} | {bounds_text} | {edge} | {ci} |")

    if not args.quick:
        out += ["", "## 6. Robustnost (modul 76)", "",
                "| parametr | hodnota | obchodu | E [R] | meze E (neznamo) | edge smeru vs nahoda | 95% IS | znamenko E se otoci |",
                "|---|---|---|---|---|---|---|---|"]

        for item in validation.robustness(config, preloaded, bench["model"]):
            s, pe, b = item["summary"], item["paired"], item["bounds"]
            bounds_text = f"{b['trade_worst']:+.3f} .. {b['trade_best']:+.3f}" if b.get("unknown") else "-"
            edge = f"{pe['edge']:+.3f}" if pe.get("n", 0) >= 2 else "-"
            ci = f"{pe['low']:+.3f} .. {pe['high']:+.3f}" if pe.get("n", 0) >= 2 else "-"
            out.append(f"| {item['param']} | {item['value']} | {len(s.r_values)} | "
                       f"{'-' if s.expectancy is None else format(s.expectancy, '+.3f')} | {bounds_text} | {edge} | "
                       f"{ci} | {'ANO' if item['sensitive'] else 'ne'} |")

        out += ["", "## 7. Walk-forward out-of-sample (modul 77)", ""]
        wf = validation.walk_forward(available, start, last, p, list(validation.DEFAULT_GRID), preloaded)
        out += ["| okno testu | vybrane parametry (jen z minulosti) | OOS E vybrane | OOS E vychozi |", "|---|---|---|---|"]

        for fold in wf["folds"]:
            out.append(f"| {datetime.fromtimestamp(fold.test_start, tz=UTC):%Y-%m-%d} | {fold.chosen or 'vychozi'} | "
                       f"{'-' if fold.oos_chosen.expectancy is None else format(fold.oos_chosen.expectancy, '+.3f')} | "
                       f"{'-' if fold.oos_default.expectancy is None else format(fold.oos_default.expectancy, '+.3f')} |")

        out += ["", HEADER, row(wf["oos_chosen"]), row(wf["oos_default"]), ""]
        decision, reasons = promotion_gate(wf["oos_chosen"], wf["oos_default"], wf["difference"])
        out.append(f"**Promotion gate: {decision}**" + (" - " + "; ".join(reasons) if reasons else ""))

    out += ["", "## Zaver", "",
            "Cisla vyse jsou historicky pokus na verejnych cenach s modelovanymi naklady. Rozhoduje jen "
            "out-of-sample dukaz a dopredne testovani zamcenych predikci; zadna zmena se neprovadi automaticky.",
            "", f"_vypocet trval {time.monotonic() - started:.0f} s_"]
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
