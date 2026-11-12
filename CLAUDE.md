# FXBOT - instructions for Claude sessions

User: Czech, layperson; answer in Czech, plainly. Project rules: no live order execution (broker
read-only), no fabricated data, tests only via `python fxbot.py test` (isolated DB), no automatic
promotion of model changes without the walk-forward gate (`scripts/self_learn.py`), every change in
`docs/CHANGE_LOG.md`. Never disable TLS verification or bypass the proxy.

Claude Code hooks (R-053, `.claude/settings.json`, `.claude/hooks/fxbot_hooky.py`): they block direct edits of the
hash-chained ledgers (learning/heuristiky/predikce|vyhodnoceni, learning/registr_pokusu/registr.jsonl) and of the vault
(learning/trezor.json), check syntax after every edit of a .py / .json / .jsonl file, and run `python fxbot.py test` before a
`git commit` / `git push` that contains .py changes. When a hook blocks, fix the cause or report it to the user - never work
around it (other tools, scripts, renamed paths). The ideas queue of the learning runs is in docs/FRONTA_POKUSU.md.

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
signals themselves (entry, targets, stop) are the gate-tested champion's. Limit on one currency (user's decision 2026-10-22, R-052, docs/RIZIKO.md
ch. 7): the dashboard adds up the stop losses of trades betting on the same currency in the same direction (the user's open
journal trades + the cards above) and caps them at 1.5 x the one-trade risk (adjustable); the journal requires stop loss and margin.
Dashboard only - not a model change; the value was chosen up front, not fitted (freeze R-047).

