# FXBOT - instructions for Claude sessions

User: Czech, layperson; answer in Czech, plainly. Project rules: no live order execution (broker
read-only), no fabricated data, tests only via `python fxbot.py test` (isolated DB), no automatic
promotion of model changes without the walk-forward gate (`scripts/self_learn.py`), every change in
`docs/CHANGE_LOG.md`. Never disable TLS verification or bypass the proxy.

Scope (user's decision 2026-10-01): only the 12 live pairs (src/instruments.DEFAULT_ACTIVE). Do not
add markets.

## Weekly jobs
- Start every job with `python scripts/diagnostika.py --online` (read-only); on CHYBA other than a
  known open item (docs/AUDIT_2026-10-02.md) do not publish signals, report it.
- Friday signals (`python scripts/signals_live.py`): Yahoo hourly + FRED rates -> `data/live/stav.json`
  and `learning/forward_trades.json` (model forward test). Then write the JSON to the dashboard
  database: Artifact URL and doc in `learning/dashboard.json` (ArtifactData: get `stav/aktualni` for
  its version, then set with `file_path` data/live/stav.json and `if_version`). Commit
  `learning/forward_trades.json`.
- Saturday learning: data first - `python scripts/fxcm_universe.py download && python scripts/fxcm_universe.py build`
  (FXCM hourly, ~3 min), `python -c "import sys; sys.path.insert(0,'scripts'); import signals_live; signals_live.refresh_rates()"`
  (FRED). Then add 3-5 new, economically motivated experiments to `EXPERIMENTS` in `scripts/self_learn.py`
  (not repeats of rejected ones in docs/UCENI_LOG.md), run `python scripts/self_learn.py` and
  `python scripts/self_learn.py --profile mesicne`; if a champion changed: `python scripts/champion_report.py --profile mesicne`,
  `python scripts/pair_stats.py` (pair ranking on the dashboard),
  `python scripts/signals_live.py` and update the dashboard. Note results in docs/UCENI_LOG.md (automatic)
  and docs/CHANGE_LOG.md; commit and push to main.

The learning state (champions) lives in `learning/` (tracked); market data in `data/` is not in git and is
re-downloaded by the scripts.

## Ideas queue for the Saturday learning
- (done 2026-10-01, R-014) The user's pivot method (classic pivots day/week/month, fades at P/R1/R2 and
  S1/S2, limit or confirmation, SMA50 with/against, rates filter, 1,080 variants, `scripts/pivot_lab2.py`,
  docs/PIVOTY2.md): no robust edge on the 12 pairs 2012-2026 - do not re-test the same family.
- (priority, from the audit 2026-10-02) H3: mark-to-market drawdown in `portfolio_sim.run_portfolio`
  (daily closes) and the gate on it, then re-fit the tier margins.
- (priority) H2: GBP rate fallback (Bank of England / BIS policy rate) when OECD lags >= 2 months.
- Central bank meeting / US CPI / NFP calendar (dates known in advance, history from 2012): do not
  enter, or smaller size, when a meeting of either currency is within N days.

