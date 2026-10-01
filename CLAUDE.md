# FXBOT - instructions for Claude sessions

User: Czech, layperson; answer in Czech, plainly. Project rules: no live order execution (broker
read-only), no fabricated data, tests only via `python fxbot.py test` (isolated DB), no automatic
promotion of model changes without the walk-forward gate (`scripts/self_learn.py`), every change in
`docs/CHANGE_LOG.md`. Never disable TLS verification or bypass the proxy.

Scope (user's decision 2026-10-01): only the 12 live pairs (src/instruments.DEFAULT_ACTIVE). Do not
add markets.

## Weekly jobs
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
- The user's own method (daily classic pivot points, entries at pivot resistance / support on the daily
  chart, e.g. shorts EUR/CHF ~0.947 and USD/JPY 158.33 on 2026-10-01): implement pivot entries in
  `scripts/profit_deep.py` and test as a separate candidate through the same walk-forward gate
  (earlier test R-004 / docs/PIVOTY.md: classic pivots + SMA50 had no robust edge 2013-2026).