Heuristic model (user's request 2026-10-07, R-038, docs/HEURISTIKY.md): `scripts/heuristiky.py` is a separate
information layer - 5,760 measurable rules (57 template families x params x 12 pairs x 1D / 4H, per pair and all pairs)
with statuses AKTIVNÍ / SLABÁ / NEOVĚŘENÁ / NEFUNKČNÍ / OVERFIT/NESTABILNÍ, an append-only live prediction ledger
(learning/heuristiky/predikce|vyhodnoceni/<day>.jsonl, hash chain - never edit or delete lines) and self-evaluation.
Keep STATISTICKÁ PRAVDĚPODOBNOST (out-of-sample win rate) and HEURISTICKÝ ODHAD (subjective confluence) apart; agreement
with the main model never raises confidence unless the history shows it adds value. It never changes the main model's
signals; a heuristic reaches the model only as a gate experiment. A heuristics CHYBA in the diagnostics (ledger chain)
does not block the main signals but must be reported.

ARCHITECTURE (user's request 2026-10-20, R-048, architektura-v2 phase 1): the live core is `src/core` (ta, rates, market, paths,
levels) + scripts/{signals_live, aktualizace, diagnostika, portfolio_sim, profit_deep}; it must NOT import the research
labs (profit_lab, profit_lab2, winrate_lab, pivot_lab, strategy_mining) - `test_h1_core.py` checks it, and that results stay
bit for bit equal to `tests/fixtures/jadro_zlaty.json`. Entry, target and stop of every trade are computed ONLY by
`src/core/levels.py` (backtest = live plan = forward test, from the fill price incl. half the spread; `test_h2_levels.py`).
V7.8.0 code and uncalled labs are in `archive/` (table in `archive/README.md`); `python fxbot.py` only has `test`.

RESEARCH HYGIENE (user's request 2026-10-20, R-049, architektura-v2 phase 2): (1) every trial is registered BEFORE it runs in
`learning/registr_pokusu/registr.jsonl` (append-only hash chain; `python scripts/registr_pokusu.py registruj ...`: hypothesis,
ECONOMIC REASON, parameters, data / test are mandatory); `self_learn.py` does not run an unregistered trial and records every
result; a trial without a record does not count. 332 logged trials were imported. (2) DSR / PBO (`src/core/statistika.py`,
`scripts/faze2_analyza.py`) are computed from the number of trials in the registry. (3) VAULT: trading days from 2026-10-01 on
are locked (`learning/trezor.json`, docs/TREZOR.md): `market.series()` cuts them off, research must not read them; open only
once and only with the user's explicit consent (`scripts/trezor.py otevri --souhlas ...`). (4) `python scripts/kontrola_histdata.py`
(16 HistData pairs, report only, NOT a selection criterion) after every change of the champion. Registry / vault CHYBA in the
diagnostics does not block the main signals but must be reported.

FREEZE OF NEW TRIALS (user's decision 2026-10-20, R-047, branch architektura-v2 phase 0; docs/CHANGE_LOG.md): the test
years 2019-26 are worn out (332 logged trials, 8 accepted). Do NOT add experiments to `EXPERIMENTS` in
scripts/self_learn.py and do not run new gate trials from any lab script until the user lifts the freeze
(learning/zmrazeni_pokusu.json; `self_learn.py` refuses to run with a new name, diagnostics WARN, test_g0_zmrazeni).
Learning runs still download data, refresh rates / fundamentals / heuristics / weekly research and re-evaluate the
champion on the new data - but add no experiments. The ideas queue (docs/FRONTA_POKUSU.md) is parked. The champion stays unchanged and
is only watched in the forward test.

GITHUB OPERATION (user's decision 2026-10-22, R-050, docs/GITHUB_PROVOZ.md): the same jobs also run on GitHub Actions
(.github/workflows/fxbot-denni.yml, fxbot-uceni.yml) and publish the dashboard on GitHub Pages (scripts/web_stranka.py; the
user's journal lives only in his browser there). Mode in learning/provoz/github.json: "stin" = GitHub commits nothing (the
Claude routines below stay the only writer of main), "ostry" = GitHub is the only writer and the Claude routines must be
switched off first (two writers would break the append-only heuristics ledger). SINCE 2026-11-12 (R-054, user's decision)
the mode is "ostry": GitHub Actions is the ONLY writer of learning/ and the job outputs in docs/; all FXBOT Claude scheduled
tasks are switched off. A Claude session must not run the jobs below and commit their outputs (learning/forward_trades.json,
learning/heuristiky/, learning/provoz/, champions) - code and documentation changes are fine. To go back: set "stin" first,
then switch the Claude tasks on. The user's dashboard is https://liberdamarek-del.github.io/FXbot-/ (the claude.ai artifact
is no longer updated). web/prehled.html serves both the claude.ai artifact and Pages.
R-051 (user's decision 2026-10-22): in the "ostry" mode the daily workflow also refreshes every hour Monday to Friday (cron
"12 * * * 1-5" UTC) and runs send phone notifications via ntfy.sh (secret FXBOT_NTFY_TEMA; scripts/github_beh.py). Learning
stays Wednesday + Saturday (more frequent learning adds nothing while trials are frozen and the vault is closed).

## Jobs (user's decision 2026-10-11, R-044: every routine starts a FRESH session - firing into the long main
conversation cost ~300k tokens per step; 2026-10-08: one update a day (was hourly, the weekly usage limit);
2026-10-06: learning 2x a week)
SWITCHED OFF since 2026-11-12 (R-054): GitHub Actions runs these jobs ("ostry" mode above). The description stays as the
reference for what the workflows do and for a return to the Claude routines.
Since 2026-10-11 the four routines fire into a small dispatcher session ("FXBOT dispečer rutin", Sonnet), which only
calls create_session with the repository attached and the task text (docs/RUTINY.md): a routine created by the
create_trigger tool has no repository and cannot push, the phone UI cannot attach one. The old routines that fired
into the main session are switched off. A worker session has the repository but no data/. `python scripts/rutina.py denni` (daily update / Friday signals: FRED rates + aktualizace; without price
history it runs lean, FXBOT_LEHKY=1 - the diagnostics accept the missing FXCM history, the research lock is the tracked
learning/vyzkum_zamek.json) or `python scripts/rutina.py uceni` (learning: FXCM history of the 12 pairs `--jen-12`,
~1.5 min, bit-identical to the full data; fundamentals; rates). `rutina.py denik <dir>` imports the journal,
`rutina.py souhrn` prints the short summary. Each run writes learning/provoz/posledni_beh.json - commit it with the
rest of learning/ and docs/ (never data/), git identity Claude <noreply@anthropic.com>. Exploration (user's request
2026-10-11): at the end of each learning run at most one bounded step from docs/VYZKUM_FRONTA.md (rules there).
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
  PAUSED since 2026-10-20 (R-047, see FREEZE OF NEW TRIALS above) - skip the experiment steps; the HistData control `python scripts/kontrola_histdata.py` only when the champion changed; `python scripts/self_learn.py`
  (both profiles) only re-evaluates the champion on the new data. Originally: add 3-5 new, economically motivated experiments to `EXPERIMENTS` in `scripts/self_learn.py` (ideas queue
  in docs/FRONTA_POKUSU.md - read it in full before choosing experiments; never repeats of rejected ones in docs/UCENI_LOG.md; do not loosen the gate), run
  `python scripts/self_learn.py --profile mesicne` and `python scripts/self_learn.py`. If a champion changed:
  `python scripts/champion_report.py --profile mesicne`, `python scripts/pair_stats.py`,
  `python scripts/riziko_lab.py --stupne` (risk weights + table; diagnostics warn otherwise), then the Update steps.
  Note in docs/CHANGE_LOG.md, commit and push. Tell the user briefly what was tried and what passed.
  The gate v3 (user's decision 2026-10-02 evening): return per drawdown (CAGR / max dd, open trades at daily
  closes) better by >= 10 % in both tests, >= 85 % of the champion's return, dd <= 30 %, >= 3 of 4 two-year
  blocks at least as good; the monthly profile keeps >= 2 wins a month (margins fitted with >= 2.0 on the
  selection years, the test tolerates 1.8). The user allowed changing the rules. A new rule option must also
  be implemented in signals_live (diagnostika.live_unsupported lists what the live run supports).
- Weekly research (PAUSED while the vault is closed, R-049: it reads prices only through `market.series()`, so it could only
  repeat weeks before 2026-10-01; skip `tydenni_analyza.py` until the user opens the vault) (user's specification 2026-10-04; part of the Saturday job, after the data download and
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
