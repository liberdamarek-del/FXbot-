"""Module manifest 0-145 and model fingerprint (modules 101, 103, 114).

The model specification (FX_MASTER_MODEL_V7.8.0 Word document) defines
146 modules. This manifest states, for every module, how this code base
implements it:

    IMPLEMENTED     the rule is enforced by code (reference given)
    PARTIAL         enforced in a reduced form; the reason says what is missing
    NOT_AVAILABLE   no keyless data source / capability exists in this
                    runtime; the module is reported N/A with the reason on
                    every run (never silently skipped, module 103)
    SUPERSEDED      an earlier run procedure replaced by module 145

The fingerprint covers the manifest, the parameter set and the version, so
two runs with a different rule set can never share one identity.
"""

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

MODEL_VERSION = "V7.8.0"
IMPLEMENTATION = "fxbot-impl-1.0"
SPEC_MODULES = 146            # 0..145


@dataclass(frozen=True)
class ModuleSpec:
    id: int
    title: str
    status: str
    ref: str
    note: str = ""


I, P, N, S = "IMPLEMENTED", "PARTIAL", "NOT_AVAILABLE", "SUPERSEDED"

_MODULES = [
    (0, "Main task and allowed decisions", I, "engine/decision.py", ""),
    (1, "Architecture and precedence", I, "engine/decision.py, v78/run.py", ""),
    (2, "Model units, source of truth, persistence", I, "prediction_ledger.py, path_archive.py, v78/runstate.py", ""),
    (3, "Evidence taxonomy", I, "engine/evidence.py", ""),
    (4, "Anti-hindsight and immutability", I, "prediction_ledger.py, fundamental/store.py", ""),
    (5, "Absolute verification bans", I, "all adapters", "missing data is reported, never estimated"),
    (6, "Causal reasoning under machine control", P, "engine/decision.py", "hypotheses are built from evidence templates, not free reasoning"),
    (7, "Output discipline", I, "v78/report.py", ""),
    (8, "Live data + historical backfill", I, "v78/run.py, data_update.py, sources/dukascopy.py", ""),
    (9, "Source hierarchy, adapter register, provenance", I, "v78/sources.py", ""),
    (10, "Snapshot T0, freshness, path continuity", I, "v78/quotes.py, v78/coverage.py", ""),
    (11, "Price identity spot/futures/CFD/broker", I, "v78/quotes.py", "public feeds are labelled, never shown as broker price"),
    (12, "Side-correct execution", P, "engine/resolution.py", "historical path side-correct; live quote has no bid/ask without a broker adapter"),
    (13, "Source conflict reconciliation", P, "v78/quotes.py", "few contemporaneous sources; overlap consistency and outlier gate"),
    (14, "Data gap, backfill, recovery", I, "v78/coverage.py, sources/dukascopy.py", ""),
    (15, "History, vintage, revisions", P, "fundamental/store.py", "revisions tracked from first collection; older vintages unknown"),
    (16, "Data quality and confidence classes", I, "engine/fundamental.py, engine/decision.py", ""),
    (17, "FX universe and driver map", P, "instruments.py", "12 active pairs, 4 more on demand; CNH/CNY not supported"),
    (18, "Macro engine", P, "fundamental/calendar.py", "releases used as event risk; no release-surprise model"),
    (19, "Expectation gap and market pricing", P, "fundamental/calendar.py", "forecast/previous shown; actual values not in the free feed"),
    (20, "Central bank engine", P, "engine/fundamental.py", "policy rate level and trend; no guidance/voting data"),
    (21, "Rate repricing engine", I, "engine/fundamental.py", "2y (GBP 5y) differential change as the priced-path proxy; no OIS"),
    (22, "Yield and curve engine", P, "fundamental/catalog.py", "2y/10y for 6 currencies; CHF/NZD monthly only"),
    (23, "Funding and liquidity engine", P, "engine/fundamental.py", "HY spread and stress index; no cross-currency basis"),
    (24, "Carry engine", I, "engine/fundamental.py", "volatility-adjusted policy differential"),
    (25, "Positioning engine", I, "fundamental/adapters.py, engine/fundamental.py", "CFTC TFF weekly"),
    (26, "Options engine", N, "-", "no keyless options data source"),
    (27, "Flow, fixing and reserve flows", N, "-", "no structured free flow data; fixes not modelled"),
    (28, "Fiscal, trade and tariff engine", N, "-", "no structured free feed"),
    (29, "China engine", N, "-", "CNH/CNY outside the universe; no structured China data"),
    (30, "Commodity and oil engine", P, "engine/fundamental.py", "WTI/Brent with measured correlation; no metals feed"),
    (31, "Risk and intermarket engine", I, "engine/fundamental.py", "VIX, S&P 500, HY spread, measured pair beta"),
    (32, "Geopolitical engine", N, "-", "no structured feed; shocks visible only as price/regime"),
    (33, "Intervention engine", P, "engine/fundamental.py", "price context flag only (never evidence of intervention)"),
    (34, "Causal chain engine", P, "engine/decision.py", "chain summarised as H1/H2/H3 from evidence clusters"),
    (35, "Second-order and transmission", P, "engine/fundamental.py", "risk regime transmission via measured beta"),
    (36, "Factor clustering and dependence", I, "engine/evidence.py", ""),
    (37, "Competing hypotheses and counterforce", I, "engine/decision.py", ""),
    (38, "Market reaction engine", P, "engine/decision.py", "price structure must confirm the mechanism"),
    (39, "Correlation, divergence, confluence", P, "engine/fundamental.py", "confluence counted per cluster"),
    (40, "Regime engine", I, "engine/regime.py", ""),
    (41, "Regime transition / change-point", I, "engine/regime.py", "volatility expansion + trend flip / shock"),
    (42, "Technical multi-timeframe + path", I, "engine/technical.py", "D1/H4/H1 decisions, 1min path for resolution"),
    (43, "Level lifetime and structural reset", I, "engine/technical.py", ""),
    (44, "Market microstructure", P, "engine/decision.py", "spread and tick activity only"),
    (45, "Direction != entry", I, "engine/decision.py", ""),
    (46, "Setup engine", P, "engine/decision.py", "pullback, retest, continuation; no event-reaction setup"),
    (47, "Event engine", P, "fundamental/calendar.py", "calendar gate; history only from collection start"),
    (48, "Event kill switch and level reset", I, "engine/decision.py, engine/technical.py", ""),
    (49, "Signal persistence and path reconstruction", I, "v78/coverage.py, engine/thesis.py, engine/pipeline.py", "stability gate: price +-0.15 ATR, spread x2"),
    (50, "Evidence matrix instead of magic score", I, "engine/decision.py", ""),
    (51, "Tradeability gate", I, "engine/decision.py", ""),
    (52, "Entry engine", I, "engine/decision.py", ""),
    (53, "Stop-loss engine", I, "engine/decision.py", ""),
    (54, "Take-profit and expected move", I, "engine/decision.py", "no options expected move"),
    (55, "R:R and asymmetry", I, "engine/decision.py", "after costs"),
    (56, "Invalidation and trade management", I, "engine/decision.py", ""),
    (57, "Risk engine", I, "engine/portfolio.py", "paper sizing"),
    (58, "Candidates, factor concentration, one-trade priority", I, "engine/portfolio.py", ""),
    (59, "Scenario and time-horizon engine", P, "engine/decision.py", "qualitative scenarios, 24h primary horizon"),
    (60, "Prediction lock, ledger, path link", I, "prediction_ledger.py, v78/run.py", ""),
    (61, "Lifecycle + automatic path resolver", I, "v78/audit.py, engine/resolution.py", ""),
    (62, "Outcome resolution + path coverage", I, "engine/resolution.py", ""),
    (63, "Side-correct historical validation", I, "engine/resolution.py, sources/fxcm.py",
     "second 1-minute source decides an ambiguous hour only with the same events"),
    (64, "Cost, spread, slippage, gap layers", I, "engine/decision.py, engine/resolution.py", ""),
    (65, "MFE/MAE, timing, full-path audit", I, "engine/resolution.py", ""),
    (66, "Forecast accuracy", I, "stats/performance.py", ""),
    (67, "Trade performance", I, "stats/performance.py", ""),
    (68, "Decision quality, no trade, opportunity capture", P, "stats/errors.py", "no-trade opportunity capture not measured"),
    (69, "Error taxonomy, root cause, counterfactual", I, "stats/errors.py", ""),
    (70, "Performance statistics and sample guard", I, "stats/performance.py", ""),
    (71, "Event clusters, path segments, dependence", I, "engine/backtest.py, stats/performance.py", ""),
    (72, "Confidence calibration", I, "stats/performance.py", ""),
    (73, "Regime performance and decay", I, "stats/validation.py", ""),
    (74, "Benchmark, placebo, path-consistent control", I, "engine/backtest.py", ""),
    (75, "Ablation test", I, "stats/validation.py", ""),
    (76, "Robustness and sensitivity", I, "stats/validation.py", ""),
    (77, "Walk-forward, OOS, vintage control", I, "stats/validation.py", ""),
    (78, "Champion/challenger and acceptance gate", I, "stats/registry.py", ""),
    (79, "Learning loop", I, "stats/registry.py", "candidates only, never auto-promotion"),
    (80, "Model change log, impact, rollback, release", I, "stats/registry.py", ""),
    (81, "Every-run historical self-audit + gap recovery", I, "v78/run.py, v78/audit.py", ""),
    (82, "Review cadence", P, "scripts/review.py", "on demand; no scheduler on the phone"),
    (83, "V7.7.0 final run procedure", S, "v78/run.py", "superseded by module 145"),
    (84, "Performance dashboard and user output", I, "v78/report.py", ""),
    (85, "What did the model miss / what to change", I, "v78/report.py", ""),
    (86, "Market path archive - canonical role", I, "path_archive.py", ""),
    (87, "Archive schema and integrity", I, "path_archive.py", ""),
    (88, "Path continuity, gap detection, severity", I, "v78/coverage.py", ""),
    (89, "Backfill strategy and source failover", I, "v78/run.py", ""),
    (90, "Path resolution of triggers, SL, TP, sequence", I, "engine/resolution.py", ""),
    (91, "Event-to-path join", P, "fundamental/calendar.py", "event windows; no post-event segment statistics"),
    (92, "Between-run delta reconstruction", I, "v78/coverage.py", ""),
    (93, "Retention tiers and lifecycle", P, "path_archive.py", "1min kept as payloads; no automatic cold storage"),
    (94, "Archive quality states", I, "path_archive.py", ""),
    (95, "Change impact analysis - pre-change gate", I, "stats/registry.py", ""),
    (96, "Non-interference and regression matrix", I, "scripts/run_tests.py", ""),
    (97, "Change benefit proof class", I, "stats/registry.py", ""),
    (98, "Champion/challenger isolation", I, "stats/registry.py", ""),
    (99, "Reproducible run package", I, "v78/persist.py", ""),
    (100, "Final safety principle", I, "all", "no hindsight, no fabrication, no forced trade"),
    (101, "Model loading integrity gate", I, "v78/manifest.py", ""),
    (102, "Persistent state discovery, new-chat continuity", I, "v78/run.py", ""),
    (103, "No-silent-skip / full module execution trace", I, "v78/runstate.py", ""),
    (104, "Atomic-style persistence commit gate", I, "v78/persist.py", ""),
    (105, "Official run state machine", I, "v78/runstate.py", ""),
    (106, "Between-run delta mandate", I, "v78/coverage.py", ""),
    (107, "Rolling 14D working window", I, "v78/run.py", ""),
    (108, "Structured-data priority and source recovery", I, "v78/sources.py", ""),
    (109, "Timezone and timestamp normalization", I, "all adapters", "UTC everywhere; unknown zone = not used"),
    (110, "Cross-rate synchronization", I, "v78/quotes.py", "only direct quotes are used"),
    (111, "Current-quote retry and fallback", I, "v78/quotes.py", ""),
    (112, "Artifact recovery gate", P, "v78/run.py", "detects missing artifacts; recovery is manual from backups"),
    (113, "Run completion certificate", I, "v78/report.py", ""),
    (114, "Model fidelity across reloads", I, "v78/manifest.py", ""),
    (115, "V7.7 release / regression gate", I, "scripts/run_tests.py", ""),
    (116, "Concrete live source register + capability", I, "v78/sources.py", ""),
    (117, "Machine-readable live quote contract", I, "v78/quotes.py", ""),
    (118, "Atomic T0 snapshot and cross-pair skew", I, "v78/quotes.py", ""),
    (119, "Freshness and data-state gate 2.0", I, "v78/quotes.py", ""),
    (120, "Source conflict and failover matrix 2.0", I, "v78/quotes.py", ""),
    (121, "Live vs historical path separation", I, "engine/data.py", ""),
    (122, "Continuous market path ingestion", I, "sources/dukascopy.py, sources/fxcm.py, data_update.py", ""),
    (123, "Path coverage and gap certificate 2.0", I, "v78/coverage.py", ""),
    (124, "Raw payload provenance hash and replay", I, "raw_archive.py", ""),
    (125, "Environment capability gate", I, "v78/sources.py", ""),
    (126, "Mandatory pre-change improvement test gate", I, "stats/registry.py", ""),
    (127, "V7.7.1 release and promotion gate", I, "stats/registry.py", ""),
    (128, "V7.7.1 final run procedure", S, "v78/run.py", "superseded by module 145"),
    (129, "Global price source matrix", I, "v78/sources.py", ""),
    (130, "Web ticker observation adapter", N, "v78/sources.py", "deliberately not implemented: no web scraping; interface for API/broker sources only"),
    (131, "Dynamic widget / rendered-snapshot gate", N, "-", "no renderer in this runtime; nothing is fabricated"),
    (132, "Source observation classes", I, "v78/quotes.py", ""),
    (133, "Multi-source validation and outlier gate", I, "v78/quotes.py", ""),
    (134, "Market session and closed-market mode", P, "market_session.py, v78/quotes.py", "holidays not modelled"),
    (135, "User-facing current price contract", I, "v78/report.py", ""),
    (136, "Historical backfill source ladder", I, "v78/run.py, v78/coverage.py",
     "path: Dukascopy day > FXCM week > Dukascopy ticks > Twelve Data mid"),
    (137, "Between-run market path reconstruction", I, "v78/coverage.py", ""),
    (138, "Prediction state machine", I, "engine/thesis.py", ""),
    (139, "No-instant-flip gate", I, "engine/thesis.py", ""),
    (140, "Prediction persistence and hysteresis", I, "engine/thesis.py", ""),
    (141, "Top-3 continuity contract", I, "engine/portfolio.py, v78/report.py", ""),
    (142, "Full-model backtest and replay", I, "engine/backtest.py", ""),
    (143, "Data-layer benchmark before promotion", P, "v78/quotes.py", "source consistency measured per run"),
    (144, "Pre-change hold / stability gate", I, "stats/registry.py", ""),
    (145, "V7.8.0 final run procedure", I, "v78/run.py", ""),
]

