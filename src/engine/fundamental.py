"""Per-pair fundamental evidence as of time t (modules 17-33, 36).

A currency pair is the difference of two currencies, so every factor is
computed as base minus quote. All inputs are point-in-time
(src/fundamental/store.py): at time t only values that were public at t
are used.

Factors and how they become evidence (all thresholds in ModelParams):

RATES_REPRICING  change of the short-rate differential over ~20 business
                 days (module 21: the change of the expected path matters,
                 not the level). Widening in favour of the base -> BUY.
CARRY            policy-rate differential divided by the pair's realized
                 volatility (module 24). Only a context-weight vote; carry
                 alone never makes a trade.
POSITIONING      CFTC leveraged funds, z-score of base minus quote (module
                 25). Extreme = crowded = COUNTERFORCE (squeeze risk), a
                 4-week build-up in the trade direction = weak flow support.
RISK             global regime from VIX, S&P 500 and high-yield spreads,
                 multiplied by the pair's MEASURED correlation with equities
                 over the last 120 days (module 31: no mechanical safe-haven
                 label). Used only when |correlation| is material.
COMMODITY        CAD pairs vs WTI, only with a measured correlation
                 (module 30: CAD is not automatically oil).
INTERVENTION     JPY: a fast JPY-weakening move is flagged as intervention
                 RISK CONTEXT only - price alone is never evidence of
                 intervention (module 33).
EVENT            high-impact calendar events of either currency (module 47)
                 -> gate, not direction.
"""

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from src.engine.evidence import (
    CARRY,
    COMMODITY,
    DATA,
    EVENT,
    INTERVENTION,
    POSITIONING,
    RATES_REPRICING,
    RISK,
    Evidence,
)
from src.engine.params import ModelParams
from src.engine.series import PriceSeries
from src.fundamental.catalog import SERIES_BY_ID, SHORT_RATE
from src.fundamental.store import PointInTimeSeries, load_series
from src.instruments import get_instrument
from src.path_archive import trading_date

UTC = timezone.utc
STALE_DAYS = 7          # a daily series older than this at t is flagged


@dataclass
class CurrencyState:
    currency: str
    short_rate: float | None = None
    short_rate_past: float | None = None
    short_series: str | None = None
    short_proxy_note: str | None = None
    short_as_of: date | None = None
    policy: float | None = None
    policy_6m_ago: float | None = None
    cot_z: float | None = None
    cot_change_4w: float | None = None
    cot_as_of: date | None = None
    quality: str = "A"
    notes: list = field(default_factory=list)


@dataclass
class FundamentalView:
    symbol: str
    t: int
    base: CurrencyState
    quote: CurrencyState
    evidence: list = field(default_factory=list)
    risk_regime: str = "UNKNOWN"
    equity_corr: float | None = None
    events_pre: list = field(default_factory=list)
    events_post: list = field(default_factory=list)
    event_layer: str = "AVAILABLE"      # AVAILABLE / NOT_AVAILABLE (no calendar for t)
    data_gaps: list = field(default_factory=list)


def _value_days_ago(series: PointInTimeSeries, t: int, days: int):
    """(value now, value ~days calendar days earlier, date now), as known at t."""
    now = series.asof(t)

    if now is None:
        return None, None, None

    past = series.asof_date(t, now.obs_date - timedelta(days=days))
    return now.value, (past.value if past else None), now.obs_date


def currency_state(currency: str, t: int, p: ModelParams) -> CurrencyState:
    """Cached per (currency, t): all pairs of one run share the result."""
    state = _currency_state(currency, t, p)
    return CurrencyState(state.currency, state.short_rate, state.short_rate_past, state.short_series,
                         state.short_proxy_note, state.short_as_of, state.policy, state.policy_6m_ago,
                         state.cot_z, state.cot_change_4w, state.cot_as_of, state.quality, list(state.notes))


