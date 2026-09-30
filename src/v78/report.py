"""Czech user output of a run (modules 7, 84, 85, 113, 128/15, 135, 141).

The visible output may be short, but it never hides a critical gate
(module 7, 84): blocked gates, data states and the certificates are always
printed. Prices are printed directly (module 135); when no verified live
quote exists the line says LIVE CENA NEOVERENA. Lines stay <= 100
characters (Termux screen). No diacritics, like the rest of the project.
"""

from datetime import datetime, timezone

from src.engine.portfolio import position_size
from src.instruments import get_instrument

UTC = timezone.utc
DECISION_CZ = {
    "BUY NOW": "KOUPIT TED",
    "SELL NOW": "PRODAT TED",
    "WAIT FOR BUY": "CEKAT NA NAKUP",
    "WAIT FOR SELL": "CEKAT NA PRODEJ",
    "NO TRADE": "NEOBCHODOVAT",
}
EXECUTION_CZ = {
    "EXECUTABLE": "EXEKUCNI",
    "MODEL-PRICE": "model-cena",
    "BROKER-BLOCKED": "BROKER-BLOK",
    "DATA-BLOCKED": "DATA-BLOK",
}
SOURCE_SHORT = {
    "TWELVE_DATA": "12data",
    "DUKASCOPY_TICK": "duka-tick",
    "DUKASCOPY_M1": "duka-m1",
    "OANDA": "oanda",
}
LINE = "=" * 78
THIN = "-" * 78


def _t(ts) -> str:
    if ts is None:
        return "-"
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, tz=UTC)
    return ts.astimezone(UTC).strftime("%m-%d %H:%M:%S")


def _age(seconds) -> str:
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 120:
        return f"{seconds}s"
    if seconds < 7200:
        return f"{seconds // 60}m"
    if seconds < 172800:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def price_table(snapshot) -> list[str]:
    out = [f"CENY (T0 snapshot {snapshot.t0.astimezone(UTC):%Y-%m-%d}, cas zdroje UTC, modul 135)",
           "par      bid        ask        mid        zdroj     cas     stari stav        exekuce"]
    now_ts = snapshot.t0.timestamp()

    for symbol, quote in snapshot.pairs.items():
        instrument = get_instrument(symbol)
        c = quote.canonical

        if c is None:
            out.append(f"{symbol:<8} LIVE CENA NEOVERENA - zadny platny zdroj ({quote.data_state})")
            continue

        bid = instrument.fmt(c.bid) if c.bid is not None else "-"
        ask = instrument.fmt(c.ask) if c.ask is not None else "-"
        state = {"LAST_VALID_SESSION": "POSL.REL"}.get(quote.data_state, quote.data_state)
        source = SOURCE_SHORT.get(c.source_id, c.source_id.lower()[:9])
        clock = datetime.fromtimestamp(c.source_ts, tz=UTC).strftime("%H:%M") if c.source_ts else "-"
        out.append(
            f"{symbol:<8} {bid:<10} {ask:<10} {instrument.fmt(c.mid):<10} {source:<9} {clock:<7} "
            f"{_age(c.age(now_ts)):>5} {state[:11]:<11} {EXECUTION_CZ.get(quote.execution, quote.execution)}"
        )

        if quote.data_state not in ("LIVE", "FRESH"):
            out.append(f"         LIVE CENA NEOVERENA: {'; '.join(quote.notes)[:66]}")

        if quote.spread_reference is not None:
            out.append(f"         spread ref. {instrument.pips(quote.spread_reference):.1f} pip ({quote.spread_source})")

    out.append(f"trh: {snapshot.market} | skew mezi pary: "
               f"{'-' if snapshot.max_skew_s is None else f'{snapshot.max_skew_s:.0f} s'} ({snapshot.skew_state})")

    for symbol, check in snapshot.consistency.items():
        if check and check["state"] != "CONSISTENT":
            out.append(f"POZOR {symbol}: zdroje se lisi (median {check['median_pips']} pip, p95 {check['p95_pips']} pip)"
                       f" - SOURCE_DRIFT")

    return out


