"""Decision layer: evidence matrix -> hypotheses -> gates -> setup (modules
34-37, 45-59, 64).

Order of precedence (module 1): data integrity -> direction (causal +
market structure) -> entry location -> execution/cost -> risk. A hard gate
can never be outvoted by a strong score (module 50: HARD GATES +
SUPPORTING EVIDENCE + COUNTEREVIDENCE, no magic number).

Direction (module 45) needs the technical structure (the market is the
final observed result, module 38) and must not be contradicted by the
fundamental evidence; confidence is a CLASS of evidence (A/B/C, module 16
and 72), not a probability:

    A   technical direction + >= 2 independent fundamental clusters agree,
        no fundamental cluster against, no unresolved counterforce
    B   technical direction + >= 1 fundamental cluster agrees, none against
    C   technical direction only, or with an unresolved counterforce
        -> never NOW (module 37: unresolved counter-argument -> WAIT)

Entry (modules 46, 52): PULLBACK to an active level, BREAKOUT_RETEST of a
broken level, or CONTINUATION at the H1 EMA20 zone. SL beyond the level
(module 53), TP1 before the opposing level or capped by ATR (module 54),
R:R measured against TP1 AFTER costs (module 55, 64).

All levels are MODEL-PRICE (mid). Costs are the KNOWN-COST-ADJUSTED layer:
the round-trip spread observed at the decision plus assumed slippage.
Outcomes are checked side-correct against BID/ASK where available
(src/engine/resolution.py).
"""

import math
from dataclasses import dataclass, field

from src.engine import evidence as E
from src.engine.evidence import Evidence, cluster_votes, opposite
from src.engine.fundamental import FundamentalView
from src.engine.params import ModelParams
from src.engine.regime import RegimeView
from src.engine.series import PriceSeries
from src.engine.technical import TechLevel, TechnicalView, recent_move_atr
from src.instruments import get_instrument

DECISIONS = ("BUY NOW", "SELL NOW", "WAIT FOR BUY", "WAIT FOR SELL", "NO TRADE")
CONFIDENCE_RANK = {"A": 0, "B": 1, "C": 2}
USABLE_LEVEL_STATES = ("FRESH", "ACTIVE")


@dataclass
class Gate:
    name: str
    status: str        # PASS / FAIL / CONDITIONAL / N/A
    reason: str


@dataclass
class Candidate:
    symbol: str
    t: int
    decision: str
    direction: str                     # BUY / SELL / NONE
    thesis_direction: str = "NONE"     # direction bias even when no trade (module 45)
    setup_type: str | None = None
    entry: float | None = None
    zone_low: float | None = None
    zone_high: float | None = None
    stop: float | None = None
    targets: list = field(default_factory=list)
    rr_gross: float | None = None
    rr_net: float | None = None
    cost_price: float | None = None
    spread_price: float | None = None
    confidence: str | None = None
    clusters_for: list = field(default_factory=list)
    clusters_against: list = field(default_factory=list)
    evidence_for: list = field(default_factory=list)
    evidence_against: list = field(default_factory=list)
    counterforces: list = field(default_factory=list)
    hypotheses: dict = field(default_factory=dict)
    invalidation: str | None = None
    gates: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    risk_pct: float | None = None
    regime: str | None = None
    event_cluster: str | None = None
    scenarios: dict = field(default_factory=dict)
    price: float | None = None
    atr_h1: float | None = None
    level: TechLevel | None = None

    @property
    def actionable(self) -> bool:
        return self.decision != "NO TRADE"

    @property
    def is_now(self) -> bool:
        return self.decision.endswith("NOW")

    def gate(self, name: str) -> Gate | None:
        return next((g for g in self.gates if g.name == name), None)

    def failed_gates(self) -> list[Gate]:
        return [g for g in self.gates if g.status == "FAIL"]

    def exposure(self) -> dict[str, int]:
        """Currency exposure of the trade: +1 long, -1 short (module 58)."""
        if self.direction == "NONE":
            return {}

        instrument = get_instrument(self.symbol)
        sign = 1 if self.direction == "BUY" else -1
        return {instrument.base: sign, instrument.quote: -sign}


def _no_trade(candidate: Candidate, reason: str) -> Candidate:
    candidate.decision = "NO TRADE"
    candidate.direction = "NONE"
    candidate.reasons.insert(0, reason)
    return candidate


