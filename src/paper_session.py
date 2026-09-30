from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.historical_data import HistoricalBar
from src.intrabar_policy import IntrabarExit
from src.paper_audit import record_paper_event
from src.paper_trading import PaperTradingEngine


# What to do when stop-loss and take-profit are both reachable inside one
# bar and the order of the two touches cannot be known from OHLC data.
#
# CONTINUE (legacy, default): keep the position open and keep both levels
#   active. Behaviour is unchanged from earlier versions. The trade may
#   later close at an unrelated price, so its result is not trustworthy.
# CLOSE_UNRESOLVED: close the position at the OPEN of the ambiguous bar
#   (the last price known before the unknown sequence) with reason
#   UNRESOLVED_SEQUENCE. No order of touches is assumed. The trade is
#   counted in unresolved_trades and must be excluded from win/loss
#   statistics.
AMBIGUOUS_CONTINUE = "CONTINUE"
AMBIGUOUS_CLOSE_UNRESOLVED = "CLOSE_UNRESOLVED"
AMBIGUOUS_POLICIES = (AMBIGUOUS_CONTINUE, AMBIGUOUS_CLOSE_UNRESOLVED)


@dataclass(frozen=True)
class PaperSessionResult:
    symbol: str
    timeframe: str
    started_at: datetime
    finished_at: datetime
    bars_processed: int
    trades: int
    realized_pnl: Decimal
    final_equity: Decimal
    stop_loss_exits: int
    take_profit_exits: int
    ambiguous_bars: int
    forced_close: bool
    unresolved_trades: int = 0


def run_paper_session(
    bars: list[HistoricalBar],
    engine: PaperTradingEngine,
    symbol: str,
    timeframe: str,
    ambiguous_policy: str = AMBIGUOUS_CONTINUE,
) -> PaperSessionResult:
    if ambiguous_policy not in AMBIGUOUS_POLICIES:
        raise ValueError(
            f"unsupported ambiguous_policy: {ambiguous_policy}"
        )

    if not bars:
        raise ValueError("bars must not be empty")

    if not symbol.strip():
        raise ValueError("symbol must not be empty")

    if not timeframe.strip():
        raise ValueError("timeframe must not be empty")

    previous_time = None

    for bar in bars:
        if bar.bar_time.tzinfo is None:
            raise ValueError("bar_time must contain timezone information")

        if previous_time is not None and bar.bar_time <= previous_time:
            raise ValueError("bars must be strictly chronological")

        if bar.symbol != symbol:
            raise ValueError("bar symbol does not match session symbol")

        if bar.timeframe != timeframe:
            raise ValueError("bar timeframe does not match session timeframe")

        previous_time = bar.bar_time

    started_at = bars[0].bar_time
    finished_at = bars[-1].bar_time

    trades = 0
    stop_loss_exits = 0
    take_profit_exits = 0
    ambiguous_bars = 0
    unresolved_trades = 0
    forced_close = False

    for bar in bars:
        exit_signal = engine.check_ohlc_risk_exit(
            market_time=bar.bar_time,
            bar_open=bar.open,
            bar_high=bar.high,
            bar_low=bar.low,
        )

        if exit_signal == IntrabarExit.AMBIGUOUS:
            ambiguous_bars += 1

            open_position = engine.position_simulator.position

            # Always leave an audit trail of the unresolved sequence.
            record_paper_event(
                event_time=bar.bar_time,
                symbol=symbol,
                timeframe=timeframe,
                event_type="AMBIGUOUS",
                side=open_position.side.value if open_position else None,
                reason="SL_AND_TP_IN_SAME_BAR",
            )

            if (
                ambiguous_policy == AMBIGUOUS_CLOSE_UNRESOLVED
                and open_position is not None
            ):
                engine.close_position(
                    exit_time=bar.bar_time,
                    exit_price=bar.open,
                    reason="UNRESOLVED_SEQUENCE",
                )

                trades += 1
                unresolved_trades += 1

            continue

        if exit_signal == IntrabarExit.STOP_LOSS:
            if engine.position_simulator.position is None:
                raise RuntimeError("STOP_LOSS detected without open position")

            if engine.stop_loss is None:
                raise RuntimeError("STOP_LOSS detected without stop_loss")

            engine.close_position(
                exit_time=bar.bar_time,
                exit_price=engine.stop_loss,
                reason="STOP_LOSS",
            )

            trades += 1
            stop_loss_exits += 1
            continue

        if exit_signal == IntrabarExit.TAKE_PROFIT:
            if engine.position_simulator.position is None:
                raise RuntimeError("TAKE_PROFIT detected without open position")

            if engine.take_profit is None:
                raise RuntimeError("TAKE_PROFIT detected without take_profit")

            engine.close_position(
                exit_time=bar.bar_time,
                exit_price=engine.take_profit,
                reason="TAKE_PROFIT",
            )

            trades += 1
            take_profit_exits += 1
            continue

    if engine.position_simulator.position is not None:
        last_bar = bars[-1]

        engine.close_position(
            exit_time=last_bar.bar_time,
            exit_price=last_bar.close,
            reason="END_OF_DATA",
        )

        trades += 1
        forced_close = True

    if engine.position_simulator.position is not None:
        raise RuntimeError("paper session ended with an open position")

    return PaperSessionResult(
        symbol=symbol,
        timeframe=timeframe,
        started_at=started_at,
        finished_at=finished_at,
        bars_processed=len(bars),
        trades=trades,
        realized_pnl=engine.account.realized_pnl,
        final_equity=engine.account.cash,
        stop_loss_exits=stop_loss_exits,
        take_profit_exits=take_profit_exits,
        ambiguous_bars=ambiguous_bars,
        forced_close=forced_close,
        unresolved_trades=unresolved_trades,
    )


def run_and_persist_paper_session(
    bars: list[HistoricalBar],
    engine: PaperTradingEngine,
    symbol: str,
    timeframe: str,
    session_key: str,
    created_at: datetime,
    ambiguous_policy: str = AMBIGUOUS_CONTINUE,
) -> PaperSessionResult:
    from src.paper_session_audit import save_paper_session

    result = run_paper_session(
        bars=bars,
        engine=engine,
        symbol=symbol,
        timeframe=timeframe,
        ambiguous_policy=ambiguous_policy,
    )

    save_paper_session(
        session_key=session_key,
        created_at=created_at,
        symbol=result.symbol,
        timeframe=result.timeframe,
        started_at=result.started_at,
        finished_at=result.finished_at,
        bars_processed=result.bars_processed,
        trades=result.trades,
        realized_pnl=result.realized_pnl,
        final_equity=result.final_equity,
        stop_loss_exits=result.stop_loss_exits,
        take_profit_exits=result.take_profit_exits,
        ambiguous_bars=result.ambiguous_bars,
        forced_close=result.forced_close,
    )

    return result