def candidate_block(rank: int, c, thesis, p, balance: float) -> list[str]:
    instrument = get_instrument(c.symbol)
    f = instrument.fmt
    lines = [f"#{rank} {c.symbol}: {DECISION_CZ[c.decision]} ({c.setup_type}) | duvera {c.confidence}"
             f" | R:R {c.rr_net:.2f} po nakladech"]
    lines.append(f"   ref. cena {f(c.price)} | vstup {f(c.entry)} (zona {f(c.zone_low)}-{f(c.zone_high)})"
                 f" | SL {f(c.stop)}")
    lines.append("   TP1 " + f(c.targets[0]) + " / TP2 " + f(c.targets[1]) + " / TP3 " + f(c.targets[2])
                 + f" | horizont {p.horizon_hours} h | riziko {c.risk_pct}% uctu")

    if c.entry is not None and c.stop is not None:
        size = position_size(balance, c.risk_pct or 0.5, c.entry, c.stop, instrument.pip)
        lines.append(f"   SL {size.get('stop_pips', 0):.1f} pip; pri uctu {balance:.0f} = ~{size['units']:.0f} jednotek "
                     f"(odhad, over u brokera)")

    lines.append(f"   H1 teze: {c.hypotheses.get('H1', '-')[:70]}")
    lines.append(f"   H2 alt.: {c.hypotheses.get('H2', '-')[:70]}")
    lines.append(f"   H3 proti: {c.hypotheses.get('H3', '-')[:69]}")

    if c.evidence_for:
        lines.append("   PRO: " + " | ".join(e.cluster for e in c.evidence_for)[:70])

    if c.evidence_against or c.counterforces:
        items = {e.cluster for e in c.evidence_against} | {e.cluster for e in c.counterforces}
        lines.append("   PROTI: " + ", ".join(sorted(items)))

    lines.append(f"   invalidace: {c.invalidation[:68]}")

    if len(c.invalidation) > 68:
        lines.append(f"               {c.invalidation[68:136]}")

    blocked = [g for g in c.gates if g.status not in ("PASS", "N/A")]

    if blocked:
        lines.append("   brany: " + "; ".join(f"{g.name}={g.status}" for g in blocked)[:69])

    if thesis is not None:
        lines.append(f"   teze: {thesis.state} od {_t(thesis.t0)} | smer {thesis.direction} | {thesis.last_reason[:40]}")

    return lines


def dashboard(stats: dict) -> list[str]:
    out = ["DASHBOARD (evidence predikci, modul 84)"]
    live = stats.get("live")

    if live is None or live.predictions == 0:
        out.append("  zatim zadne uzavrene predikce v evidenci")
        return out

    out.append(f"  predikci {live.predictions} | se vstupem {live.triggered} | binarne uzavreno {live.binary}"
               f" | bez vstupu {live.not_activated}")

    if live.direction_accuracy is not None:
        out.append(f"  PRESNOST SMERU {live.direction_accuracy * 100:.0f}% (n={live.direction_n})")

    if live.win_rate is not None:
        low, high = live.win_ci
        out.append(f"  WIN RATE {live.win_rate * 100:.0f}% (95% IS {low * 100:.0f}-{high * 100:.0f}%)"
                   f" | E {live.expectancy:+.2f}R | PF {live.profit_factor or 0:.2f}")

    out.append(f"  poradi neznamo {live.sequence_unknown} | nerozhodnuto (diry) {live.unresolved}")
    out.append(f"  vzorek: {live.sample}")
    return out


ADVERSARIAL = (
    ("missing path segment", "coverage"),
    ("source drift", "drift"),
    ("bar-completion error", "open_bar"),
    ("timezone mismatch", "timezone"),
    ("hidden spread", "spread"),
    ("session gap", "session"),
    ("sequence ambiguity", "sequence"),
    ("artifact write failure", "write"),
    ("read-back failure", "readback"),
    ("wrong previous T0", "previous_t0"),
    ("wrong model version", "model"),
    ("module omission", "trace"),
    ("silent fallback to stale values", "stale"),
)


def adversarial_lines(flags: dict) -> list[str]:
    out = ["CO MODEL PREHLEDL? (modul 85)"]

    for label, key in ADVERSARIAL:
        value = flags.get(key)
        mark = "ANO" if value else "ne"
        detail = f" - {value}" if isinstance(value, str) else ""
        out.append(f"  {label:<32} {mark}{detail}"[:78])

    return out


def certificate_lines(cert: dict, pipeline: dict) -> list[str]:
    out = [LINE, f"RUN COMPLETION CERTIFICATE: {cert['status']}", THIN]

    for key in ("model_version", "implementation", "run_id", "t0", "previous_run_id", "previous_t0",
                "module_trace", "archive", "path_coverage", "gap_counts", "quote_freshness",
                "predictions_locked", "persistence_read_back", "broker_verification"):
        value = cert.get(key)
        out.append(f"  {key:<24} {value}"[:78])

    out += [THIN, f"DATA PIPELINE CERTIFICATE: {pipeline['status']}"]

    for key in ("source_capability", "quote_freshness", "atomic_skew", "path_coverage", "unresolved_gaps",
                "source_consistency", "broker_verification"):
        out.append(f"  {key:<24} {pipeline.get(key)}"[:78])

    out.append(LINE)
    return out