def _pick_level(levels: list[TechLevel], price: float, direction: str, reach: float) -> TechLevel | None:
    """Nearest usable level on the own side (support for BUY, resistance for
    SELL), including broken opposite-side levels (retest, polarity flip)."""
    sign = 1 if direction == "BUY" else -1
    usable = []

    for level in levels:
        distance = sign * (price - level.price)

        if distance < 0 or distance > reach:
            continue

        if level.state in USABLE_LEVEL_STATES:
            usable.append(level)
        elif level.state == "BROKEN" and level.broken_recently:
            # broken resistance now below price (BUY) = retest candidate
            if (direction == "BUY" and level.source == "H") or (direction == "SELL" and level.source == "L"):
                usable.append(level)

    usable.sort(key=lambda l: abs(price - l.price))
    return usable[0] if usable else None


def hypotheses(direction: str, votes: dict, items: list[Evidence], tech: TechnicalView,
               regime: RegimeView) -> dict:
    """H1 dominant mechanism, H2 alternative, H3 strongest counterforce (module 37)."""
    supporting = [e for e in items if e.role == "DIRECTION" and e.direction == direction and e.weight > 0]
    supporting.sort(key=lambda e: (-e.weight, e.cluster != E.RATES_REPRICING))
    against = [e for e in items if e.direction == opposite(direction) and e.weight > 0]
    against.sort(key=lambda e: (-e.weight, e.role != "COUNTERFORCE"))

    if supporting:
        h1 = f"{supporting[0].cluster}: {supporting[0].text}"
    else:
        h1 = "cenova struktura bez fundamentalniho ridiciho faktoru (technicke pokracovani)"

    if regime.structure == "RANGE":
        h2 = "trh je v rezimu RANGE - pohyb se muze vratit do stredu pasma (mean reversion)"
    elif tech.momentum_z is not None and abs(tech.momentum_z) >= 2.0:
        h2 = f"trend je natazeny (momentum {tech.momentum_z:+.1f} sigma) - mozna korekce pred pokracovanim"
    else:
        h2 = "pohyb je jen hluk uvnitr sirsiho pasma; uroven nemusi vydrzet"

    if against:
        h3 = f"{against[0].cluster}: {against[0].text}"
    elif regime.transition:
        h3 = "znaky zmeny rezimu (" + "; ".join(regime.notes) + ")"
    else:
        h3 = "nenalezena materialni fundamentalni protisila; hlavni riziko = selhani urovne"

    return {"H1": h1, "H2": h2, "H3": h3}


