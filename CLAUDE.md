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
  The gate (since 2026-10-02): drawdown with open trades at daily closes, gain in both tests AND at least as
  good in >= 3 of the 4 two-year blocks (many experiments a week -> guard against luck).
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
- Next: macro trends (CPI y/y, unemployment; OECD SDMX in data/research/fundamenty/macro.json - JPY CPI ends
  2021, AUD monthly only from 2025, EUR/CHF/NZD unemployment missing: find sources first, e.g. Eurostat, e-Stat);
  meeting dates of SNB, RBA, BoC, RBNZ (sources reachable except RBNZ); BoE dates 8/2015-12/2016 missing;
  exit or tighten the stop before a decision instead of skipping the entry; trades after a decision in the
  entry week (better in 2023-26 only); position size by distance to the next decision.