def mechanism_lines(ctx: dict) -> list[str]:
    """Main causal mechanism (module 7, 34): currency scoreboard from the
    point-in-time fundamentals + the global risk regime."""
    from src.engine.fundamental import currency_state, risk_regime
    from src.instruments import CURRENCIES

    t = int(ctx["run"].t0.timestamp())
    p = ctx["params"]
    regime, notes = risk_regime(t, p)
    out = ["HLAVNI MECHANISMUS (sazby, politika, pozicovani; modul 7/34)",
           f"  rizikovy rezim: {regime} ({'; '.join(notes)})"[:78]]
    rows = []

    for currency in CURRENCIES:
        state = currency_state(currency, t, p)

        if state.short_rate is None or state.short_rate_past is None:
            continue

        change = (state.short_rate - state.short_rate_past) * 100
        policy = ""

        if state.policy is not None and state.policy_6m_ago is not None:
            diff = state.policy - state.policy_6m_ago
            policy = "zvysuje" if diff >= 0.2 else "snizuje" if diff <= -0.2 else "drzi"

        cot = f" | COT z {state.cot_z:+.1f}" if state.cot_z is not None else ""
        rows.append((change, f"  {currency}: kratka sazba {state.short_rate:.2f}% ({change:+.0f} bp/20d)"
                             f" | politika {state.policy if state.policy is not None else '-'}% {policy}{cot}"))

    rows.sort(key=lambda r: -r[0])
    out += [line[:78] for _, line in rows]

    if rows:
        out.append(f"  nejvic precenovana nahoru: {rows[0][1].split(':')[0].strip()} | "
                   f"dolu: {rows[-1][1].split(':')[0].strip()}")

    return out


def catalyst_lines(ctx: dict) -> list[str]:
    """Calendar of high-impact catalysts for 24 h / 3 d / 7 d (module 47, 59)."""
    from src.fundamental.calendar import calendar_coverage, events_between

    t = int(ctx["run"].t0.timestamp())
    out = ["KATALYZATORY (vysoky dopad, modul 47)"]
    _, last_seen = calendar_coverage()
    shown = 0

    for label, hours in (("24 h", 24), ("3 d", 72), ("7 d", 168)):
        events = events_between(t, t + hours * 3600, None, "High")
        previous = events_between(t, t + {24: 0, 72: 24, 168: 72}[hours] * 3600, None, "High") if hours > 24 else []
        new = [e for e in events if e not in previous]

        for e in new[:8]:
            forecast = f" (odhad {e.forecast}, minule {e.previous})" if e.forecast else ""
            out.append(f"  [{label}] {e.time:%a %d.%m %H:%M} {e.currency} {e.title}{forecast}"[:78])
            shown += 1

    if not shown:
        out.append("  zadna udalost s vysokym dopadem v dostupnem kalendari")

    out.append("  14 d: NEOVERENO (volny kalendar pokryva jen aktualni tyden)")
    return out


def summary_lines(ctx: dict) -> list[str]:
    """Short summary for the phone screen; details and all gates follow."""
    states = [q.data_state for q in ctx["snapshot"].pairs.values()]
    fresh = sum(1 for s in states if s in ("LIVE", "FRESH"))
    out = [f"SHRNUTI: certifikat {ctx['certificate']['status']} | ceny LIVE/FRESH {fresh}/{len(states)}"
           f" | trh {ctx['snapshot'].market}"]
    top = ctx["selection"].top

    if not top:
        out.append("  Top-3: zadny obchod (NEOBCHODOVAT)")

    for rank, c in enumerate(top, 1):
        instrument = get_instrument(c.symbol)
        out.append(f"  {rank}. {c.symbol} {DECISION_CZ[c.decision]} vstup {instrument.fmt(c.entry)} "
                   f"SL {instrument.fmt(c.stop)} TP1 {instrument.fmt(c.targets[0])} R:R {c.rr_net:.1f} ({c.confidence})"[:78])

    closed = [i for i in ctx["audit"] if i.outcome_state and i.outcome_state != "UNRESOLVED"]

    if closed:
        out.append(f"  vyhodnoceno tento beh: {len(closed)} predikci")

    if ctx.get("theses"):
        out.append(f"  otevrene teze: {', '.join(f'{s} {t.direction}' for s, t in ctx['theses'].items())}"[:78])

    return out


