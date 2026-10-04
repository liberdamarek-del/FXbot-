# FXBOT - instructions for Claude sessions

User: Czech, layperson; answer in Czech, plainly. Project rules: no live order execution (broker
read-only), no fabricated data, tests only via `python fxbot.py test` (isolated DB), no automatic
promotion of model changes without the walk-forward gate (`scripts/self_learn.py`), every change in
`docs/CHANGE_LOG.md`. Never disable TLS verification or bypass the proxy.

Scope (user's decision 2026-10-01): only the 12 live pairs (src/instruments.DEFAULT_ACTIVE). Do not
add markets.

## Jobs (routines fire into this session; user's decision 2026-10-02: hourly updates, learning several times a day)
- Update (weekdays every hour, the platform minimum): `git pull origin main`, `python scripts/aktualizace.py`
  (diagnostics + live signals/plans + this week's calendar + next central bank decisions -> data/live/stav.json).
  Then ArtifactData: `list denik` with out_dir -> `python scripts/aktualizace.py --denik <out_dir>` (the user's
  journal from the dashboard; snapshot in data/live, NOT in git - personal data), then get `stav/aktualni` for
  its version and set it with `file_path` data/live/stav.json and `if_version` (URL in learning/dashboard.json).
  Commit + push only when learning/forward_trades.json changed. Reply to the user with one short line, in detail
  only for a new signal, a diagnostics CHYBA, or a journal trade whose price is beyond its SL / TP.
- Friday signals (16:05 New York): same as Update (the decision is valid only from 16:00 New York,
  `signals_live.decision_ready`), then a Czech summary of the signals for the user.
- Learning (weekdays 07:40, 12:40, 17:40 Prague; Saturday 08:57 also downloads data first:
  `python scripts/fxcm_universe.py download && python scripts/fxcm_universe.py build`, `python scripts/fundamenty.py download`).
  FRED: `python -c "import sys; sys.path.insert(0,'scripts'); import signals_live; signals_live.refresh_rates()"`.
  Add 3-5 new, economically motivated experiments to `EXPERIMENTS` in `scripts/self_learn.py` (ideas queue
  below; never repeats of rejected ones in docs/UCENI_LOG.md; do not loosen the gate), run
  `python scripts/self_learn.py --profile mesicne` and `python scripts/self_learn.py`. If a champion changed:
  `python scripts/champion_report.py --profile mesicne`, `python scripts/pair_stats.py`, then the Update steps.
  Note in docs/CHANGE_LOG.md, commit and push. Tell the user briefly what was tried and what passed.
  The gate v3 (user's decision 2026-10-02 evening): return per drawdown (CAGR / max dd, open trades at daily
  closes) better by >= 10 % in both tests, >= 85 % of the champion's return, dd <= 30 %, >= 3 of 4 two-year
  blocks at least as good; the monthly profile keeps >= 2 wins a month. The user allowed changing the rules.
- Weekly research (user's specification 2026-10-04; part of the Saturday job, after the data download and
  before self_learn): `python scripts/tydenni_analyza.py` (the last completed FX week, the 12 pairs; `--pary` for
  any other list, `--rychle` without the walk-forward of combinations) -> docs/tydenni/<YYYY-Www>.md (Czech
  report: 0 data quality, 1 what happened, 2 each pair by day / UTC session with events and reactions, 3-8
  fundamental / technical / combination / fundamental+technical winners, failed signals, regime, 9 archive) and
  learning/tydenni/<week>.json.gz + udalosti.jsonl (tracked: the long-term record). Keep A) descriptive,
  B) attribution, C) predictive apart; labels NEOVĚŘENO / TIMESTAMP UNVERIFIED / FUNDAMENT UNVERIFIED /
  INSUFFICIENT SAMPLE / POSSIBLE OVERFIT; never fill missing data. Query a condition's weekly record:
  `python scripts/tydenni_analyza.py --dotaz "RSI14>50 & C>EMA20" --par EUR/USD --tf 1H --tydnu 20 [--rezim trend]`.
  Findings go into the model only as experiments through the gate. Method: docs/TYDENNI_VYZKUM.md.
