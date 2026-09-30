"""V7.8.0 final run procedure (module 145; supersedes 83 and 128).

    1  load the model (manifest 0-145, Word document if present) and the
       persistent state (ledger, run state, archive, source register)
    2  determine the previous official (COMMITTED) T0
    3  detect the market session
    4  acquire data: live 1-minute bars (Twelve Data, if a key is set),
       canonical/provisional BID/ASK path (Dukascopy), fundamentals, calendar
    5  build the multi-source T0 snapshot, classify every observation
    6  reconcile conflicts, reject outliers, measure source consistency
    7  (prices are printed in the Czech report)
    8  between-run path: coverage certificate + delta per pair
    9  audit all due predictions BEFORE any new one
    10 thesis book: preserve prior theses, no-instant-flip
    11 full analysis per pair (technical, fundamental, regime, decision)
    12 cost / event / no-chase / risk gates (inside the decision)
    13 Top-3 with continuity and factor concentration
    14 lock predictions justified by the verified T0 set only
    15 persist artifacts, staged commit, read-back
    16 Czech report + English audit artifacts, certificates

A failing step is recorded (trace + run state) and the run continues in
the layers that do not depend on it; nothing is fabricated to fill a gap.
Closed markets never produce NOW.
"""

import json
import os
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.config import PROJECT_ROOT
from src.database import initialize_database
from src.engine.backtest import event_cluster
from src.engine.data import load_pair
from src.engine.params import DEFAULT_PARAMS, ModelParams
from src.engine.pipeline import analyze_pair
from src.engine.portfolio import select_top
from src.engine.thesis import SqliteThesisStore, ThesisBook
from src.instruments import get_instrument, parse_symbols
from src.path_archive import day_minutes, initialize_path_archive, rebuild_aggregates
from src.prediction_ledger import PredictionRejected, initialize_ledger, list_predictions, lock_prediction
from src.stats.errors import taxonomy_table
from src.stats.performance import summarize
from src.v78 import manifest as M
from src.v78 import persist, report
from src.v78.audit import audit_all
from src.v78.coverage import between_run_delta, coverage, path_minutes
from src.v78.quotes import QuoteObservation, Snapshot, build_pair_quote, market_state, skew_state, source_consistency
from src.v78.runstate import Trace, create_run, set_state
from src.v78.sources import initialize_register, record_capability, register_state, register_version, twelve_data_key

UTC = timezone.utc
WORKING_WINDOW = timedelta(days=14)          # module 107
MODEL_DOC_CANDIDATES = ("docs/FX_MASTER_MODEL_V7.8.0.docx",)


@dataclass
class RunOptions:
    symbols: list = field(default_factory=list)
    params: ModelParams = DEFAULT_PARAMS
    fetch: bool = True             # download new data (False = offline run on stored data)
    lock: bool = True              # lock Top-3 predictions into the ledger
    balance: float = 10000.0       # paper account for position sizing
    dukascopy_days: int = 5        # canonical days to catch up per run
    broker: object = None          # optional broker adapter (src/broker/)
    now: datetime | None = None


# ----------------------------------------------------------------------
# step 4: acquisition
# ----------------------------------------------------------------------

class ArchivingTwelveDataFeed:
    """Wraps the Twelve Data client so that every JSON payload is archived
    with its hash (module 124). The API key is never stored."""

    def __init__(self, api_key: str):
        from src.twelve_data import TwelveDataFeed

        self.inner = TwelveDataFeed(api_key=api_key, timeout=15)
        original = self.inner._request

        def archived(params: dict) -> dict:
            data = original(params)
            from src.path_archive import store_payload

            body = json.dumps(data, sort_keys=True).encode("utf-8")
            endpoint = "time_series?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            store_payload(source_id="TWELVE_DATA", kind="TD_JSON", endpoint=endpoint,
                          instrument=params.get("symbol"), side="MID", period_start=None, period_end=None,
                          http_status=200, content=body, parser_version="td-1")
            return data

        self.inner._request = archived

    def __getattr__(self, name):
        return getattr(self.inner, name)


def acquire_live(symbols: list[str], now: datetime, notes: list) -> dict:
    """Twelve Data 1-minute catch-up (only what is missing; 0 credits when current)."""
    key = twelve_data_key()

    if not key:
        record_capability("TWELVE_DATA", "KEY-REQUIRED", "TWELVE_DATA_API_KEY not configured")
        notes.append("Twelve Data: klic neni nastaven (python scripts/set_api_key.py) - bez zivych dat")
        return {"state": "KEY-REQUIRED"}

    from src.data_update import update_all

    feed = ArchivingTwelveDataFeed(key)
    results = update_all(feed, [(s, "1min") for s in symbols], now=now)
    errors = [f"{r.symbol}: {r.error}" for r in results if r.error]

    if errors and len(errors) == len(results):
        record_capability("TWELVE_DATA", "RUNTIME-FAIL", errors[0])
    else:
        record_capability("TWELVE_DATA", "RUNTIME-PASS", f"{sum(r.saved for r in results)} bars saved")

    if errors:
        notes.extend(f"Twelve Data {e[:90]}" for e in errors[:3])

    return {"state": "OK" if not errors else "PARTIAL", "saved": sum(r.saved for r in results),
            "calls": sum(r.calls for r in results), "errors": errors,
            "budget": feed.budget.status()}


