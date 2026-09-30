from datetime import datetime

from src.backtest_engine import BacktestResult
from src.backtest_fingerprint import fingerprint_bars
from src.backtest_pipeline import PipelineResult
from src.backtest_results import save_backtest_result


def persist_pipeline_result(
    run_key: str,
    symbol: str,
    timeframe: str,
    source: str,
    result: PipelineResult,
    strategy_name: str,
    strategy_version: str,
    created_at: datetime,
    bars=None,
) -> int:
    if not run_key.strip():
        raise ValueError("run_key must not be empty")

    if not symbol.strip():
        raise ValueError("symbol must not be empty")

    if not timeframe.strip():
        raise ValueError("timeframe must not be empty")

    if not source.strip():
        raise ValueError("source must not be empty")

    if not strategy_name.strip():
        raise ValueError("strategy_name must not be empty")

    if not strategy_version.strip():
        raise ValueError("strategy_version must not be empty")

    if created_at.tzinfo is None:
        raise ValueError(
            "created_at must contain timezone information"
        )

    backtest_result = BacktestResult(
        bars_processed=result.bars_processed,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )

    data_fingerprint = None

    if bars is not None:
        if len(bars) != result.bars_processed:
            raise ValueError(
                "bars count must match pipeline result"
            )

        data_fingerprint = fingerprint_bars(bars)

    return save_backtest_result(
        run_key=run_key,
        created_at=created_at,
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        result=backtest_result,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        status="COMPLETED",
        data_fingerprint=data_fingerprint,
    )
