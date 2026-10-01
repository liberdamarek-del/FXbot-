# Moduly 0-145: stav implementace

Generovano z `src/v78/manifest.py` (`python fxbot.py verify-model --list`).

| # | modul | stav | kde v kodu | poznamka |
|---|---|---|---|---|
| 0 | Main task and allowed decisions | implementovano | `engine/decision.py` |  |
| 1 | Architecture and precedence | implementovano | `engine/decision.py, v78/run.py` |  |
| 2 | Model units, source of truth, persistence | implementovano | `prediction_ledger.py, path_archive.py, v78/runstate.py` |  |
| 3 | Evidence taxonomy | implementovano | `engine/evidence.py` |  |
| 4 | Anti-hindsight and immutability | implementovano | `prediction_ledger.py, fundamental/store.py` |  |
| 5 | Absolute verification bans | implementovano | `all adapters` | missing data is reported, never estimated |
| 6 | Causal reasoning under machine control | castecne | `engine/decision.py` | hypotheses are built from evidence templates, not free reasoning |
| 7 | Output discipline | implementovano | `v78/report.py` |  |
| 8 | Live data + historical backfill | implementovano | `v78/run.py, data_update.py, sources/dukascopy.py` |  |
| 9 | Source hierarchy, adapter register, provenance | implementovano | `v78/sources.py` |  |
| 10 | Snapshot T0, freshness, path continuity | implementovano | `v78/quotes.py, v78/coverage.py` |  |
| 11 | Price identity spot/futures/CFD/broker | implementovano | `v78/quotes.py` | public feeds are labelled, never shown as broker price |
| 12 | Side-correct execution | castecne | `engine/resolution.py` | historical path side-correct; live quote has no bid/ask without a broker adapter |
| 13 | Source conflict reconciliation | castecne | `v78/quotes.py` | few contemporaneous sources; overlap consistency and outlier gate |
| 14 | Data gap, backfill, recovery | implementovano | `v78/coverage.py, sources/dukascopy.py` |  |
| 15 | History, vintage, revisions | castecne | `fundamental/store.py` | revisions tracked from first collection; older vintages unknown |
| 16 | Data quality and confidence classes | implementovano | `engine/fundamental.py, engine/decision.py` |  |
| 17 | FX universe and driver map | castecne | `instruments.py` | 12 active pairs, 4 more on demand; CNH/CNY not supported |
| 18 | Macro engine | castecne | `fundamental/calendar.py` | releases used as event risk; no release-surprise model |
| 19 | Expectation gap and market pricing | castecne | `fundamental/calendar.py` | forecast/previous shown; actual values not in the free feed |
| 20 | Central bank engine | castecne | `engine/fundamental.py` | policy rate level and trend; no guidance/voting data |
| 21 | Rate repricing engine | implementovano | `engine/fundamental.py` | 2y (GBP 5y) differential change as the priced-path proxy; no OIS |
| 22 | Yield and curve engine | castecne | `fundamental/catalog.py` | 2y/10y for 6 currencies; CHF/NZD monthly only |
| 23 | Funding and liquidity engine | castecne | `engine/fundamental.py` | HY spread and stress index; no cross-currency basis |
| 24 | Carry engine | implementovano | `engine/fundamental.py` | volatility-adjusted policy differential |
| 25 | Positioning engine | implementovano | `fundamental/adapters.py, engine/fundamental.py` | CFTC TFF weekly |
| 26 | Options engine | nedostupne | `-` | no keyless options data source |
| 27 | Flow, fixing and reserve flows | nedostupne | `-` | no structured free flow data; fixes not modelled |
| 28 | Fiscal, trade and tariff engine | nedostupne | `-` | no structured free feed |
| 29 | China engine | nedostupne | `-` | CNH/CNY outside the universe; no structured China data |
| 30 | Commodity and oil engine | castecne | `engine/fundamental.py` | WTI/Brent with measured correlation; no metals feed |
| 31 | Risk and intermarket engine | implementovano | `engine/fundamental.py` | VIX, S&P 500, HY spread, measured pair beta |
| 32 | Geopolitical engine | nedostupne | `-` | no structured feed; shocks visible only as price/regime |
| 33 | Intervention engine | castecne | `engine/fundamental.py` | price context flag only (never evidence of intervention) |
| 34 | Causal chain engine | castecne | `engine/decision.py` | chain summarised as H1/H2/H3 from evidence clusters |
| 35 | Second-order and transmission | castecne | `engine/fundamental.py` | risk regime transmission via measured beta |
| 36 | Factor clustering and dependence | implementovano | `engine/evidence.py` |  |
| 37 | Competing hypotheses and counterforce | implementovano | `engine/decision.py` |  |
| 38 | Market reaction engine | castecne | `engine/decision.py` | price structure must confirm the mechanism |
| 39 | Correlation, divergence, confluence | castecne | `engine/fundamental.py` | confluence counted per cluster |
| 40 | Regime engine | implementovano | `engine/regime.py` |  |
| 41 | Regime transition / change-point | implementovano | `engine/regime.py` | volatility expansion + trend flip / shock |
| 42 | Technical multi-timeframe + path | implementovano | `engine/technical.py` | D1/H4/H1 decisions, 1min path for resolution |
| 43 | Level lifetime and structural reset | implementovano | `engine/technical.py` |  |
| 44 | Market microstructure | castecne | `engine/decision.py` | spread and tick activity only |
| 45 | Direction != entry | implementovano | `engine/decision.py` |  |
| 46 | Setup engine | castecne | `engine/decision.py` | pullback, retest, continuation; no event-reaction setup |
| 47 | Event engine | castecne | `fundamental/calendar.py` | calendar gate; history only from collection start |
| 48 | Event kill switch and level reset | implementovano | `engine/decision.py, engine/technical.py` |  |
| 49 | Signal persistence and path reconstruction | implementovano | `v78/coverage.py, engine/thesis.py, engine/pipeline.py` | stability gate: price +-0.15 ATR, spread x2 |
| 50 | Evidence matrix instead of magic score | implementovano | `engine/decision.py` |  |
| 51 | Tradeability gate | implementovano | `engine/decision.py` |  |
| 52 | Entry engine | implementovano | `engine/decision.py` |  |
| 53 | Stop-loss engine | implementovano | `engine/decision.py` |  |
| 54 | Take-profit and expected move | implementovano | `engine/decision.py` | no options expected move |
| 55 | R:R and asymmetry | implementovano | `engine/decision.py` | after costs |
| 56 | Invalidation and trade management | implementovano | `engine/decision.py` |  |
| 57 | Risk engine | implementovano | `engine/portfolio.py` | paper sizing |
| 58 | Candidates, factor concentration, one-trade priority | implementovano | `engine/portfolio.py` |  |
| 59 | Scenario and time-horizon engine | castecne | `engine/decision.py` | qualitative scenarios, 24h primary horizon |
| 60 | Prediction lock, ledger, path link | implementovano | `prediction_ledger.py, v78/run.py` |  |
| 61 | Lifecycle + automatic path resolver | implementovano | `v78/audit.py, engine/resolution.py` |  |
| 62 | Outcome resolution + path coverage | implementovano | `engine/resolution.py` |  |
| 63 | Side-correct historical validation | implementovano | `engine/resolution.py, sources/fxcm.py` | second 1-minute source decides an ambiguous hour only with the same events |
| 64 | Cost, spread, slippage, gap layers | implementovano | `engine/decision.py, engine/resolution.py` |  |
| 65 | MFE/MAE, timing, full-path audit | implementovano | `engine/resolution.py` |  |
| 66 | Forecast accuracy | implementovano | `stats/performance.py` |  |
| 67 | Trade performance | implementovano | `stats/performance.py` |  |
| 68 | Decision quality, no trade, opportunity capture | castecne | `stats/errors.py` | no-trade opportunity capture not measured |
| 69 | Error taxonomy, root cause, counterfactual | implementovano | `stats/errors.py` |  |
| 70 | Performance statistics and sample guard | implementovano | `stats/performance.py` |  |
| 71 | Event clusters, path segments, dependence | implementovano | `engine/backtest.py, stats/performance.py` |  |
| 72 | Confidence calibration | implementovano | `stats/performance.py` |  |
| 73 | Regime performance and decay | implementovano | `stats/validation.py` |  |
| 74 | Benchmark, placebo, path-consistent control | implementovano | `engine/backtest.py` |  |
| 75 | Ablation test | implementovano | `stats/validation.py` |  |
| 76 | Robustness and sensitivity | implementovano | `stats/validation.py` |  |
| 77 | Walk-forward, OOS, vintage control | implementovano | `stats/validation.py` |  |
| 78 | Champion/challenger and acceptance gate | implementovano | `stats/registry.py` |  |
| 79 | Learning loop | implementovano | `stats/registry.py` | candidates only, never auto-promotion |
| 80 | Model change log, impact, rollback, release | implementovano | `stats/registry.py` |  |
| 81 | Every-run historical self-audit + gap recovery | implementovano | `v78/run.py, v78/audit.py` |  |
| 82 | Review cadence | castecne | `scripts/review.py` | on demand; no scheduler on the phone |
| 83 | V7.7.0 final run procedure | nahrazeno modulem 145 | `v78/run.py` | superseded by module 145 |
| 84 | Performance dashboard and user output | implementovano | `v78/report.py` |  |
| 85 | What did the model miss / what to change | implementovano | `v78/report.py` |  |
| 86 | Market path archive - canonical role | implementovano | `path_archive.py` |  |
| 87 | Archive schema and integrity | implementovano | `path_archive.py` |  |
| 88 | Path continuity, gap detection, severity | implementovano | `v78/coverage.py` |  |
| 89 | Backfill strategy and source failover | implementovano | `v78/run.py` |  |
| 90 | Path resolution of triggers, SL, TP, sequence | implementovano | `engine/resolution.py` |  |
| 91 | Event-to-path join | castecne | `fundamental/calendar.py` | event windows; no post-event segment statistics |
| 92 | Between-run delta reconstruction | implementovano | `v78/coverage.py` |  |
| 93 | Retention tiers and lifecycle | castecne | `path_archive.py` | 1min kept as payloads; no automatic cold storage |
| 94 | Archive quality states | implementovano | `path_archive.py` |  |
| 95 | Change impact analysis - pre-change gate | implementovano | `stats/registry.py` |  |
| 96 | Non-interference and regression matrix | implementovano | `scripts/run_tests.py` |  |
| 97 | Change benefit proof class | implementovano | `stats/registry.py` |  |
| 98 | Champion/challenger isolation | implementovano | `stats/registry.py` |  |
| 99 | Reproducible run package | implementovano | `v78/persist.py` |  |
| 100 | Final safety principle | implementovano | `all` | no hindsight, no fabrication, no forced trade |
| 101 | Model loading integrity gate | implementovano | `v78/manifest.py` |  |
| 102 | Persistent state discovery, new-chat continuity | implementovano | `v78/run.py` |  |
| 103 | No-silent-skip / full module execution trace | implementovano | `v78/runstate.py` |  |
| 104 | Atomic-style persistence commit gate | implementovano | `v78/persist.py` |  |
| 105 | Official run state machine | implementovano | `v78/runstate.py` |  |
| 106 | Between-run delta mandate | implementovano | `v78/coverage.py` |  |
| 107 | Rolling 14D working window | implementovano | `v78/run.py` |  |
| 108 | Structured-data priority and source recovery | implementovano | `v78/sources.py` |  |
| 109 | Timezone and timestamp normalization | implementovano | `all adapters` | UTC everywhere; unknown zone = not used |
| 110 | Cross-rate synchronization | implementovano | `v78/quotes.py` | only direct quotes are used |
| 111 | Current-quote retry and fallback | implementovano | `v78/quotes.py` |  |
| 112 | Artifact recovery gate | castecne | `v78/run.py` | detects missing artifacts; recovery is manual from backups |
| 113 | Run completion certificate | implementovano | `v78/report.py` |  |
| 114 | Model fidelity across reloads | implementovano | `v78/manifest.py` |  |
| 115 | V7.7 release / regression gate | implementovano | `scripts/run_tests.py` |  |
| 116 | Concrete live source register + capability | implementovano | `v78/sources.py` |  |
| 117 | Machine-readable live quote contract | implementovano | `v78/quotes.py` |  |
| 118 | Atomic T0 snapshot and cross-pair skew | implementovano | `v78/quotes.py` |  |
| 119 | Freshness and data-state gate 2.0 | implementovano | `v78/quotes.py` |  |
| 120 | Source conflict and failover matrix 2.0 | implementovano | `v78/quotes.py` |  |
| 121 | Live vs historical path separation | implementovano | `engine/data.py` |  |
| 122 | Continuous market path ingestion | implementovano | `sources/dukascopy.py, sources/fxcm.py, data_update.py` |  |
| 123 | Path coverage and gap certificate 2.0 | implementovano | `v78/coverage.py` |  |
| 124 | Raw payload provenance hash and replay | implementovano | `raw_archive.py` |  |
| 125 | Environment capability gate | implementovano | `v78/sources.py` |  |
| 126 | Mandatory pre-change improvement test gate | implementovano | `stats/registry.py` |  |
| 127 | V7.7.1 release and promotion gate | implementovano | `stats/registry.py` |  |
| 128 | V7.7.1 final run procedure | nahrazeno modulem 145 | `v78/run.py` | superseded by module 145 |
| 129 | Global price source matrix | implementovano | `v78/sources.py` |  |
| 130 | Web ticker observation adapter | nedostupne | `v78/sources.py` | deliberately not implemented: no web scraping; interface for API/broker sources only |
| 131 | Dynamic widget / rendered-snapshot gate | nedostupne | `-` | no renderer in this runtime; nothing is fabricated |
| 132 | Source observation classes | implementovano | `v78/quotes.py` |  |
| 133 | Multi-source validation and outlier gate | implementovano | `v78/quotes.py` |  |
| 134 | Market session and closed-market mode | castecne | `market_session.py, v78/quotes.py` | holidays not modelled |
| 135 | User-facing current price contract | implementovano | `v78/report.py` |  |
| 136 | Historical backfill source ladder | implementovano | `v78/run.py, v78/coverage.py` | path: Dukascopy day > FXCM week > Dukascopy ticks > Twelve Data mid |
| 137 | Between-run market path reconstruction | implementovano | `v78/coverage.py` |  |
| 138 | Prediction state machine | implementovano | `engine/thesis.py` |  |
| 139 | No-instant-flip gate | implementovano | `engine/thesis.py` |  |
| 140 | Prediction persistence and hysteresis | implementovano | `engine/thesis.py` |  |
| 141 | Top-3 continuity contract | implementovano | `engine/portfolio.py, v78/report.py` |  |
| 142 | Full-model backtest and replay | implementovano | `engine/backtest.py` |  |
| 143 | Data-layer benchmark before promotion | castecne | `v78/quotes.py` | source consistency measured per run |
| 144 | Pre-change hold / stability gate | implementovano | `stats/registry.py` |  |
| 145 | V7.8.0 final run procedure | implementovano | `v78/run.py` |  |

Soucty: implementovano 110, castecne 27, nedostupne 7, nahrazeno modulem 145: 2
