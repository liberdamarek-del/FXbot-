"""Benchmark, ablation, robustness, walk-forward (modules 73-77, 142, 143).

All variants run on the SAME preloaded history, decision times, costs and
coverage rules as the model (module 74); no variant gets better data.

benchmark      model vs placebo (same decisions and geometry, random
               direction): the only honest answer to "does the direction
               add anything?"
ablation       switch off one layer at a time (fundamentals, no-chase,
               R:R gate) and see what each layer really adds (module 75)
robustness     reasonable perturbations of each threshold; a result whose
               sign flips under a small change is SENSITIVE (module 76)
walk-forward   choose parameters only on the past window, evaluate on the
               following unseen window, roll forward (module 77). The
               chosen set stays a CHALLENGER until the promotion gate says
               otherwise (src/stats/registry.py)
"""

import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from src.engine.backtest import BacktestConfig, run
from src.engine.params import ModelParams
from src.stats.performance import Summary, breakdown, summarize

UTC = timezone.utc


def difference(model: Summary, control: Summary) -> dict:
    """Expectancy difference with a normal-approximation 95 % interval."""
    if not model.r_values or not control.r_values:
        return {"difference": None}

    def var(values):
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1)

    diff = model.expectancy - control.expectancy
    se = math.sqrt(var(model.r_values) / len(model.r_values) + var(control.r_values) / len(control.r_values))
    return {"difference": diff, "low": diff - 1.96 * se, "high": diff + 1.96 * se,
            "significant": (diff - 1.96 * se) > 0}


def benchmark(result) -> dict:
    model = summarize(result.trades, "model")
    placebo = summarize(result.placebo, "placebo (nahodny smer)")
    return {"model": model, "placebo": placebo, "difference": difference(model, placebo)}


ABLATIONS = (
    ("FULL", {}, True),
    ("BEZ FUNDAMENTU", {"require_fundamental_for_now": False}, False),
    ("BEZ NO-CHASE", {"no_chase_atr": 99.0}, True),
    ("R:R >= 1.0", {"min_rr": 1.0}, True),
    ("R:R >= 2.0", {"min_rr": 2.0}, True),
)


def ablation(config: BacktestConfig, preloaded: dict, progress=None) -> list[tuple[str, Summary, Summary]]:
    rows = []

    for label, changes, fundamentals in ABLATIONS:
        variant = replace(config, params=config.params.with_changes(**changes), use_fundamentals=fundamentals,
                          label=label)
        result = run(variant, preloaded)
        rows.append((label, summarize(result.trades, label), summarize(result.placebo, "placebo")))

        if progress:
            progress(rows[-1][1].line())

    return rows


PERTURBATIONS = {
    "entry_offset_atr": (0.2, 0.4),
    "stop_buffer_atr": (0.35, 0.65),
    "max_tp1_atr": (2.5, 3.5),
    "trend_slope_atr": (0.1, 0.2),
    "broker_markup_pips": (0.0, 1.0),
    "near_level_atr": (0.45, 0.75),
}


def robustness(config: BacktestConfig, preloaded: dict, baseline: Summary | None = None,
               progress=None) -> list[dict]:
    baseline = baseline or summarize(run(config, preloaded).trades, "baseline")
    rows = []

    for name, values in PERTURBATIONS.items():
        for value in values:
            variant = replace(config, params=config.params.with_changes(**{name: value}), placebo_seed=None)
            summary = summarize(run(variant, preloaded).trades, f"{name}={value}")
            flips = (baseline.expectancy is not None and summary.expectancy is not None
                     and (baseline.expectancy > 0) != (summary.expectancy > 0))
            rows.append({"param": name, "value": value, "summary": summary, "sensitive": flips})

            if progress:
                progress(summary.line() + ("  SENSITIVE" if flips else ""))

    return rows


@dataclass
class Fold:
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    chosen: dict = field(default_factory=dict)
    chosen_train: Summary | None = None
    oos_chosen: Summary | None = None
    oos_default: Summary | None = None


def walk_forward(symbols: list[str], start_ts: int, end_ts: int, base: ModelParams, grid: list[dict],
                 preloaded: dict, train_days: int = 365, test_days: int = 90, min_trades: int = 30,
                 progress=None) -> dict:
    """Rolling walk-forward. Parameters are chosen on the training window
    only (highest expectancy with at least min_trades trades), then frozen
    and evaluated on the next unseen window."""
    folds = []
    cursor = start_ts
    day = 86400
    oos_chosen_trades, oos_default_trades = [], []

    while cursor + (train_days + test_days) * day <= end_ts:
        fold = Fold(cursor, cursor + train_days * day, cursor + train_days * day,
                    cursor + (train_days + test_days) * day)
        best = None

        for changes in grid:
            params = base.with_changes(**changes)
            cfg = BacktestConfig(symbols, fold.train_start, fold.train_end, params, placebo_seed=None)
            summary = summarize(run(cfg, preloaded).trades, str(changes))

            if len(summary.r_values) >= min_trades and summary.expectancy is not None:
                if best is None or summary.expectancy > best[1].expectancy:
                    best = (changes, summary)

        fold.chosen, fold.chosen_train = best if best else ({}, None)
        chosen_cfg = BacktestConfig(symbols, fold.test_start, fold.test_end, base.with_changes(**fold.chosen),
                                    placebo_seed=None)
        default_cfg = BacktestConfig(symbols, fold.test_start, fold.test_end, base, placebo_seed=None)
        chosen_trades = run(chosen_cfg, preloaded).trades
        default_trades = run(default_cfg, preloaded).trades
        fold.oos_chosen = summarize(chosen_trades, "OOS vybrane")
        fold.oos_default = summarize(default_trades, "OOS vychozi")
        oos_chosen_trades += chosen_trades
        oos_default_trades += default_trades
        folds.append(fold)

        if progress:
            label = datetime.fromtimestamp(fold.test_start, tz=UTC).strftime("%Y-%m-%d")
            progress(f"fold {label}: vybrano {fold.chosen or 'vychozi'} | "
                     f"OOS E vybrane {fold.oos_chosen.expectancy} / vychozi {fold.oos_default.expectancy}")

        cursor += test_days * day

    chosen_all = summarize(oos_chosen_trades, "OOS walk-forward (vybrane)")
    default_all = summarize(oos_default_trades, "OOS vychozi parametry")
    return {"folds": folds, "oos_chosen": chosen_all, "oos_default": default_all,
            "difference": difference(chosen_all, default_all)}


DEFAULT_GRID = (
    {},
    {"entry_offset_atr": 0.2},
    {"entry_offset_atr": 0.4},
    {"max_tp1_atr": 2.5},
    {"stop_buffer_atr": 0.65},
    {"min_rr": 2.0},
)


def regime_performance(trades: list[dict]) -> dict[str, list[Summary]]:
    """Module 73: performance split by the regime components."""
    def part(index):
        return lambda t: (t.get("regime") or "?").split("/")[index] if t.get("regime") else "?"

    return {
        "struktura": breakdown(trades, part(0)),
        "volatilita": breakdown(trades, part(1)),
        "riziko": breakdown(trades, part(2)),
        "smer": breakdown(trades, lambda t: t.get("direction")),
        "setup": breakdown(trades, lambda t: t.get("setup_type")),
        "rozhodnuti": breakdown(trades, lambda t: t.get("decision")),
        "par": breakdown(trades, lambda t: t.get("symbol")),
        "duvera": breakdown(trades, lambda t: t.get("confidence")),
    }
