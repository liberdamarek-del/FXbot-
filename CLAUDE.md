# FXBOT - instructions for Claude sessions

User: Czech, layperson; answer in Czech, plainly. Project rules: no live order execution (broker
read-only), no fabricated data, tests only via `python fxbot.py test` (isolated DB), no automatic
promotion of model changes without the walk-forward gate (`scripts/self_learn.py`), every change in
`docs/CHANGE_LOG.md`. Never disable TLS verification or bypass the proxy.

Scope (user's decision 2026-10-01): only the 12 live pairs (src/instruments.DEFAULT_ACTIVE). Do not
add markets.

System memory (user's request 2026-10-07): read `docs/STAV_PROJEKTU.md` first - data flow, module status
(HOTOVO/OVĚŘENO, ROZPRACOVÁNO, BLOKOVÁNO, NEOVĚŘENO, CHYBA), open items - and update it after every significant
change. Work as a system architect: observe -> understand -> connect information -> analyse -> design ->
implement -> test -> evaluate; before a change list the affected parts (simulator, account, gate, live signals,
dashboard, forward test, diagnostics) and verify all of them afterwards. Never repeat a computation or test
without a reason; never fill missing data (NEOVĚŘENO).

Position size (user's decision 2026-10-07, R-037, docs/RIZIKO.md): the live dashboard sizes every trade by its
stop loss - the stop costs at most the user's chosen share of the account (default 5 %, weak tiers 30 % of it;
weights in `learning/riziko.json` from `python scripts/riziko_lab.py --stupne`, chosen walk-forward). The
signals themselves (entry, targets, stop) are the gate-tested champion's.

Heuristic model (user's request 2026-10-07, R-038, docs/HEURISTIKY.md): `scripts/heuristiky.py` is a separate
information layer - 5,760 measurable rules (57 template families x params x 12 pairs x 1D / 4H, per pair and all pairs)
with statuses AKTIVNÍ / SLABÁ / NEOVĚŘENÁ / NEFUNKČNÍ / OVERFIT/NESTABILNÍ, an append-only live prediction ledger
(learning/heuristiky/predikce|vyhodnoceni/<day>.jsonl, hash chain - never edit or delete lines) and self-evaluation.
Keep STATISTICKÁ PRAVDĚPODOBNOST (out-of-sample win rate) and HEURISTICKÝ ODHAD (subjective confluence) apart; agreement
with the main model never raises confidence unless the history shows it adds value. It never changes the main model's
signals; a heuristic reaches the model only as a gate experiment. A heuristics CHYBA in the diagnostics (ledger chain)
does not block the main signals but must be reported.

## Jobs (routines fire into this session; user's decision 2026-10-08: one update a day (was hourly, the weekly usage
limit); 2026-10-06: learning 2x a week)
Reports to the user (user's decision 2026-10-06): short and plain - signals, the user's trades, the model's trades
and real improvements of the model. Rejected experiments at most one sentence, no gate details unless asked.
- Update (weekdays once a day at 17:07 New York, right after the daily close; R-041): `git pull origin main`, `python scripts/aktualizace.py`
  (diagnostics + live signals/plans + this week's calendar + next central bank decisions -> data/live/stav.json).
  Then ArtifactData: `list denik` with out_dir -> `python scripts/aktualizace.py --denik <out_dir>` (the user's
  journal from the dashboard; snapshot in data/live, NOT in git - personal data), then get `stav/aktualni` for
  its version and set it with `file_path` data/live/stav.json and `if_version` (URL in learning/dashboard.json).
  aktualizace.py also runs the heuristic layer (new predictions at fresh closes, evaluations, stav `heuristiky`).
  Commit + push when learning/forward_trades.json or learning/heuristiky/ changed (the ledger must survive the
  container). Reply to the user with one short line, in detail only for a new signal, a diagnostics CHYBA, a
  journal trade whose price is beyond its SL / TP, or a journal central bank warning (it comes two trading days
  ahead, because the run is after the close; heuristic predictions: counts only, they are information).
  Heuristics with one run a day: every 1D bar, of the 4H bars only the one closing 17:00 New York (by design, not a
  missed update). Do not add more runs without the user's consent (usage limit).
- Friday signals (16:05 New York): same as Update (the decision is valid only from 16:00 New York,
  `signals_live.decision_ready`), then a Czech summary of the signals for the user (size by risk: margin and loss
  at the stop in % of the account at the default risk, stav signaly[].riziko). The decision uses the Friday
  up to 16:00 New York (`decision_cut`), exactly as the backtest and the learning (`Rule.decide_h=1`, audit
  2026-10-04); a run after 16:00 (also the 23:07 Prague update) decides the same. Keep `signals_live.DECIDE_H`
  and the champions' `decide_h` equal (diagnostics: CHYBA otherwise).
- Learning (Wednesday 17:40 and Saturday 08:57 Prague - user's decision 2026-10-06, was 3x every weekday;
  Saturday also downloads data first:
  `python scripts/fxcm_universe.py download && python scripts/fxcm_universe.py build`, `python scripts/fundamenty.py download`,
  then `python scripts/heuristiky.py prepocet` - the heuristic registry with the new data, statuses, docs/heuristiky_vysledky.md;
  mention status changes of AKTIVNÍ rules in the report).
  FRED: `python -c "import sys; sys.path.insert(0,'scripts'); import signals_live; signals_live.refresh_rates()"`.
  Add 3-5 new, economically motivated experiments to `EXPERIMENTS` in `scripts/self_learn.py` (ideas queue
  below; never repeats of rejected ones in docs/UCENI_LOG.md; do not loosen the gate), run
  `python scripts/self_learn.py --profile mesicne` and `python scripts/self_learn.py`. If a champion changed:
  `python scripts/champion_report.py --profile mesicne`, `python scripts/pair_stats.py`,
  `python scripts/riziko_lab.py --stupne` (risk weights + table; diagnostics warn otherwise), then the Update steps.
  Note in docs/CHANGE_LOG.md, commit and push. Tell the user briefly what was tried and what passed.
  The gate v3 (user's decision 2026-10-02 evening): return per drawdown (CAGR / max dd, open trades at daily
  closes) better by >= 10 % in both tests, >= 85 % of the champion's return, dd <= 30 %, >= 3 of 4 two-year
  blocks at least as good; the monthly profile keeps >= 2 wins a month (margins fitted with >= 2.0 on the
  selection years, the test tolerates 1.8). The user allowed changing the rules. A new rule option must also
  be implemented in signals_live (diagnostika.live_unsupported lists what the live run supports).
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
  Bridge to the model (R-028, scripts/vyzkum_most.py): research filter / boost and event-day add-on as gate
  experiments (cfg `vyzkum_filtr`, `vyzkum_udalosti`; selection per gate split, no look-ahead); live the research
  is information only (stav pary[].vyzkum, signal vyzkum votes, forward test vyzkum_pro / vyzkum_proti, event
  notes, dashboard section "Týdenní výzkum trhu"). Statistics are excess over the pair's average of the window.
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
- (done 2026-10-04, R-028) research bridge: veto / half / boost by the research conditions, event-day add-on -
  all rejected. Re-test them once a quarter with the new data as new names (e.g. `vyzkum_udalosti_2027Q1`), never
  every week (repeated tests of the same idea inflate lucky passes); after 8+ closed forward trades compare the
  trades the research supported vs opposed (forward_trades.json vyzkum_pro / vyzkum_proti).
- (done 2026-10-04, R-029, docs/AUDIT_2026-10-04.md) code audit: live decision time (16:00 New York) in the
  backtest, ESMA leverage 1:20 for AUD/NZD pairs, causal weekly indicators, forward test = backtest. Round 25
  (leverage: same position volume / minimum target in price) through the gate. Open for the user: deciding right
  before the close instead of 16:00 (historically +8-15 points a year, the last 10 minutes NEOVĚŘENO).
- Re-validation (from 2027-04, audit R-029: about 5 % of pure-noise changes pass gate v3): check every accepted
  component of the champions (exit before decisions, stop 4 ATR, RSI(3) < 15, vol sizing) only on the data after its
  acceptance (2026-10 onwards) - that is truly new data; report, change the champion only through the gate.
- (done 2026-10-05, R-030, docs/INTRADAY.md) intraday: 300 hourly variants, walk-forward LightGBM 1-24 h, FXCM minute
  data 2016-2026 (night scalper, round numbers, London open range, spikes, NFP/CPI) - gross edges exist, none survives
  retail costs; round 26 (no minimum target, RSI2 < 10, daily decisions) rejected. Do not repeat these families with
  retail costs; re-test the night scalper / hourly ML only with a real ECN account cost (< 0.3 pip incl. commission)
  and automatic execution (the project does not send orders).
- (done 2026-10-05, R-031, docs/HAZARD.md) gambling systems: martingale / anti / d'Alembert / Fibonacci as bet sizing
  (round 27, cfg `sazeni`) and a grid / martingale robot - all rejected; Kelly says the model already bets near the
  growth optimum. Do not repeat bet-sizing-by-streak families.
- (done 2026-10-05 morning, R-032) round 28: 2-year yields as confirmation (weak / all tiers), 2-month rate window,
  no trades over the year end - all rejected.
- (done 2026-10-05 noon, R-033) round 29: at most 5 / 7 open trades in the account, pause 2 / 4 weeks after a stop
  in the pair - all rejected (do not repeat open-trade caps or post-stop pauses).
- (done 2026-10-05 afternoon, R-034) round 30: the bought currency's own rate not falling (weak / all tiers), both
  legs of the divergence - all rejected (too few trades; do not repeat rate-decomposition confirmations).
- (done 2026-10-06 morning, R-035) round 31: weekly RSI(2) < 10 as an extra entry (strong / all tiers), exit once
  RSI(2) > 70 - all rejected (more but weaker trades; the target already takes the reversion). The weekly entry
  was strong in max 2023-26 only (return per drawdown 1.58 vs 0.70) - not a reason to retest it before 2027-04.
- (done 2026-10-07, R-039) round 32: no new trade in a volatility shock of the pair (ATR rank > 90 % / 80 % of 250
  days), exit when the 3-month rate change turns against the trade - all rejected (the rate-turn exit helped
  2019-22 and hurt 2023-26; do not retest before 2027-04 re-validation).
- (done 2026-10-11, R-042) round 33: without the weakest tier (rate divergence 0), deeper pullback RSI(2) < 3 in the
  weak tiers / only the weakest tier - all rejected (do not retest tier removal or stricter weak-tier pullbacks).
- Next (new families only): BoE announcement days 2015-05/06/07 (stored = vote day? R-033, NEOVĚŘENO); BoC dates (history not on the site; try archived press releases), RBNZ (403);
  BoE dates 8/2015-12/2016 missing; a different entry family with the same rate filter (Friday intraday path) only
  with an economic reason first; forward test review after 4+ weeks of live trades.

