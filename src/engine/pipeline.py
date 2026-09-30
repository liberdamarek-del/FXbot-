"""One analysis of one pair at one moment: technical -> fundamental ->
regime -> decision. Used unchanged by the live run and the backtest."""

from dataclasses import dataclass, replace

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

    if candidate.is_now and p.stability_atr > 0:
        stability_gate(candidate, tech, fund, reg, series, t, p, data_state, spread_price, live_quote_ok)

    return PairAnalysis(symbol, t, tech, fund, reg, candidate)


def stability_gate(candidate, tech, fund, reg, series, t, p, data_state, spread_price, live_quote_ok) -> None:
    """Module 49 / 140: a NOW signal must survive a small change of price and
    spread. If the decision changes under the perturbation the signal is
    FRAGILE and only a WAIT is allowed (the WAIT entry is recomputed by the
    normal rules on the unperturbed price)."""
    a = tech.h1.atr
    variants = [
        ("cena +", replace(tech, price=tech.price + p.stability_atr * a), spread_price),
        ("cena -", replace(tech, price=tech.price - p.stability_atr * a), spread_price),
        ("spread x2", tech, None if spread_price is None else 2 * spread_price),
    ]
    fragile = []

    for label, variant_tech, variant_spread in variants:
        other = decision.decide(candidate.symbol, t, variant_tech, fund, reg, series.h1, p, data_state,
                                variant_spread, live_quote_ok)

        if other.decision != candidate.decision:
            fragile.append(f"{label}: {other.decision}")

    if not fragile:
        candidate.gates.append(decision.Gate("STABILITY", "PASS", "rozhodnuti stabilni pri malem posunu ceny/spreadu"))
        return

    candidate.gates.append(decision.Gate("STABILITY", "FAIL", "krehky signal - " + "; ".join(fragile)))
    # a fragile NOW becomes a WAIT at the pullback entry (below the price for
    # BUY), never a limit at the current price (that would be a NOW again)
    sign = 1.0 if candidate.direction == "BUY" else -1.0
    anchor = candidate.level.price if candidate.level is not None else tech.h1.ema20
    wait_entry = anchor + sign * p.entry_offset_atr * a * 0.5

    if sign * (tech.price - wait_entry) <= 0 or sign * (wait_entry - candidate.stop) <= 0:
        candidate.thesis_direction = candidate.direction
        candidate.decision, candidate.direction = "NO TRADE", "NONE"
        candidate.reasons.insert(0, "krehky signal a bez platneho cekaciho vstupu (modul 49)")
        return

    risk = sign * (wait_entry - candidate.stop)
    reward = sign * (candidate.targets[0] - wait_entry)
    candidate.entry = wait_entry
    candidate.zone_low, candidate.zone_high = min(anchor, wait_entry), max(anchor, wait_entry)
    candidate.rr_gross = reward / risk
    candidate.rr_net = (reward - candidate.cost_price) / (risk + candidate.cost_price)
    candidate.decision = f"WAIT FOR {candidate.direction}"
    candidate.reasons.append("NOW blokovano: krehky signal (modul 49)")