@lru_cache(maxsize=256)
def _currency_state(currency: str, t: int, p: ModelParams) -> CurrencyState:
    state = CurrencyState(currency)
    t_date = datetime.fromtimestamp(t, tz=UTC).date()

    series_id, proxy_note = SHORT_RATE.get(currency, (None, None))

    if series_id:
        spec = SERIES_BY_ID[series_id]
        now, past, as_of = _value_days_ago(load_series(series_id), t, int(p.repricing_days * 1.4))
        state.short_rate, state.short_rate_past, state.short_as_of = now, past, as_of
        state.short_series, state.short_proxy_note = series_id, proxy_note

        if proxy_note:
            state.quality = "C"
            state.notes.append(proxy_note)
        else:
            state.quality = spec.quality

        if as_of is None:
            state.notes.append(f"{series_id}: zadna data k datu")
            state.quality = "D"
        elif (t_date - as_of).days > STALE_DAYS:
            state.notes.append(f"{series_id}: posledni hodnota {as_of} (starsi nez {STALE_DAYS} dni)")
            state.quality = "C" if state.quality in ("A", "B") else state.quality

    policy_series = load_series(f"{currency}.POLICY")
    policy_now = policy_series.asof(t)

    if policy_now is not None:
        state.policy = policy_now.value
        past = policy_series.asof_date(t, policy_now.obs_date - timedelta(days=182))
        state.policy_6m_ago = past.value if past else None

    if currency != "USD":
        cot = load_series(f"COT.{currency}.LEV_NET_PCT")
        history = cot.history(t, p.cot_lookback_weeks)

        if len(history) >= 26:
            values = [h.value for h in history]
            mean = sum(values) / len(values)
            sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
            state.cot_z = (values[-1] - mean) / sd if sd > 0 else 0.0
            state.cot_change_4w = values[-1] - values[-5] if len(values) >= 5 else None
            state.cot_as_of = history[-1].obs_date

    return state


def _returns_by_date(values: list[tuple[date, float]]) -> dict[date, float]:
    out = {}

    for (d0, v0), (d1, v1) in zip(values, values[1:]):
        if v0 and v1:
            out[d1] = math.log(v1 / v0)

    return out


def _pair_daily_returns(d1: PriceSeries, i: int, days: int) -> dict[date, float]:
    start = max(1, i - days)
    points = [(trading_date(d1.ts[j]), d1.close[j]) for j in range(start - 1, i + 1)]
    return _returns_by_date(points)


def correlation(a: dict[date, float], b: dict[date, float], minimum: int = 40) -> float | None:
    common = sorted(set(a) & set(b))

    if len(common) < minimum:
        return None

    x = [a[d] for d in common]
    y = [b[d] for d in common]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    sxx = sum((u - mx) ** 2 for u in x)
    syy = sum((v - my) ** 2 for v in y)

    if sxx <= 0 or syy <= 0:
        return None

    return sxy / math.sqrt(sxx * syy)


_corr_cache: dict = {}


def _corr_cached(d1: PriceSeries, i: int, series_id: str, t: int, p: ModelParams) -> float | None:
    """Correlation of the pair's daily returns with a market series as known
    at t. Cached by the newest observation known at t (inputs change once a
    day), so no value published after t can enter."""
    other_series = load_series(series_id)
    newest = other_series.asof(t)
    key = (id(d1), d1.symbol, i, series_id, newest.obs_date if newest else None, p.risk_beta_days)

    if key not in _corr_cache:
        if len(_corr_cache) > 20000:
            _corr_cache.clear()
        other = other_series.history(t, p.risk_beta_days + 20)
        _corr_cache[key] = correlation(_pair_daily_returns(d1, i, p.risk_beta_days),
                                       _returns_by_date([(o.obs_date, o.value) for o in other]))

    return _corr_cache[key]


