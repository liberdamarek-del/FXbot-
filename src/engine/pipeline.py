"""One analysis of one pair at one moment: technical -> fundamental ->
regime -> decision. Used unchanged by the live run and the backtest."""

from dataclasses import dataclass

from src.engine import decision, fundamental, regime, technical
from src.engine.data import PairSeries
from src.engine.params import ModelParams
from src.instruments import get_instrument


@dataclass
class PairAnalysis:
    symbol: str
    t: int
    tech: technical.TechnicalView
    fund: fundamental.FundamentalView
    regime: regime.RegimeView
    candidate: decision.Candidate


def analyze_pair(
    series: PairSeries,
    t: int,
    p: ModelParams,
    data_state: str,
    spread_price: float | None,
    event_mode: str = "AVAILABLE",      # AVAILABLE / ABLATED (backtest without calendar)
    price: float | None = None,
    live_quote_ok: bool = True,
    use_fundamentals: bool = True,
) -> PairAnalysis:
    symbol = series.symbol
    instrument = get_instrument(symbol)
    tech = technical.analyze(symbol, t, series.d1, series.h4, series.h1, p, price)
    events = None
    events_24h = None

    if event_mode == "AVAILABLE":
        from src.fundamental.calendar import event_window, events_between

        currencies = (instrument.base, instrument.quote)
        events = event_window(currencies, t, p.event_pre_hours, p.event_post_minutes)
        events_24h = len(events_between(t, t + 86400, currencies, "High"))

    if use_fundamentals:
        fund = fundamental.analyze(symbol, t, series.d1, p, events, event_mode == "AVAILABLE")
    else:
        fund = fundamental.FundamentalView(symbol, t, fundamental.CurrencyState(instrument.base),
                                           fundamental.CurrencyState(instrument.quote))

    if event_mode == "ABLATED":
        fund.event_layer = "ABLATED"

    reg = regime.diagnose(series.d1, series.h1, t, fund.risk_regime, events_24h)
    candidate = decision.decide(symbol, t, tech, fund, reg, series.h1, p, data_state, spread_price, live_quote_ok)
    return PairAnalysis(symbol, t, tech, fund, reg, candidate)