MODULES = tuple(ModuleSpec(*row) for row in _MODULES)


def verify_manifest() -> list[str]:
    """Module manifest integrity (module 101): complete, contiguous, unique."""
    problems = []
    ids = [m.id for m in MODULES]

    if len(ids) != SPEC_MODULES:
        problems.append(f"manifest has {len(ids)} modules, specification has {SPEC_MODULES}")

    if ids != list(range(SPEC_MODULES)):
        problems.append("module ids are not the contiguous sequence 0..145")

    return problems


def fingerprint(params_fingerprint: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL_VERSION,
            "implementation": IMPLEMENTATION,
            "modules": [(m.id, m.status, m.ref) for m in MODULES],
            "params": params_fingerprint,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def docx_text(path: Path) -> str:
    """Plain text of a .docx without extra dependencies."""
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="replace")

    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def verify_document(path: Path) -> dict:
    """Check a model Word document against the manifest (modules 101, 114):
    version text, every module heading 0..145 present and in order."""
    result = {"path": str(path), "status": "MODEL LOAD COMPLETE", "problems": []}

    try:
        text = docx_text(path)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        result["status"] = "MODEL LOAD INCOMPLETE"
        result["problems"].append(f"document cannot be read: {exc}")
        return result

    if "V7.8.0" not in text:
        result["problems"].append("version V7.8.0 not found in the document")

    # headings are "N. TITLE IN CAPITALS"; searching each one after the
    # previous verifies presence AND sequence in one pass
    position = 0
    found = 0

    for module in MODULES:
        pattern = re.compile(rf"(?m)^\s*{module.id}\.\s+[A-Z\u00C0-\u017D][A-Z\u00C0-\u017D0-9\"/:,\-]+")
        match = pattern.search(text, position)

        if match is None:
            result["problems"].append(f"module {module.id} heading not found after module {module.id - 1}")
            continue

        found += 1
        position = match.end()

    result["modules_found"] = found

    if result["problems"]:
        result["status"] = "MODEL LOAD INCOMPLETE"

    return result
