from dataclasses import dataclass
from decimal import Decimal

from src.backtest_pipeline import PipelineResult
from src.backtest_results import get_backtest_run


@dataclass(frozen=True)
class BacktestReport:
    run_key: str
    symbol: str
    timeframe: str
    source: str
    started_at: str | None
    finished_at: str | None
    bars_processed: int
    strategy_name: str
    strategy_version: str
    status: str
    signals_generated: int
    executions: int
    trades: int
    net_pnl: Decimal


def build_backtest_report(
    run_key: str,
    pipeline_result: PipelineResult,
) -> BacktestReport:
    stored = get_backtest_run(run_key)

    if stored is None:
        raise ValueError(
            f"Backtest run not found: {run_key}"
        )

    if stored["bars_processed"] != pipeline_result.bars_processed:
        raise ValueError(
            "Stored bars_processed does not match pipeline result"
        )

    net_pnl = sum(
        (trade.net_pnl for trade in pipeline_result.trades),
        Decimal("0"),
    )

    return BacktestReport(
        run_key=stored["run_key"],
        symbol=stored["symbol"],
        timeframe=stored["timeframe"],
        source=stored["source"],
        started_at=stored["started_at"],
        finished_at=stored["finished_at"],
        bars_processed=stored["bars_processed"],
        strategy_name=stored["strategy_name"],
        strategy_version=stored["strategy_version"],
        status=stored["status"],
        signals_generated=pipeline_result.signals_generated,
        executions=pipeline_result.executions,
        trades=len(pipeline_result.trades),
        net_pnl=net_pnl,
    )


def format_backtest_report(
    report: BacktestReport,
) -> str:
    lines = [
        "=" * 70,
        "BACKTEST REPORT",
        "=" * 70,
        f"RUN KEY: {report.run_key}",
        f"SYMBOL: {report.symbol}",
        f"TIMEFRAME: {report.timeframe}",
        f"SOURCE: {report.source}",
        f"STARTED: {report.started_at}",
        f"FINISHED: {report.finished_at}",
        f"BARS: {report.bars_processed}",
        f"STRATEGY: {report.strategy_name}",
        f"STRATEGY VERSION: {report.strategy_version}",
        f"STATUS: {report.status}",
        f"SIGNALS: {report.signals_generated}",
        f"EXECUTIONS: {report.executions}",
        f"TRADES: {report.trades}",
        f"NET PNL: {report.net_pnl}",
        "=" * 70,
    ]

    return "\n".join(lines)