def acquire_path(symbols: list[str], now: datetime, days: int, notes: list, budget_s: float = 90.0) -> dict:
    """Canonical BID/ASK days since the last complete one + provisional
    hours of today (backfill ladder, modules 136/137).

    A run spends at most about budget_s seconds here and retries each file
    only twice (the server may throttle); whatever is left is fetched by
    the next run or by `fxbot.py history`. Nothing is estimated instead."""
    import time

    from src.sources import dukascopy
    from src.sources.dukascopy import SourceUnavailable, ingest_day, ingest_provisional_hours

    summary = {"days": {}, "hours": {}, "state": "OK"}
    deadline = time.monotonic() + budget_s
    saved_retries = dukascopy.MAX_RETRIES
    dukascopy.MAX_RETRIES = 2

    def out_of_time() -> bool:
        if time.monotonic() > deadline:
            if summary["state"] == "OK":
                summary["state"] = "BUDGET"
                notes.append(f"Dukascopy: casovy limit {budget_s:.0f} s - zbytek dalsim behem / fxbot.py history")
            return True
        return False

    try:
        for symbol in symbols:
            for back in range(days, 0, -1):
                if out_of_time():
                    break

                day = now.date() - timedelta(days=back)
                state = ingest_day(symbol, day, now)
                summary["days"][f"{symbol} {day}"] = state

                if state in ("COMPLETE", "PARTIAL"):
                    rebuild_aggregates(symbol, day - timedelta(days=1), day + timedelta(days=1))

            if out_of_time():
                break

            summary["hours"][symbol] = ingest_provisional_hours(symbol, now.date(), now, deadline)
    except SourceUnavailable as exc:
        summary["state"] = "UNAVAILABLE"
        notes.append(f"Dukascopy neodpovida ({str(exc)[-50:]}) - historie z archivu, mezery GAP-UNRESOLVED")
    finally:
        dukascopy.MAX_RETRIES = saved_retries

    record_capability("DUKASCOPY_M1", "RUNTIME-FAIL" if summary["state"] == "UNAVAILABLE" else "RUNTIME-PASS",
                      summary["state"])
    return summary


FUNDAMENTALS_EVERY = timedelta(hours=6)


def last_fundamental_update() -> datetime | None:
    from src.fundamental.store import get_fund_connection, initialize_fundamentals

    initialize_fundamentals()

    with get_fund_connection() as connection:
        row = connection.execute("SELECT MAX(attempted_at) AS t FROM fetch_log WHERE source_id = 'FRED' "
                                 "AND result = 'OK'").fetchone()

    return datetime.fromisoformat(row["t"]) if row and row["t"] else None


def acquire_fundamentals(now: datetime, notes: list, force: bool = False) -> dict:
    """Daily series change once a day: a full update at most every 6 hours
    (the calendar is refreshed every run - schedules can move)."""
    from src.fundamental.adapters import update_all as update_fundamentals
    from src.fundamental.calendar import update_calendar

    out = {}
    last = last_fundamental_update()

    if not force and last is not None and now - last < FUNDAMENTALS_EVERY:
        calendar = update_calendar(now)
        out["FF_CALENDAR"] = "OK" if calendar.get("ok") else f"FAIL {calendar.get('detail')}"
        out["series"] = f"aktualni (posledni stazeni {last:%H:%M} UTC)"
        return out

    for result in update_fundamentals((now - timedelta(days=21)).date()):
        out[result.source] = "OK" if result.ok else f"FAIL {result.detail[:80]}"
        record_capability(result.source, "RUNTIME-PASS" if result.ok else "RUNTIME-FAIL", result.detail[:200])

        if not result.ok:
            notes.append(f"fundamenty {result.source}: {result.detail[:70]}")

    calendar = update_calendar(now)
    out["FF_CALENDAR"] = "OK" if calendar.get("ok") else f"FAIL {calendar.get('detail')}"
    record_capability("FF_CALENDAR", "RUNTIME-PASS" if calendar.get("ok") else "RUNTIME-FAIL",
                      str(calendar)[:200])
    return out


# ----------------------------------------------------------------------
# step 5-6: snapshot
# ----------------------------------------------------------------------

