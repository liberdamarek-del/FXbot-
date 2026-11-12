# Fronta nápadů pro učení (přesunuto z CLAUDE.md 2026-11-12, R-053)

_Text níže je beze změny přesunutý z `CLAUDE.md`, aby se do každého sezení Claude nenačítal (fronta je odložená,
dokud platí zmrazení R-047). Učení ji čte, až uživatel zmrazení zruší; zamítnuté rodiny se neopakují._

## Ideas queue for the learning runs (PARKED while the freeze R-047 is active)
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
- (done 2026-10-11, R-043, docs/VYZKUM_KRIVKA.md) round 34: relative yield curve veto (`curve_veto`: no trade when the
  bought currency's curve steepened, weak / all tiers) - rejected (helped 2023-26 drawdown 28 -> 19 %, hurt 2019-22);
  re-check only at the 2027-04 re-validation on data after 2026-10.
- (done 2026-10-17, R-046) round 35: rate-divergence window 4 months (weak / all tiers) - rejected (do not retest rate windows 2/4/6).
- Next (new families only): BoE announcement days 2015-05/06/07 (stored = vote day? R-033, NEOVĚŘENO); BoC dates (history not on the site; try archived press releases), RBNZ (403);
  BoE dates 8/2015-12/2016 missing; a different entry family with the same rate filter (Friday intraday path) only
  with an economic reason first; forward test review after 4+ weeks of live trades.