@lru_cache(maxsize=256)
def risk_regime(t: int, p: ModelParams) -> tuple[str, list[str]]:
    """RISK_ON / RISK_OFF / NEUTRAL / UNKNOWN from VIX, S&P 500, HY spread."""
    notes = []
    vix_now, vix_past, vix_date = _value_days_ago(load_series("GLOBAL.VIX"), t, 7)
    spx_now, spx_past, _ = _value_days_ago(load_series("GLOBAL.SPX"), t, 28)
    hy_now, hy_past, _ = _value_days_ago(load_series("GLOBAL.HY_OAS"), t, 28)

    if vix_now is None or vix_past is None:
        return "UNKNOWN", ["VIX neni k dispozici"]

    off = on = 0
    vix_change = vix_now - vix_past
    notes.append(f"VIX {vix_now:.1f} ({vix_change:+.1f} za tyden)")

    if vix_change >= p.risk_vix_jump or vix_now >= 30:
        off += 1
    elif vix_change <= -1.5 and vix_now < 20:
        on += 1

    if spx_now and spx_past:
        spx_ret = spx_now / spx_past - 1.0
        notes.append(f"S&P 500 {spx_ret * 100:+.1f} % za 4 tydny")

        if spx_ret <= -0.05:
            off += 1
        elif spx_ret >= 0.03:
            on += 1

    if hy_now is not None and hy_past is not None:
        hy_change = (hy_now - hy_past) * 100
        notes.append(f"HY spread {hy_change:+.0f} bp za 4 tydny")

        if hy_change >= 40:
            off += 1
        elif hy_change <= -25:
            on += 1

    if off >= 2 or (off == 1 and on == 0 and vix_now >= 25):
        return "RISK_OFF", notes

    if on >= 2 and off == 0:
        return "RISK_ON", notes

    return "NEUTRAL", notes