def render(ctx: dict) -> str:
    run = ctx["run"]
    p = ctx["params"]
    out = [LINE, f"FXBOT {ctx['model_version']} ({ctx['implementation']}) - BEH {run.run_id}", LINE]
    out.append(f"T0 {run.t0.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC | predchozi oficialni T0: "
               f"{run.previous_t0.astimezone(UTC).strftime('%Y-%m-%d %H:%M') if run.previous_t0 else 'zadny (prvni beh)'}")
    out.append(f"model: {ctx['model_load']}")
    out.append(f"parametry {p.fingerprint} | registr zdroju {ctx['register_version']}")

    out += [THIN] + summary_lines(ctx)

    if ctx.get("blocked_critical"):
        out.append(THIN)
        out.append("KRITICKE BLOKACE:")
        out += [f"  ! {line}"[:78] for line in ctx["blocked_critical"]]

    out += [THIN] + price_table(ctx["snapshot"])
    out += [THIN, "DATA A CESTA (pokryti od predchoziho T0, modul 123)"]

    for symbol, cov in ctx["coverage"].items():
        critical = sum(1 for g in cov.gaps if g.severity == "CRITICAL")
        layers = ", ".join(f"{k.replace('DUKASCOPY_', 'D.')}:{v}" for k, v in sorted(cov.layers.items()))
        out.append(f"  {symbol:<8} {cov.state:<10} {cov.ratio * 100:5.1f}% | max mezera {cov.max_gap_minutes} min"
                   f"{' | KRITICKE ' + str(critical) if critical else ''} | {layers}"[:78])

    try:
        out += [THIN] + mechanism_lines(ctx)
        out += [THIN] + catalyst_lines(ctx)
    except Exception as exc:              # a report section never blocks the run
        out += [THIN, f"HLAVNI MECHANISMUS: nelze sestavit ({type(exc).__name__})"]

    out += [THIN, "AUDIT SPLATNYCH PREDIKCI (modul 81)"]

    if not ctx["audit"]:
        out.append("  zadne otevrene predikce")

    for item in ctx["audit"]:
        r = f"{item.r_net:+.2f}R" if item.r_net is not None else ""
        out.append(f"  {item.prediction_id} {item.symbol} {DECISION_CZ.get(item.decision, item.decision)}: "
                   f"{item.outcome_state or item.status} {r} [{item.cost_layer}]"[:78])

    out += [THIN, "MEZIBEHOVA DELTA (modul 92/106)"]

    for symbol, delta in ctx["delta"].items():
        if delta.get("state") == "NO_PATH":
            out.append(f"  {symbol:<8} bez cesty")
            continue
        crosses = len(delta.get("locked_level_crossings", []))
        out.append(f"  {symbol:<8} {delta['change_pips']:+7.1f} pip | rozsah {delta['range_pips']:.1f} pip"
                   f" | {delta.get('change_atr_h1') or 0:+.1f} ATR | udalosti {len(delta.get('events', []))}"
                   f"{' | prekrizeni urovni ' + str(crosses) if crosses else ''}")

    out += [THIN, "TOP-3 (modul 141)"]
    top = ctx["selection"].top

    if not top:
        out.append("  zadny kandidat neprosel branami - NEOBCHODOVAT je platny vysledek (no forced trade)")

    for rank, candidate in enumerate(top, 1):
        out += candidate_block(rank, candidate, ctx["theses"].get(candidate.symbol), p, ctx["balance"])

        lock = ctx["locks"].get(candidate.symbol)

        if lock:
            out.append(f"   evidence: {lock}")

    for symbol, note in ctx["continuity"].items():
        out.append(f"  {symbol}: {note}"[:78])

    for symbol, note in ctx["selection"].concentration.items():
        out.append(f"  {symbol}: {note}"[:78])

    out += [THIN, "VSECHNY PARY"]

    for analysis in ctx["analyses"]:
        c = analysis.candidate
        reason = c.reasons[0] if c.reasons else ""
        thesis = f" (teze {c.thesis_direction})" if c.decision == "NO TRADE" and c.thesis_direction != "NONE" else ""
        out.append(f"  {c.symbol:<8} {DECISION_CZ[c.decision]}{thesis} | {analysis.regime.label}"[:78])

        if reason:
            out.append(f"           {reason[:67]}")

    out += [THIN] + dashboard(ctx["stats"])
    out += [THIN] + adversarial_lines(ctx["adversarial"])
    out.append("CO BYCH PRISTE ZMENIL? (kandidati zmen, nic se nemeni automaticky)")

    for line in ctx.get("change_candidates") or ["  zadny kandidat (malo uzavrenych predikci)"]:
        out.append(f"  {line}"[:78])

    out += certificate_lines(ctx["certificate"], ctx["pipeline"])
    out.append("Analyza je modelova, bez zaruky; neni to investicni doporuceni. Pred obchodem over kotaci u brokera.")
    return "\n".join(out)