def decide(
    symbol: str,
    t: int,
    tech: TechnicalView,
    fund: FundamentalView,
    regime: RegimeView,
    h1: PriceSeries,
    p: ModelParams,
    data_state: str,
    spread_price: float | None,
    live_quote_ok: bool = True,
) -> Candidate:
    instrument = get_instrument(symbol)
    candidate = Candidate(symbol=symbol, t=t, decision="NO TRADE", direction="NONE",
                          price=tech.price, regime=regime.label)

    # ------------------------------------------------------------ data gates
    data_ok = data_state == "CURRENT"
    candidate.gates.append(Gate("DATA_STATE", "PASS" if data_ok else "FAIL", f"stav dat {data_state}"))

    if not tech.complete:
        return _no_trade(candidate, "nedostatek historie pro D1/H4/H1 analyzu")

    i1 = h1.index_at(t)
    a = tech.h1.atr
    candidate.atr_h1 = a

    # ------------------------------------------------------------ evidence matrix
    items: list[Evidence] = [Evidence(E.PRICE_TREND, d, 1 if d in ("BUY", "SELL") else 0, text,
                                      "DERIVED METRIC", "D1/H4 mid", "", "A",
                                      "DIRECTION" if d in ("BUY", "SELL") else "CONTEXT")
                             for text, d in tech.evidence]
    items += fund.evidence
    votes = cluster_votes(items)
    fundamental_votes = {c: v for c, v in votes.items() if c in E.FUNDAMENTAL_CLUSTERS}
    fund_buy = [c for c, v in fundamental_votes.items() if v == "BUY"]
    fund_sell = [c for c, v in fundamental_votes.items() if v == "SELL"]

    # thesis direction (can exist without a trade, module 45)
    if tech.bias != "NONE":
        candidate.thesis_direction = tech.bias
    elif len(fund_buy) >= 2 and not fund_sell:
        candidate.thesis_direction = "BUY"
    elif len(fund_sell) >= 2 and not fund_buy:
        candidate.thesis_direction = "SELL"

    if tech.bias == "NONE":
        note = tech.notes[0] if tech.notes else "technicky smer neurcen"
        if candidate.thesis_direction != "NONE":
            note += f"; fundamenty naznacuji {candidate.thesis_direction}, ale cena to nepotvrzuje (smer != vstup)"
        return _no_trade(candidate, note)

    direction = tech.bias
    sign = 1.0 if direction == "BUY" else -1.0
    clusters_for = [E.PRICE_TREND] + (fund_buy if direction == "BUY" else fund_sell)
    clusters_against = fund_sell if direction == "BUY" else fund_buy
    counterforces = [e for e in items if e.role == "COUNTERFORCE" and e.direction == opposite(direction)]
    candidate.clusters_for, candidate.clusters_against = clusters_for, clusters_against
    candidate.evidence_for = [e for e in items if e.direction == direction and e.weight > 0]
    candidate.evidence_against = [e for e in items if e.direction == opposite(direction) and e.weight > 0]
    candidate.counterforces = counterforces
    candidate.hypotheses = hypotheses(direction, votes, items, tech, regime)

    if len(clusters_against) > len(clusters_for) - 1:
        # more fundamental clusters against than in favour: the mechanism
        # contradicts the price structure -> no trade (module 37)
        candidate.thesis_direction = direction
        return _no_trade(
            candidate,
            f"technicky {direction}, ale fundamenty proti ({', '.join(clusters_against)}) - nevyresena protisila",
        )

    fundamental_for = len(clusters_for) - 1

    if fundamental_for >= p.min_clusters_a - 1 and not clusters_against and not counterforces:
        confidence = "A"
    elif fundamental_for >= p.min_clusters_b - 1 and not clusters_against:
        confidence = "B"
    else:
        confidence = "C"

    candidate.confidence = confidence

    # ------------------------------------------------------------ entry location
    reach = p.max_level_distance_atr * a
    levels = (tech.h1.levels if tech.h1 else []) + (tech.h4.levels if tech.h4 else [])
    price = tech.price
    level = _pick_level(levels, price, direction, reach)

    if level is not None:
        setup_type = "BREAKOUT_RETEST" if level.state == "BROKEN" else "PULLBACK"
        anchor = level.price
        stop = level.price - sign * p.stop_buffer_atr * a
    else:
        # continuation at the H1 EMA20 zone, SL beyond the last H1 swing
        ema20 = tech.h1.ema20
        if sign * (price - ema20) < 0:
            return _no_trade(candidate, "cena je pod/nad H1 EMA20 proti smeru a zadna uroven v dosahu")
        pivots = h1.pivots_known_at(i1, 60)
        swing = [pv[2] for pv in pivots if pv[3] == ("L" if direction == "BUY" else "H")]
        if not swing:
            return _no_trade(candidate, "zadna struktura pro SL (chybi swing)")
        anchor = ema20
        stop = swing[-1] - sign * p.stop_buffer_atr * a
        setup_type = "CONTINUATION"
        if sign * (anchor - stop) <= 0.3 * a:
            return _no_trade(candidate, "SL by byl prilis tesny vuci EMA20 zone")

    candidate.setup_type = setup_type
    candidate.level = level
    distance = sign * (price - anchor)
    move = recent_move_atr(h1, i1, price, p.no_chase_bars, direction)
    near = 0.0 <= distance <= p.near_level_atr * a

    if near:
        entry = price
        zone_a, zone_b = anchor, price
        now_possible = True
    else:
        entry = anchor + sign * p.entry_offset_atr * a
        zone_a, zone_b = anchor, anchor + sign * 2 * p.entry_offset_atr * a
        now_possible = False

    risk = sign * (entry - stop)

    if risk <= 0:
        return _no_trade(candidate, "neplatna vzdalenost SL")

    # ------------------------------------------------------------ targets (module 54)
    other_side = [l for l in levels if l.state in ("FRESH", "ACTIVE", "WEAKENED")
                  and sign * (l.price - entry) > 0]
    other_side.sort(key=lambda l: sign * (l.price - entry))
    cap = entry + sign * p.max_tp1_atr * a

    if other_side:
        structural = other_side[0].price - sign * p.target_buffer_atr * a
        tp1 = min(structural, cap) if direction == "BUY" else max(structural, cap)
        tp1_source = "struktura" if tp1 == structural else "ATR"
    else:
        tp1 = entry + sign * min(p.max_tp1_atr * a, max(2.0 * risk, 1.5 * a))
        tp1_source = "ATR"

    targets = [tp1]

    for multiple in (2.5, 3.5):
        previous = targets[-1]
        fallback = entry + sign * max(multiple * risk, sign * (previous - entry) + 0.5 * risk)
        beyond = [l.price - sign * p.target_buffer_atr * a for l in other_side[1:]
                  if sign * ((l.price - sign * p.target_buffer_atr * a) - previous) >= 0.5 * risk]
        candidate_tp = beyond[0] if beyond else fallback
        targets.append(candidate_tp if sign * (candidate_tp - previous) > 0 else fallback)

    # ------------------------------------------------------------ costs and R:R (modules 55, 64)
    slip = p.slippage_pips * instrument.pip
    spread = spread_price if spread_price is not None else 0.0
    # observed (ECN) spread + broker markup + slippage on both sides
    cost = spread + p.broker_markup_pips * instrument.pip + 2 * slip
    reward = sign * (tp1 - entry)
    rr_gross = reward / risk
    rr_net = (reward - cost) / (risk + cost)
    candidate.entry, candidate.stop, candidate.targets = entry, stop, targets
    candidate.zone_low, candidate.zone_high = min(zone_a, zone_b), max(zone_a, zone_b)
    candidate.rr_gross, candidate.rr_net = rr_gross, rr_net
    candidate.cost_price, candidate.spread_price = cost, spread_price
    candidate.direction = direction
    candidate.reasons.append(
        f"{setup_type}: {'uroven' if level else 'EMA20 H1'} {instrument.fmt(anchor)}"
        + (f" ({level.timeframe}, {level.touches}x, {level.state})" if level else "")
        + f", R:R {rr_net:.2f} po nakladech (TP1 z {tp1_source})"
    )

    rr_ok = rr_net >= p.min_rr - 1e-9
    candidate.gates.append(Gate("RR", "PASS" if rr_ok else "FAIL",
                                f"R:R {rr_net:.2f} po nakladech (min {p.min_rr})"))

    if not rr_ok:
        shown = math.floor(rr_net * 100) / 100
        candidate.thesis_direction = direction
        return _no_trade(candidate, f"R:R {shown:.2f} po nakladech pod hranici {p.min_rr} (TP1 z {tp1_source})")

    # ------------------------------------------------------------ NOW gates (module 51)
    now_gates = []
    now_gates.append(Gate("LOCATION", "PASS" if now_possible else "FAIL",
                          "cena u urovne" if now_possible else f"cena {distance / a:.1f} ATR od urovne - cekat na vstup"))
    chase = move >= p.no_chase_atr
    now_gates.append(Gate("NO_CHASE", "FAIL" if chase else "PASS",
                          f"pohyb {move:.1f} ATR za {p.no_chase_bars} h" + (" - zakaz NOW (module 48)" if chase else "")))
    shock_recent = any(h1.shock[j] for j in range(max(0, i1 - 2), i1 + 1))
    now_gates.append(Gate("SHOCK", "FAIL" if shock_recent else "PASS",
                          "sokova svicka v poslednich 3 h - cekat na stabilizaci" if shock_recent else "bez soku"))

    if fund.event_layer == "ABLATED":
        now_gates.append(Gate("EVENT", "N/A", "event vrstva vypnuta (backtest bez historickeho kalendare)"))
    elif fund.event_layer == "NOT_AVAILABLE":
        now_gates.append(Gate("EVENT", "CONDITIONAL", "kalendar neni k dispozici - event riziko NEOVERENO"))
    elif fund.events_pre or fund.events_post:
        names = ", ".join(f"{e.currency} {e.title}" for e in (fund.events_pre + fund.events_post)[:3])
        now_gates.append(Gate("EVENT", "FAIL", f"udalost s vysokym dopadem: {names}"))
    else:
        now_gates.append(Gate("EVENT", "PASS", "zadna udalost s vysokym dopadem v okne"))

    if spread_price is None:
        now_gates.append(Gate("SPREAD", "CONDITIONAL", "spread neznamy (jen MODEL-PRICE)"))
    elif spread_price > p.max_spread_atr * a:
        now_gates.append(Gate("SPREAD", "FAIL", f"spread {instrument.pips(spread_price):.1f} pip > {p.max_spread_atr} ATR"))
    else:
        now_gates.append(Gate("SPREAD", "PASS", f"spread {instrument.pips(spread_price):.1f} pip"))

    now_gates.append(Gate("CONFIDENCE", "PASS" if confidence in ("A", "B") else "FAIL",
                          f"trida dukazu {confidence}"))

    if p.require_fundamental_for_now:
        now_gates.append(Gate("FUNDAMENTAL", "PASS" if fundamental_for >= 1 else "FAIL",
                              f"{fundamental_for} fundamentalni klastr(y) ve smeru"))

    now_gates.append(Gate("LIVE_QUOTE", "PASS" if (live_quote_ok and data_ok) else "FAIL",
                          "aktualni kotace overena" if (live_quote_ok and data_ok) else "LIVE CENA NEOVERENA"))
    now_gates.append(Gate("REGIME", "FAIL" if regime.transition else "PASS",
                          "zmena rezimu - vyssi dukazni bremeno" if regime.transition else regime.label))
    candidate.gates.extend(now_gates)

    now_ok = all(g.status in ("PASS", "N/A") for g in now_gates)

    if now_ok:
        candidate.decision = f"{direction} NOW"
    else:
        candidate.decision = f"WAIT FOR {direction}"

        if now_possible:
            # at the level but a gate blocks NOW: wait for a better entry
            # (the pullback zone) instead of chasing
            blocked = [g for g in now_gates if g.status not in ("PASS", "N/A")]
            candidate.reasons.append("NOW blokovano: " + "; ".join(g.reason for g in blocked[:3]))
            # the waiting entry must lie on the favourable side of the
            # current price, otherwise the limit would fill at once (= NOW)
            if sign * (price - anchor) <= 0.1 * a:
                return _no_trade(candidate, "cena je primo na urovni a NOW je blokovano - bez cekaciho vstupu")

            candidate.entry = anchor + sign * min(p.entry_offset_atr * a * 0.5, 0.5 * sign * (price - anchor))
            candidate.zone_low = min(anchor, candidate.entry)
            candidate.zone_high = max(anchor, candidate.entry)
            risk = sign * (candidate.entry - stop)
            reward = sign * (tp1 - candidate.entry)

            if risk <= 0 or reward <= 0:
                return _no_trade(candidate, "po posunu vstupu neni platna geometrie obchodu")

            candidate.rr_gross = reward / risk
            candidate.rr_net = (reward - cost) / (risk + cost)

            if candidate.rr_net < p.min_rr - 1e-9:
                return _no_trade(candidate, f"cekaci vstup: R:R {candidate.rr_net:.2f} pod {p.min_rr}")

    # ------------------------------------------------------------ invalidation, risk, scenarios
    candidate.invalidation = (
        f"obchod prestava platit pri uzavreni H1 {'pod' if direction == 'BUY' else 'nad'} "
        f"{instrument.fmt(stop)}"
        + (", nebo kdyz se sazbovy diferencial otoci o vice nez 15 bp proti smeru"
           if E.RATES_REPRICING in clusters_for else "")
        + ", nebo po udalosti s vysokym dopadem, ktera zmeni ridici mechanismus"
    )

    risk_pct = p.risk_pct_standard

    if fund.events_pre or confidence == "C" or regime.volatility in ("HIGH", "EXTREME"):
        risk_pct = p.risk_pct_event

    candidate.risk_pct = risk_pct
    candidate.scenarios = {
        "BASE": f"{direction} k TP1 {instrument.fmt(tp1)} do {p.horizon_hours} h",
        "ALT": f"cena se vrati k urovni a obchod zustane bez vstupu / expiruje",
        "BEAR" if direction == "BUY" else "BULL": f"pruraz {instrument.fmt(stop)} = teze neplati",
    }
    return candidate