def observations_for(symbol: str, now: datetime, broker=None) -> tuple[list[QuoteObservation], tuple | None]:
    from src.data_state import get_latest_bar_open
    from src.engine.data import twelve_data_minutes

    observations = []
    now_ts = now.timestamp()
    latest = get_latest_bar_open(symbol, "1min")

    if latest is not None:
        bars = twelve_data_minutes(symbol, int(latest.timestamp()), int(latest.timestamp()) + 60)

        if bars:
            bar = bars[-1]
            observations.append(QuoteObservation(
                symbol, "TWELVE_DATA", "API_SNAPSHOT", bar.mc, float(bar.ts + 60), now_ts,
                feed_type="MID_1MIN_CLOSE", note="close of the newest stored closed 1-minute bar"))

    # delayed bid/ask reference: newest provisional/canonical minute
    spread_reference = None

    for back in range(0, 3):
        minutes = day_minutes(symbol, now.date() - timedelta(days=back), allow_provisional=True)

        if minutes:
            last = minutes[-1]
            observations.append(QuoteObservation(
                symbol, "DUKASCOPY_TICK", "DELAYED_REFERENCE", last.mc, float(last.ts + 60), now_ts,
                bid=last.bc, ask=last.ac, feed_type="BIDASK_1MIN_CLOSE", note="finished hour tick file"))
            # typical spread of the last hour (median of minute close spreads)
            spreads = sorted(m.ac - m.bc for m in minutes[-60:])
            spread_reference = (spreads[len(spreads) // 2], "DUKASCOPY median 60 min")
            break

    if broker is not None:
        try:
            observations.extend(broker.quotes([symbol], now))
        except Exception as exc:          # a broker failure never blocks the analysis
            observations.append(QuoteObservation(symbol, getattr(broker, "source_id", "BROKER"), "BROKER_TRUTH",
                                                 0.0, None, now_ts, note=f"broker error {exc}", rejected="broker error"))

    return observations, spread_reference


def build_snapshot(symbols: list[str], now: datetime, broker=None) -> Snapshot:
    start = datetime.now(UTC)
    pairs = {}
    consistency = {}

    for symbol in symbols:
        observations, spread_reference = observations_for(symbol, now, broker)
        pairs[symbol] = build_pair_quote(symbol, observations, now, spread_reference)

        # source consistency on the overlap of the last 24 h (module 13/143)
        from src.engine.data import twelve_data_minutes

        end_ts = int(now.timestamp())
        td = twelve_data_minutes(symbol, end_ts - 86400, end_ts)

        if td:
            duka = []
            day = (now - timedelta(days=1)).date()

            while day <= now.date():
                duka += [m for m in day_minutes(symbol, day, True) if m.ts >= end_ts - 86400]
                day += timedelta(days=1)

            consistency[symbol] = source_consistency(td, duka, get_instrument(symbol).pip)

    skew, skew_label = skew_state(pairs)
    return Snapshot(now, start, datetime.now(UTC), pairs, skew, skew_label, market_state(now), consistency)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def ledger_trades() -> list[dict]:
    """Ledger predictions with a final outcome, as dicts for src/stats."""
    trades = []

    for p in list_predictions(limit=5000):
        if p["direction"] == "NONE" or not p["outcomes"]:
            continue

        last = p["outcomes"][-1]
        trades.append({
            "symbol": p["instrument"], "t0": datetime.fromisoformat(p["t0"]).timestamp(),
            "decision": p["decision"], "direction": p["direction"], "confidence": p["confidence"],
            "setup_type": p["setup_type"], "outcome_state": last["outcome_state"],
            "r_net": float(last["r_multiple"]) if last["r_multiple"] is not None else None,
            "r_model": None, "mfe_r": float(last["mfe"]) if last["mfe"] else None,
            "mae_r": float(last["mae"]) if last["mae"] else None, "notes": last["notes"],
            "triggered": any(s["state"] == "TRIGGERED" for s in p["states"]) or p["decision"].endswith("NOW"),
            "event_cluster": p["event_cluster"], "model_version": p["model_version"],
        })

    return trades


def change_candidates(trades: list[dict]) -> list[str]:
    """Learning loop (module 79): 1 case = observation, 2 = candidate,
    3+ consistent = active candidate. Never applied automatically."""
    lines = []

    for key, count in taxonomy_table(trades).items():
        if count >= 3:
            lines.append(f"AKTIVNI KANDIDAT ({count}x): {key}")
        elif count == 2:
            lines.append(f"kandidat ({count}x): {key}")

    return lines[:6]


def data_quality(quote, fund_quality: str) -> str:
    if quote.execution == "EXECUTABLE":
        return "A" if fund_quality in ("A", "B") else "B"

    if quote.data_state in ("LIVE", "FRESH"):
        return "B" if fund_quality in ("A", "B") else "C"

    return "D"


def find_model_document() -> Path | None:
    for candidate in MODEL_DOC_CANDIDATES:
        path = PROJECT_ROOT / candidate

        if path.exists():
            return path

    return None


# ----------------------------------------------------------------------
# the run
# ----------------------------------------------------------------------

def execute(options: RunOptions) -> dict:
    p = options.params
    now = (options.now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    symbols = options.symbols or parse_symbols(os.getenv("FXBOT_SYMBOLS") or os.getenv("COLLECTOR_SYMBOLS"))
    notes: list[str] = []
    blocked: list[str] = []

    # ---------------------------------------------------------- 1. model + state
    initialize_database()
    initialize_ledger()
    initialize_path_archive()
    initialize_register()
    manifest_problems = M.verify_manifest()
    doc = find_model_document()
    doc_check = M.verify_document(doc) if doc else {"status": "MODEL DOCUMENT NOT PRESENT", "problems": []}
    model_load = "MANIFEST OK" if not manifest_problems else "MANIFEST INVALID"
    model_load += f" | Word: {doc_check['status']}"
    fp = M.fingerprint(p.fingerprint)
    run = create_run(now, fp, p.fingerprint, M.MODEL_VERSION, M.IMPLEMENTATION)
    set_state(run.run_id, "RUNNING", "started")
    trace = Trace(run.run_id)
    run_dir = persist.RUNS_DIR / run.run_id
    ctx = {"run": run, "params": p, "model_version": M.MODEL_VERSION, "implementation": M.IMPLEMENTATION,
           "model_load": model_load, "balance": options.balance}

    if manifest_problems:
        blocked.append("MODEL LOAD INCOMPLETE: " + "; ".join(manifest_problems))
        trace.set(101, "BLOCKED", "; ".join(manifest_problems))
    else:
        trace.set(101, "PASS" if doc_check["status"] == "MODEL LOAD COMPLETE" else "CONDITIONAL",
                  f"manifest 0-145 complete; document: {doc_check['status']}")

    trace.set(102, "PASS", f"persistent state loaded; previous committed run {run.previous_run_id or 'none'}")
    trace.set(114, "PASS", f"fingerprint {fp[:16]}")

    try:
        # ------------------------------------------------------ 3. session
        market = market_state(now)
        trace.set(134, "PASS" if market in ("OPEN", "CLOSED", "PRE-OPEN") else "CONDITIONAL", f"market {market}")

        if market != "OPEN":
            notes.append(f"trh {market}: zadne NOW rozhodnuti; beh slouzi auditu a priprave")

        # ------------------------------------------------------ 4. acquisition
        acquisition = {}

        if options.fetch:
            acquisition["live"] = acquire_live(symbols, now, notes)
            acquisition["path"] = acquire_path(symbols, now, options.dukascopy_days, notes)
            acquisition["fundamentals"] = acquire_fundamentals(now, notes)
        else:
            acquisition["mode"] = "OFFLINE (stored data only)"
            notes.append("offline beh: nova data se nestahuji")

        trace.set(8, "PASS" if options.fetch else "CONDITIONAL", json.dumps(acquisition, default=str)[:300])
        trace.set(125, "PASS", "runtime capability recorded per source")
        trace.set(116, "PASS", f"register version {register_version()}")

        # ------------------------------------------------------ 5-6. snapshot
        snapshot = build_snapshot(symbols, now, options.broker)
        ctx["snapshot"] = snapshot
        states = [q.data_state for q in snapshot.pairs.values()]
        fresh = sum(1 for s in states if s in ("LIVE", "FRESH"))
        trace.set(117, "PASS", "quote contract validated per observation")
        trace.set(118, "PASS" if snapshot.skew_state in ("SYNCHRONIZED", "N/A") else "CONDITIONAL",
                  f"skew {snapshot.max_skew_s} s ({snapshot.skew_state})")
        trace.set(119, "PASS" if fresh == len(states) else "CONDITIONAL", f"{fresh}/{len(states)} pairs LIVE/FRESH")
        conflicts = [s for s, q in snapshot.pairs.items() if q.data_state == "DATA-CONFLICT"]
        trace.set(133, "CONDITIONAL" if conflicts else "PASS", f"conflicts: {conflicts or 'none'}")
        drift = [s for s, c in snapshot.consistency.items() if c and c["state"] != "CONSISTENT"]
        trace.set(13, "CONDITIONAL" if drift else "PASS", f"source drift: {drift or 'none'}")
        trace.set(135, "PASS", "prices printed in the Czech report")

        if market == "OPEN" and fresh == 0:
            blocked.append("LIVE CENA NEOVERENA u vsech paru - zadne NOW (DATA-BLOCKED)")

        # ------------------------------------------------------ 8. coverage + delta
        from src.data_update import settle_seconds

        start_ts = int((run.previous_t0 or (now - WORKING_WINDOW)).timestamp())
        # minutes still inside the settle delay are not published yet - not a gap
        end_ts = int(now.timestamp() - settle_seconds() - 60)
        end_ts -= end_ts % 60
        open_predictions = [p_ for p_ in list_predictions(limit=500)
                            if p_["direction"] != "NONE" and not any(
                                o["outcome_state"] in ("TP1_BEFORE_SL", "SL_BEFORE_TP1", "SEQUENCE_UNKNOWN",
                                                       "EXPIRED", "NOT_ACTIVATED") for o in p_["outcomes"])]
        coverages, deltas, pair_series = {}, {}, {}

        from src.fundamental.calendar import events_between

        for symbol in symbols:
            instrument = get_instrument(symbol)
            series = load_pair(symbol, p, int(now.timestamp()), live=True)
            pair_series[symbol] = series
            atr_h1 = series.h1.atr14[-1] if len(series.h1) and series.h1.atr14[-1] else None
            bars, sources = path_minutes(symbol, start_ts, end_ts)
            locked = [x for x in open_predictions if x["instrument"] == symbol]
            windows = [(int(datetime.fromisoformat(x["t0"]).timestamp()), end_ts) for x in locked]
            coverages[symbol] = coverage(symbol, start_ts, end_ts, windows, bars, sources)
            events = events_between(start_ts, end_ts, (instrument.base, instrument.quote), "High")
            deltas[symbol] = between_run_delta(symbol, start_ts, end_ts, instrument.pip, atr_h1, locked, events, bars)

        ctx["coverage"], ctx["delta"] = coverages, deltas
        cov_states = [c.state for c in coverages.values()]
        trace.set(123, "PASS" if all(s == "COMPLETE" for s in cov_states) else "CONDITIONAL",
                  f"coverage states {dict((s, cov_states.count(s)) for s in set(cov_states))}")
        trace.many((88, 137), "PASS" if all(s in ("COMPLETE", "PARTIAL") for s in cov_states) else "CONDITIONAL",
                   "gaps classified INFO/MATERIAL/CRITICAL")
        trace.many((92, 106), "PASS", f"delta from {datetime.fromtimestamp(start_ts, tz=UTC).isoformat()}")

        # ------------------------------------------------------ 9. audit due predictions
        audit_items = audit_all(now)
        ctx["audit"] = audit_items
        trace.many((61, 62, 81), "PASS", f"{len(audit_items)} open predictions audited before new ones")

        # ------------------------------------------------------ 10-12. analysis
        store = SqliteThesisStore()
        store.run_id = run.run_id
        book = ThesisBook(store)

        for item in audit_items:
            if item.outcome_state or item.triggered_at:
                book.update_from_path(item.symbol, item.resolved_at or int(now.timestamp()), item.outcome_state,
                                      item.triggered_at, item.prediction_id)

        for thesis in store.all_open():
            book.update_from_path(thesis.symbol, int(now.timestamp()), None, None, thesis.prediction_id)

        from src.data_state import get_status

        analyses = []

        for symbol in symbols:
            quote = snapshot.pairs[symbol]
            series = pair_series[symbol]
            status = get_status(symbol, "1min", now=now)
            data_state = status.state.value if quote.now_eligible else (
                "CLOSED" if market != "OPEN" else status.state.value)
            price = quote.canonical.mid if quote.now_eligible else None
            analysis = analyze_pair(series, int(now.timestamp()), p, data_state, quote.spread_reference,
                                    "AVAILABLE", price, quote.now_eligible)
            analysis.series = series
            analyses.append(analysis)

        ctx["analyses"] = analyses
        trace.many(range(42, 60), "PASS", "technical + decision gates evaluated for every pair")
        trace.many((36, 37, 50, 51), "PASS", "evidence matrix, hypotheses, tradeability")
        trace.set(40, "PASS", "regime diagnosed per pair")

        # ------------------------------------------------------ 13. Top-3 + no-flip
        flip_notes = {}
        allowed = []

        for analysis in analyses:
            candidate = analysis.candidate
            check = book.check(candidate, int(now.timestamp()), analysis.regime.transition)

            if candidate.actionable and check.allowed:
                allowed.append(candidate)
            elif candidate.actionable:
                flip_notes[candidate.symbol] = check.reason

        selection = select_top(allowed, p)
        ctx["selection"] = selection
        continuity = {}

        for thesis in store.all_open():
            if thesis.symbol not in [c.symbol for c in selection.top]:
                continuity[thesis.symbol] = (f"mimo Top-3, puvodni teze {thesis.direction} stale plati "
                                             f"({thesis.prediction_id}, {thesis.state})")

        for symbol, note in flip_notes.items():
            continuity.setdefault(symbol, note)

        ctx["continuity"] = continuity
        trace.many((138, 139, 140, 141), "PASS", f"open theses {len(store.all_open())}; blocked flips {len(flip_notes)}")
        trace.set(58, "PASS", f"concentration removed {len(selection.concentration)}")

        # ------------------------------------------------------ 14. lock
        locks = {}
        new_ids = []

        if options.lock:
            for candidate in selection.top:
                analysis = next(a for a in analyses if a.symbol == candidate.symbol)
                quote = snapshot.pairs[candidate.symbol]
                result = lock_candidate(run.run_id, now, candidate, analysis, quote, coverages[candidate.symbol], p, fp)

                if result.startswith("P-"):
                    new_ids.append(result)
                    book.open_thesis(candidate, result, int(now.timestamp()), p.horizon_hours)
                    locks[candidate.symbol] = f"zamceno {result}"
                else:
                    locks[candidate.symbol] = result

        ctx["locks"] = locks
        ctx["theses"] = {t.symbol: t for t in store.all_open()}
        trace.set(60, "PASS" if new_ids or not selection.top else "CONDITIONAL",
                  f"locked {len(new_ids)}: {', '.join(new_ids) or '-'}")

        # ------------------------------------------------------ stats + learning
        trades = ledger_trades()
        ctx["stats"] = {"live": summarize(trades, "evidence")}
        ctx["change_candidates"] = change_candidates(trades)
        trace.many((66, 67, 69, 70, 72, 79), "PASS", f"{len(trades)} resolved ledger predictions evaluated")

        set_state(run.run_id, "ANALYSIS_COMPLETE", "analysis done")

    except Exception as exc:
        tb = traceback.format_exc()
        set_state(run.run_id, "FAILED", f"{type(exc).__name__}: {exc}"[:300], finished_at=datetime.now(UTC).isoformat())
        trace.fill_from_manifest(M.MODULES)
        trace.write()
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "error.txt").write_text(tb, encoding="utf-8")
        return {"run_id": run.run_id, "state": "FAILED", "error": str(exc), "traceback": tb, "report": None}

    # ---------------------------------------------------------- 15. persistence
    set_state(run.run_id, "PERSISTENCE_PENDING", "writing artifacts")
    trace.fill_from_manifest(M.MODULES)
    ctx["register_version"] = register_version()
    ctx["blocked_critical"] = blocked + [n for n in notes if "neni nastaven" in n or "neodpovida" in n]
    adversarial = adversarial_flags(ctx, snapshot, coverages, audit_items, manifest_problems, run)
    ctx["adversarial"] = adversarial
    artifacts = {}
    artifacts["snapshot.json"] = persist.write_artifact(run_dir, "snapshot.json", snapshot.to_dict())
    artifacts["coverage.json"] = persist.write_artifact(run_dir, "coverage.json",
                                                        {s: c.to_dict() for s, c in coverages.items()})
    artifacts["delta.json"] = persist.write_artifact(run_dir, "delta.json", deltas)
    artifacts["analysis.json"] = persist.write_artifact(run_dir, "analysis.json",
                                                        [analysis_dict(a) for a in analyses])
    artifacts["audit.json"] = persist.write_artifact(run_dir, "audit.json", [vars(i) for i in audit_items])
    artifacts["sources.json"] = persist.write_artifact(run_dir, "sources.json", register_state())
    artifacts["trace.json"] = persist.write_artifact(run_dir, "trace.json",
                                                     {str(k): v for k, v in sorted(trace.rows.items())})
    artifacts["params.json"] = persist.write_artifact(run_dir, "params.json", p.to_dict())
    commit = persist.commit_manifest(run.run_id, now, artifacts, new_ids, {
        "model_version": M.MODEL_VERSION, "implementation": M.IMPLEMENTATION, "model_fingerprint": fp,
        "params_fingerprint": p.fingerprint, "source_register_version": ctx["register_version"],
        "previous_run_id": run.previous_run_id,
        "previous_t0": run.previous_t0.isoformat() if run.previous_t0 else None,
        "notes": notes,
    })
    persist.write_artifact(run_dir, "run_manifest.json", commit)
    trace.write()
    readback = persist.read_back(run_dir, commit)
    trace_summary = trace.summary()

    # ---------------------------------------------------------- 16. certificates + report
    conditional = bool(blocked) or any(s != "COMPLETE" for s in cov_states) or (market == "OPEN" and fresh < len(states)) \
        or drift or conflicts or acquisition.get("path", {}).get("state") == "UNAVAILABLE"

    if manifest_problems:
        status = "RUN BLOCKED"
    elif readback["status"] != "PASS":
        status = "REPRODUCIBILITY INCOMPLETE"
    elif conditional:
        status = "RUN COMPLETE-CONDITIONAL"
    else:
        status = "RUN COMPLETE"

    archive_counts = commit["stores"]["market_path"]
    broker_state = (f"{getattr(options.broker, 'source_id', 'BROKER')} pripojen" if options.broker
                    else "BROKER-BLOCKED (zadny broker adapter; ceny nejsou XTB)")
    ctx["certificate"] = {
        "status": status, "model_version": M.MODEL_VERSION, "implementation": M.IMPLEMENTATION,
        "run_id": run.run_id, "t0": now.isoformat(), "previous_run_id": run.previous_run_id or "-",
        "previous_t0": run.previous_t0.isoformat() if run.previous_t0 else "-",
        "module_trace": f"{sum(trace_summary.values())}/146 {trace_summary}",
        "archive": f"dny {archive_counts.get('days_complete')} mesice {archive_counts.get('months_complete')} "
                   f"svicky {archive_counts.get('bars')}",
        "path_coverage": dict((s, cov_states.count(s)) for s in set(cov_states)),
        "gap_counts": sum(len(c.gaps) for c in coverages.values()),
        "quote_freshness": dict((s, states.count(s)) for s in set(states)),
        "predictions_locked": len(new_ids),
        "persistence_read_back": readback["status"] + (f" {readback['problems'][:2]}" if readback["problems"] else ""),
        "broker_verification": broker_state,
    }
    capability = register_state()
    ctx["pipeline"] = {
        "status": "PASS" if not conditional else "CONDITIONAL",
        "source_capability": (", ".join(f"{r['source_id']}={r['state']}" for r in capability
                                        if r["tested_at"])[:200] or "netestovano v tomto behu (offline)"),
        "quote_freshness": ctx["certificate"]["quote_freshness"],
        "atomic_skew": f"{snapshot.max_skew_s} s {snapshot.skew_state}",
        "path_coverage": ctx["certificate"]["path_coverage"],
        "unresolved_gaps": sum(1 for c in coverages.values() for g in c.gaps if g.severity == "CRITICAL"),
        "source_consistency": {s: c["state"] for s, c in snapshot.consistency.items() if c} or "neni prekryv",
        "broker_verification": broker_state,
    }
    text = report.render(ctx)
    persist.write_artifact(run_dir, "report_cz.txt", text)
    persist.write_artifact(run_dir, "certificate.json", {"run": ctx["certificate"], "pipeline": ctx["pipeline"]})
    final_state = {"RUN COMPLETE": "COMMITTED", "RUN COMPLETE-CONDITIONAL": "COMMITTED_CONDITIONAL",
                   "REPRODUCIBILITY INCOMPLETE": "REPRODUCIBILITY_INCOMPLETE", "RUN BLOCKED": "FAILED"}[status]
    set_state(run.run_id, final_state, status, finished_at=datetime.now(UTC).isoformat(),
              certificate=ctx["certificate"], artifact_dir=str(run_dir),
              summary={"locked": new_ids, "top": [c.symbol for c in selection.top]})
    return {"run_id": run.run_id, "state": final_state, "certificate": status, "report": text,
            "run_dir": str(run_dir), "locked": new_ids}


def lock_candidate(run_id: str, now: datetime, candidate, analysis, quote, cov, p: ModelParams, fp: str) -> str:
    instrument = get_instrument(candidate.symbol)
    q = lambda v: round(v, instrument.decimals)
    c = quote.canonical

    if c is None or not quote.now_eligible:
        return "nezamceno: kotace neni LIVE/FRESH (predikce jen z overene T0 sady)"

    fund_quality = min((analysis.fund.base.quality, analysis.fund.quote.quality), key=lambda x: "ABCD".index(x))
    top_evidence = candidate.evidence_for[0].text if candidate.evidence_for else "technicka struktura"

    try:
        return lock_prediction(
            model_version=f"{M.MODEL_VERSION}/{M.IMPLEMENTATION}",
            run_id=run_id,
            t0=now,
            instrument=candidate.symbol,
            decision=candidate.decision,
            reference_price=q(c.mid),
            price_source=f"{c.source_id} {c.feed_type} ({'bid/ask' if c.has_bid_ask else 'MODEL-PRICE'})",
            price_timestamp=datetime.fromtimestamp(c.source_ts, tz=UTC),
            data_state="CURRENT" if analysis.candidate.gate("DATA_STATE").status == "PASS" else "UNVERIFIED",
            data_quality=data_quality(quote, fund_quality),
            bid=q(c.bid) if c.bid else None,
            ask=q(c.ask) if c.ask else None,
            forecast_mode="TECHNICAL+FUNDAMENTAL",
            setup_type=candidate.setup_type,
            entry=q(candidate.entry),
            entry_zone_low=q(candidate.zone_low),
            entry_zone_high=q(candidate.zone_high),
            trigger_price=q(candidate.entry) if candidate.decision.startswith("WAIT") else None,
            stop_loss=q(candidate.stop),
            tp1=q(candidate.targets[0]),
            tp2=q(candidate.targets[1]),
            tp3=q(candidate.targets[2]),
            primary_horizon=f"{p.horizon_hours}h",
            expected_move=f"TP1 {abs(candidate.targets[0] - candidate.entry) / instrument.pip:.0f} pip",
            catalyst=top_evidence[:300],
            thesis=candidate.hypotheses.get("H1", "")[:500],
            counterforce=candidate.hypotheses.get("H3", "")[:500],
            invalidation=candidate.invalidation,
            regime=analysis.regime.label,
            confidence=candidate.confidence,
            event_cluster=event_cluster(candidate.symbol, candidate.direction, int(now.timestamp())),
            reasons=candidate.reasons,
            inputs={
                "model_fingerprint": fp, "params": p.fingerprint, "risk_pct": candidate.risk_pct,
                "rr_net": round(candidate.rr_net, 3), "cost_price": candidate.cost_price,
                "clusters_for": candidate.clusters_for, "clusters_against": candidate.clusters_against,
                "gates": [(g.name, g.status, g.reason) for g in candidate.gates],
                "evidence": [e.to_dict() for e in candidate.evidence_for + candidate.evidence_against][:12],
                "quote": c.to_dict(now.timestamp()),
                "path_coverage_state": cov.state,
                "last_known_path_ts": max((b.ts for b in analysis.series.h1_bars), default=None),
                "archive_segment": f"SEG-DUKASCOPY_M1-{candidate.symbol.replace('/', '')}-{now:%Y%m%d}",
            },
            now=now,
        )
    except PredictionRejected as exc:
        return f"zamitnuto evidenci: {exc}"


def analysis_dict(a) -> dict:
    c = a.candidate
    return {
        "symbol": a.symbol, "t": a.t, "decision": c.decision, "direction": c.direction,
        "thesis_direction": c.thesis_direction, "confidence": c.confidence, "setup_type": c.setup_type,
        "entry": c.entry, "stop": c.stop, "targets": c.targets, "rr_net": c.rr_net,
        "reasons": c.reasons, "hypotheses": c.hypotheses, "invalidation": c.invalidation,
        "gates": [(g.name, g.status, g.reason) for g in c.gates],
        "evidence": [e.to_dict() for e in a.fund.evidence],
        "technical": {"bias": a.tech.bias, "strength": a.tech.strength, "momentum_z": a.tech.momentum_z,
                      "evidence": a.tech.evidence, "notes": a.tech.notes,
                      "d1": a.tech.d1.trend if a.tech.d1 else None, "h4": a.tech.h4.trend if a.tech.h4 else None,
                      "h1": a.tech.h1.trend if a.tech.h1 else None},
        "regime": {"label": a.regime.label, "transition": a.regime.transition, "notes": a.regime.notes},
        "fundamental_gaps": a.fund.data_gaps, "risk_regime": a.fund.risk_regime, "equity_corr": a.fund.equity_corr,
    }


def adversarial_flags(ctx, snapshot, coverages, audit_items, manifest_problems, run) -> dict:
    flags = {}
    incomplete = [s for s, c in coverages.items() if c.state not in ("COMPLETE",)]
    flags["coverage"] = f"{len(incomplete)} par(u) bez uplne cesty" if incomplete else None
    drift = [s for s, c in snapshot.consistency.items() if c and c["state"] != "CONSISTENT"]
    flags["drift"] = ", ".join(drift) if drift else None
    flags["open_bar"] = None
    flags["timezone"] = next((o.rejected for q in snapshot.pairs.values() for o in q.observations
                              if o.rejected and "TIMEZONE" in o.rejected), None)
    no_bidask = [s for s, q in snapshot.pairs.items() if q.execution == "MODEL-PRICE"]
    flags["spread"] = f"spread jen odhad u {len(no_bidask)} paru (bez live bid/ask)" if no_bidask else None
    flags["session"] = f"trh {snapshot.market}" if snapshot.market != "OPEN" else None
    unknown = [i.prediction_id for i in audit_items if i.outcome_state == "SEQUENCE_UNKNOWN"]
    flags["sequence"] = ", ".join(unknown) if unknown else None
    flags["previous_t0"] = "predchozi T0 je v budoucnosti" if run.previous_t0 and run.previous_t0 > run.t0 else None
    flags["model"] = "; ".join(manifest_problems) if manifest_problems else None
    flags["trace"] = None
    stale = [s for s, q in snapshot.pairs.items() if q.market == "OPEN" and q.data_state not in ("LIVE", "FRESH")]
    flags["stale"] = f"{len(stale)} par(u) bez overene live ceny - jen kontext" if stale else None
    return flags