- Start every job with the diagnostics (inside aktualizace.py); on CHYBA other than a known open item
  (docs/AUDIT_2026-10-02.md) do not publish signals, report it.

The learning state (champions) lives in `learning/` (tracked); market data in `data/` is not in git and is
re-downloaded by the scripts.

## Ideas queue for the learning runs
- (done 2026-10-01, R-014) The user's pivot method (classic pivots day/week/month, fades at P/R1/R2 and
  S1/S2, limit or confirmation, SMA50 with/against, rates filter, 1,080 variants, `scripts/pivot_lab2.py`,
  docs/PIVOTY2.md): no robust edge on the 12 pairs 2012-2026 - do not re-test the same family.
- (done 2026-10-02) H3 mark-to-market drawdown; H2 GBP/JPY rate extension (OECD immediate rate = SONIA for GBP).
- (done 2026-10-02, R-016) News: skip 5/7/10 days before a Fed/ECB/BoJ/BoE decision, weak tiers only, US NFP/CPI
  week, news shock > 0.75 ATR - all rejected (fewer trades -> lower annual return); half size before a decision:
  see docs/UCENI_LOG.md. docs/ZPRAVY.md: trades <= 7 days before a decision earn less in every period.
- (done 2026-10-02 morning, R-017) larger size after a decision week, weak tiers with carry, half before +
  1.5x after a decision - all rejected (do not repeat size tweaks around decisions).
- (done 2026-10-02, R-018) cross-asset lead-lag (gold, oil, copper, equities, VIX, yields -> next day),
  64 technical/fundamental/cross signals per pair with short-window walk-forward selection, per-pair adaptive
  filter of the rule (3/6/12 months) - nothing robust; do not repeat. docs/VYZKUM_POHYBY_2026-10-02.md.
- (done 2026-10-02 noon, R-019) exit in profit before a central bank decision: accepted in profile max,
  in mesicne rejected only on 2023-26 drawdown (28 % > 23 %). Next idea there: the same exit with smaller
  weak-tier margins or vol sizing; exit only for the strong tiers. Rejected: always exit, risk vs S&P 5d,
  EUR/GBP tier without rates.
- (done 2026-10-02 afternoon, R-020) literature anomalies (FOMC day, fixes, home hours, month-end
  rebalancing, dollar carry, momentum, value) and gate rounds 8-9 - all rejected; docs/ANOMALIE.md. Open
  question for the user: monthly profile with exit in profit before decisions + margin cap 15 %.
- (done 2026-10-02 evening, R-021) gate v3; exit in profit before a central bank decision now in BOTH
  profiles (live). Rejected: 3 targets, knife filter, daily strong tiers, half size / cap 15 % before decisions.
- (done, R-022) exits in profit before US NFP/CPI or on Fridays - rejected.
- (done, R-023) exit before SNB / RBA decisions too - rejected (only the big four banks matter).
- (done 2026-10-02 night, R-024/R-025, docs/OBCHODNIK.md) trader's logic: scale-in, confirmation entry, one bet per
  currency, targets 0.5/0.6/1.0 ATR, stop 5 ATR / on the close, 30 days, decaying target, Thursday entries,
  strongest tier as trend trader, 6/12-month rate confirmation, drawdown brake, BIS inflation, weekend gaps,
  post-decision drift - all rejected; do not repeat these families.
- (done 2026-10-04, R-026) macro: BIS CPI (all 8, macro.json "cpi_bis") and unemployment (all 8 incl. Eurostat
  EU27 / FRED CHF, NZD) as confirmations, accelerating rate divergence, size by rate change, vol sizing in the
  monthly profile under v3 - all rejected.
- Next (new families only): BoC dates (history not on the site; try archived press releases), RBNZ (403);
  BoE dates 8/2015-12/2016 missing; a different entry family with the same rate filter (weekly bars, Friday
  intraday path) only with an economic reason first; forward test review after 4+ weeks of live trades.