def analyze(
    symbol: str,
    t: int,
    d1: PriceSeries,
    p: ModelParams,
    events: dict | None = None,
    event_layer_available: bool = True,
) -> FundamentalView:
    instrument = get_instrument(symbol)
    base = currency_state(instrument.base, t, p)
    quote = currency_state(instrument.quote, t, p)
    view = FundamentalView(symbol, t, base, quote)
    ev = view.evidence
    quality = min(base.quality, quote.quality, key=lambda q: "ABCD".index(q))

    for state in (base, quote):
        for note in state.notes:
            view.data_gaps.append(f"{state.currency}: {note}")

    # ------------------------------------------------------------ rates repricing
    if None not in (base.short_rate, base.short_rate_past, quote.short_rate, quote.short_rate_past):
        diff_now = base.short_rate - quote.short_rate
        diff_past = base.short_rate_past - quote.short_rate_past
        change_bp = (diff_now - diff_past) * 100

        if abs(change_bp) >= p.repricing_min_bp:
            direction = "BUY" if change_bp > 0 else "SELL"
            weight = 2 if abs(change_bp) >= 2 * p.repricing_min_bp else 1
            winner = instrument.base if change_bp > 0 else instrument.quote
            ev.append(Evidence(
                RATES_REPRICING, direction, weight,
                f"sazbovy diferencial {instrument.base}-{instrument.quote} {change_bp:+.0f} bp za ~{p.repricing_days} obch. dni "
                f"(nyni {diff_now:+.2f} %) - trh precenuje sazby ve prospech {winner}",
                "DERIVED METRIC", f"{base.short_series}, {quote.short_series}",
                str(min(base.short_as_of, quote.short_as_of)), quality,
            ))
        else:
            ev.append(Evidence(
                RATES_REPRICING, "NONE", 0,
                f"sazbovy diferencial beze zmeny ({change_bp:+.0f} bp, nyni {diff_now:+.2f} %)",
                "DERIVED METRIC", f"{base.short_series}, {quote.short_series}",
                str(min(base.short_as_of, quote.short_as_of)), quality, "CONTEXT",
            ))
    else:
        view.data_gaps.append("kratke sazby nejsou k dispozici pro obe meny - RATES vrstva BLOKOVANA")

    # ------------------------------------------------------------ carry (vol adjusted)
    i = d1.index_at(t)
    realized_vol = None

    if i >= 61:
        rets = [math.log(d1.close[j] / d1.close[j - 1]) for j in range(i - 59, i + 1)]
        mean = sum(rets) / len(rets)
        realized_vol = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(260) * 100

    if base.policy is not None and quote.policy is not None:
        carry = base.policy - quote.policy

        if realized_vol and abs(carry) >= p.carry_min_pct:
            ratio = carry / realized_vol
            direction = "BUY" if carry > 0 else "SELL"
            ev.append(Evidence(
                CARRY, direction, 1 if abs(ratio) >= 0.3 else 0,
                f"carry {carry:+.2f} % p.a. pri volatilite {realized_vol:.1f} % (pomer {ratio:+.2f})"
                + ("" if abs(ratio) >= 0.3 else " - slabe vuci volatilite, jen kontext"),
                "DERIVED METRIC", f"{instrument.base}.POLICY, {instrument.quote}.POLICY", "",
                "A", "DIRECTION" if abs(ratio) >= 0.3 else "CONTEXT",
            ))

        for state in (base, quote):
            if state.policy_6m_ago is not None and abs(state.policy - state.policy_6m_ago) >= 0.2:
                trend = "zvysuje" if state.policy > state.policy_6m_ago else "snizuje"
                ev.append(Evidence(
                    CARRY, "NONE", 0,
                    f"{state.currency}: centralni banka {trend} sazby ({state.policy_6m_ago:.2f} -> {state.policy:.2f} % za 6 mesicu)",
                    "OBSERVATION", f"{state.currency}.POLICY", "", "A", "CONTEXT",
                ))

    # ------------------------------------------------------------ positioning
    z_base = base.cot_z if instrument.base != "USD" else 0.0
    z_quote = quote.cot_z if instrument.quote != "USD" else 0.0

    if z_base is not None and z_quote is not None and (instrument.base != "USD" or instrument.quote != "USD"):
        pair_z = z_base - z_quote

        if abs(pair_z) >= p.cot_z_extreme:
            crowded = "BUY" if pair_z > 0 else "SELL"
            ev.append(Evidence(
                POSITIONING, "SELL" if crowded == "BUY" else "BUY", 1,
                f"pozicovani spekulantu extremni (z {pair_z:+.1f}) - preplneny {crowded} = riziko squeeze",
                "INTERPRETATION", "CFTC TFF leveraged funds", str(base.cot_as_of or quote.cot_as_of), "B", "COUNTERFORCE",
            ))

        change = (base.cot_change_4w or 0.0) - (quote.cot_change_4w or 0.0)

        if abs(change) >= 5.0:
            ev.append(Evidence(
                POSITIONING, "BUY" if change > 0 else "SELL", 1,
                f"spekulanti za 4 tydny pridali {change:+.1f} % OI ve prospech {instrument.base if change > 0 else instrument.quote}",
                "OBSERVATION", "CFTC TFF leveraged funds", str(base.cot_as_of or quote.cot_as_of), "B",
            ))

    # ------------------------------------------------------------ risk regime x measured beta
    regime, notes = risk_regime(t, p)
    view.risk_regime = regime

    if i >= 2:
        view.equity_corr = _corr_cached(d1, i, "GLOBAL.SPX", t, p)

    if regime in ("RISK_ON", "RISK_OFF") and view.equity_corr is not None:
        if abs(view.equity_corr) >= p.risk_beta_min_corr:
            sign = 1 if view.equity_corr > 0 else -1
            regime_sign = 1 if regime == "RISK_ON" else -1
            direction = "BUY" if sign * regime_sign > 0 else "SELL"
            ev.append(Evidence(
                RISK, direction, 1,
                f"rezim {regime} ({'; '.join(notes)}); par koreluje s akciemi {view.equity_corr:+.2f} (120 dni)",
                "INTERPRETATION", "VIXCLS, SP500, BAMLH0A0HYM2", "", "A",
            ))
        else:
            ev.append(Evidence(
                RISK, "NONE", 0,
                f"rezim {regime}, ale par s akciemi nekoreluje ({view.equity_corr:+.2f}) - bez vlivu",
                "INTERPRETATION", "VIXCLS, SP500", "", "A", "CONTEXT",
            ))
    elif regime == "UNKNOWN":
        view.data_gaps.append("rizikovy rezim NEOVERENO (chybi VIX)")

    # ------------------------------------------------------------ commodity link (CAD)
    if "CAD" in (instrument.base, instrument.quote) and i >= 2:
        wti = load_series("GLOBAL.WTI").history(t, p.risk_beta_days + 20)
        corr = _corr_cached(d1, i, "GLOBAL.WTI", t, p)

        if corr is not None and abs(corr) >= p.risk_beta_min_corr and len(wti) >= 21:
            oil_change = wti[-1].value / wti[-21].value - 1.0
            window = [o.value for o in wti[-80:]]
            changes = [window[k] / window[k - 20] - 1.0 for k in range(20, len(window))]
            sd = math.sqrt(sum(c * c for c in changes) / len(changes)) if changes else 0.0

            if sd > 0 and abs(oil_change) >= sd:
                direction = "BUY" if corr * oil_change > 0 else "SELL"
                ev.append(Evidence(
                    COMMODITY, direction, 1,
                    f"ropa WTI {oil_change * 100:+.1f} % za 20 dni; par koreluje s ropou {corr:+.2f}",
                    "INTERPRETATION", "DCOILWTICO", str(wti[-1].obs_date), "A",
                ))

    # ------------------------------------------------------------ intervention context (JPY)
    if "JPY" in (instrument.base, instrument.quote) and i >= 21:
        move = d1.close[i] / d1.close[i - 20] - 1.0
        jpy_weakening = move > 0 if instrument.quote == "JPY" else move < 0
        rets = [d1.close[j] / d1.close[j - 1] - 1.0 for j in range(max(1, i - 119), i + 1)]
        sd = math.sqrt(sum(r * r for r in rets) / len(rets)) * math.sqrt(20) if rets else 0.0

        if jpy_weakening and sd > 0 and abs(move) >= 2.0 * sd:
            ev.append(Evidence(
                INTERVENTION, "SELL" if instrument.quote == "JPY" else "BUY", 1,
                f"JPY oslabil o {abs(move) * 100:.1f} % za 20 dni ({abs(move) / sd:.1f} sigma) - riziko verbalni/"
                f"skutecne intervence (NEOVERENO, jen cenovy kontext)",
                "HYPOTHESIS", "cena", "", "C", "COUNTERFORCE",
            ))

    # ------------------------------------------------------------ events
    if events is not None:
        view.events_pre = events.get("pre", [])
        view.events_post = events.get("post", [])

        for event in view.events_pre:
            hours = (event.scheduled_at - t) / 3600
            ev.append(Evidence(
                EVENT, "NONE", 0,
                f"za {hours:.1f} h: {event.currency} {event.title} (dopad {event.impact}"
                + (f", odhad {event.forecast}, minule {event.previous}" if event.forecast else "") + ")",
                "OBSERVATION", "ekonomicky kalendar", "", "B", "GATE",
            ))

        for event in view.events_post:
            minutes = (t - event.scheduled_at) / 60
            ev.append(Evidence(
                EVENT, "NONE", 0,
                f"pred {minutes:.0f} min: {event.currency} {event.title} - faze IMMEDIATE-POST",
                "OBSERVATION", "ekonomicky kalendar", "", "B", "GATE",
            ))

    if not event_layer_available:
        view.event_layer = "NOT_AVAILABLE"
        view.data_gaps.append("kalendar udalosti pro tento cas neni k dispozici - event gate NEOVEREN")

    if view.data_gaps:
        ev.append(Evidence(DATA, "NONE", 0, "; ".join(view.data_gaps), "OBSERVATION", "", "", quality, "CONTEXT"))

    return view
