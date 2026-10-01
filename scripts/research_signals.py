"""Signal research lab: which simple technical and fundamental signals
predict the next 1 / 5 / 20 trading days better than a random direction -
with a protocol that cannot fool itself (modules 66, 74-80, 126, 144).

    python scripts/research_signals.py extract    # signal table 2014-2026 -> data/research/signals.pkl (~3 min)
    python scripts/research_signals.py discover   # DISCOVERY period only; locks the candidates
    python scripts/research_signals.py confirm    # locked candidates on the two untouched periods, ONCE

Why not tune the full model: one backtest run tests one rule set, and every
look at the result is a chance to fit noise. Here every signal is one
number per pair and day, evaluated as a plain trade (enter at the daily
close, exit h days later, BID/ASK-free mid prices minus a fixed retail cost
and the overnight financing), so dozens of ideas cost seconds - and the
protocol decides what may count:

1. DISCOVERY 2016-09 .. 2021-12 (FXCM): every signal, both directions, three
   horizons. A candidate needs |t| >= 3.0 for the NET result (about a
   Bonferroni bar for ~130 tests), the same sign in both halves of the
   period and a positive gross direction edge.
2. The candidates (signal, direction, horizon) are written to
   data/research/candidates.json with their SHA-256 BEFORE any other
   period is read. Nothing may be added later.
3. CONFIRM on data the selection never saw: EARLY 2014-01 .. 2016-08 (FXCM)
   and HOLDOUT 2022-01 .. 2026-09 (FXCM, from 2023-08 Dukascopy). A
   candidate passes with a positive net mean in BOTH periods and t >= 2.5
   on both together. Only a passed candidate may become a change proposal
   (docs/CHANGE_LOG.md) for the model - and then still needs the forward
   test.

Statistics: positions are taken every h-th trading day only (no overlapping
trades), all pairs of one day form one portfolio observation (pairs share
the USD and are not independent), t = mean / standard error over days.

Costs (assumption, documented in the report): typical retail spread per
pair + 0.4 pip slippage per round trip; financing = short-rate difference
(2y yields; CHF/NZD policy rates) minus 1 % p.a. broker markup on each side.
Gross = mid-price move only (random direction = 0).
"""

import json
import hashlib
import math
import pickle
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.series import PriceSeries  # noqa: E402  (loads .env first)
from src.fundamental.catalog import LONG_RATE, SHORT_RATE  # noqa: E402
from src.fundamental.store import load_series  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402
from src.path_archive import Bar  # noqa: E402

UTC = timezone.utc
RESEARCH = PROJECT_ROOT / "data" / "research"
SIGNALS_FILE = RESEARCH / "signals.pkl"
CANDIDATES_FILE = RESEARCH / "candidates.json"
ARCHIVES = {
    "early": PROJECT_ROOT / "data" / "early_fxcm" / "market_path.sqlite3",
    "oos": PROJECT_ROOT / "data" / "oos_fxcm" / "market_path.sqlite3",
    "main": PROJECT_ROOT / "data" / "market_path.sqlite3",
}
DUKASCOPY_FROM = int(datetime(2023, 8, 1, tzinfo=UTC).timestamp())
PERIODS = {
    "EARLY": (date(2014, 1, 1), date(2016, 8, 31)),
    "DISCOVERY": (date(2016, 9, 1), date(2021, 12, 31)),
    "HOLDOUT": (date(2022, 1, 1), date(2026, 9, 30)),
}
HORIZONS = (1, 5, 20)
# typical retail spread in pips (incl. broker markup), the same in all periods
SPREAD_PIPS = {"EUR/USD": 0.8, "USD/JPY": 0.9, "GBP/USD": 1.2, "USD/CHF": 1.4, "AUD/USD": 1.0, "USD/CAD": 1.5,
               "NZD/USD": 1.5, "EUR/JPY": 1.5, "GBP/JPY": 2.5, "EUR/GBP": 1.2, "EUR/CHF": 1.6, "AUD/JPY": 1.6}
SLIPPAGE_PIPS = 0.4
FINANCING_MARKUP = 1.0      # % p.a. the broker keeps on each side of the swap
# pre-specified economic roles (a hypothesis to test, not a rule)
RISK_BETA = {"AUD": 1.0, "NZD": 1.0, "CAD": 0.5, "JPY": -1.0, "CHF": -1.0}
OIL_LINK = {"CAD": 1.0}
MAX_GAP_DAYS = 9           # longer holes than holidays (max 7 days) break returns and lookbacks
DISCOVERY_T = 3.0
CONFIRM_T = 2.5


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------

def _daily_bars(db: Path, symbol: str, source: str) -> list[Bar]:
    if not db.exists():
        return []

    connection = sqlite3.connect(db)

    try:
        rows = connection.execute(
            "SELECT ts, bo, bh, bl, bc, ao, ah, al, ac, volume, active, minutes FROM market_path "
            "WHERE instrument = ? AND timeframe = '1d' AND source_id = ? ORDER BY ts", (symbol, source)).fetchall()
    finally:
        connection.close()

    return [Bar(*row) for row in rows]


def stitched_daily(symbol: str) -> tuple[list[Bar], list[str]]:
    """One daily series 2013-2026: FXCM early archive, FXCM research archive,
    Dukascopy from 2023-08 (the sources differ by ~0.1 pip, measured)."""
    early = _daily_bars(ARCHIVES["early"], symbol, "FXCM_H1")
    oos = _daily_bars(ARCHIVES["oos"], symbol, "FXCM_H1")
    duka = {b.ts: b for b in _daily_bars(ARCHIVES["main"], symbol, "DUKASCOPY_H1")}
    duka.update({b.ts: b for b in _daily_bars(ARCHIVES["main"], symbol, "DUKASCOPY_M1")})
    first_oos = oos[0].ts if oos else DUKASCOPY_FROM
    bars, sources = [], []

    for part, label, keep in ((early, "FXCM", lambda b: b.ts < first_oos),
                              (oos, "FXCM", lambda b: b.ts < DUKASCOPY_FROM),
                              ([duka[k] for k in sorted(duka)], "DUKASCOPY", lambda b: b.ts >= DUKASCOPY_FROM)):
        for bar in part:
            if keep(bar):
                bars.append(bar)
                sources.append(label)

    return bars, sources


class Fundamentals:
    """Point-in-time currency values at a moment t (cached per currency and day)."""

    def __init__(self):
        self.series = {}
        self.cache = {}

    def _series(self, series_id: str):
        if series_id not in self.series:
            self.series[series_id] = load_series(series_id)
        return self.series[series_id]

    def value(self, series_id: str, t: int, days_ago: int = 0):
        s = self._series(series_id)
        now = s.asof(t)

        if now is None:
            return None

        if days_ago == 0:
            return now.value

        past = s.asof_date(t, now.obs_date - timedelta(days=days_ago))
        return past.value if past else None

    def currency(self, ccy: str, t: int) -> dict:
        key = (ccy, t // 86400)

        if key in self.cache:
            return self.cache[key]

        short_id = SHORT_RATE[ccy][0]
        out = {
            "short": self.value(short_id, t), "short_20": self.value(short_id, t, 28),
            "short_60": self.value(short_id, t, 84), "long": self.value(LONG_RATE[ccy], t),
            "long_20": self.value(LONG_RATE[ccy], t, 28), "policy": self.value(f"{ccy}.POLICY", t),
            "policy_6m": self.value(f"{ccy}.POLICY", t, 182), "cot_z": None, "cot_chg": None,
        }

        if ccy != "USD":
            history = self._series(f"COT.{ccy}.LEV_NET_PCT").history(t, 156)

            if len(history) >= 52:
                values = [h.value for h in history]
                mean = sum(values) / len(values)
                sd = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
                out["cot_z"] = (values[-1] - mean) / sd if sd > 0 else 0.0
                out["cot_chg"] = values[-1] - values[-5] if len(values) >= 5 else None
        else:
            out["cot_z"], out["cot_chg"] = 0.0, 0.0     # COT contracts are priced against USD

        self.cache[key] = out
        return out


def _diff(a, b):
    return None if a is None or b is None else a - b


def extract() -> None:
    RESEARCH.mkdir(parents=True, exist_ok=True)
    fund = Fundamentals()
    rows = []
    started = time.monotonic()

    for symbol in parse_symbols(None):
        instrument = get_instrument(symbol)
        bars, sources = stitched_daily(symbol)
        d1 = PriceSeries.from_bars(symbol, "1d", bars)
        cost = (SPREAD_PIPS[symbol] + SLIPPAGE_PIPS) * instrument.pip
        b, q = instrument.base, instrument.quote
        gap = [False] + [d1.ts[k] - d1.ts[k - 1] > MAX_GAP_DAYS * 86400 for k in range(1, len(d1))]

        for i in range(250, len(d1)):
            atr = d1.atr14[i]

            if not atr or atr <= 0 or any(gap[i - 59:i + 1]):
                continue

            t = d1.close_time(i)
            c = d1.close
            mom = lambda n: (c[i] - c[i - n]) / (atr * math.sqrt(n))
            hi20, lo20 = max(d1.high[i - 19:i + 1]), min(d1.low[i - 19:i + 1])
            prev_hi, prev_lo = max(d1.high[i - 20:i]), min(d1.low[i - 20:i])
            fb, fq = fund.currency(b, t), fund.currency(q, t)
            vix, vix_7 = fund.value("GLOBAL.VIX", t), fund.value("GLOBAL.VIX", t, 7)
            oil, oil_28 = fund.value("GLOBAL.BRENT", t), fund.value("GLOBAL.BRENT", t, 28)
            beta = RISK_BETA.get(b, 0.0) - RISK_BETA.get(q, 0.0)
            oil_link = OIL_LINK.get(b, 0.0) - OIL_LINK.get(q, 0.0)
            carry = _diff(fb["short"], fq["short"])
            carry_20 = _diff(fb["short_20"], fq["short_20"])
            carry_60 = _diff(fb["short_60"], fq["short_60"])
            long_diff = _diff(fb["long"], fq["long"])
            long_diff_20 = _diff(fb["long_20"], fq["long_20"])
            policy_trend = _diff(_diff(fb["policy"], fb["policy_6m"]), _diff(fq["policy"], fq["policy_6m"]))
            row = {
                "symbol": symbol, "t": t, "day": datetime.fromtimestamp(t, tz=UTC).date(), "source": sources[i],
                # technical (positive = base expected up if the signal works as trend)
                "MOM_1": (c[i] - c[i - 1]) / atr, "MOM_5": mom(5), "MOM_20": mom(20), "MOM_60": mom(60),
                "MOM_120": mom(120), "MOM_250": mom(250),
                "EMA20_DIST": (c[i] - d1.ema20[i]) / atr, "EMA50_DIST": (c[i] - d1.ema50[i]) / atr,
                "EMA200_DIST": (c[i] - d1.ema200[i]) / atr, "EMA50_200": (d1.ema50[i] - d1.ema200[i]) / atr,
                "RSI14": d1.rsi14[i] - 50.0 if d1.rsi14[i] is not None else None,
                "RANGE20_POS": (c[i] - lo20) / (hi20 - lo20) - 0.5 if hi20 > lo20 else None,
                "BREAKOUT_20": 1.0 if c[i] > prev_hi else -1.0 if c[i] < prev_lo else 0.0,
                # fundamental
                "CARRY": carry,
                "RATES_20D": _diff(carry, carry_20), "RATES_60D": _diff(carry, carry_60),
                "LONG_RATES_20D": _diff(long_diff, long_diff_20),
                "POLICY_TREND": policy_trend,
                "COT_Z": _diff(fb["cot_z"], fq["cot_z"]), "COT_4W": _diff(fb["cot_chg"], fq["cot_chg"]),
                "RISK_VIX_1W": None if vix is None or vix_7 is None or not beta else -(vix - vix_7) * beta,
                "RISK_VIX_LEVEL": None if vix is None or not beta else -(vix - 20.0) * beta,
                "OIL_20D": None if not oil or not oil_28 or oil <= 0 or oil_28 <= 0 or not oil_link
                else math.log(oil / oil_28) * oil_link,
                # modifiers (not directional)
                "ER20": d1.er20[i], "ATR_PCT": d1.atr_pct[i],
            }

            for h in HORIZONS:
                if i + h >= len(d1) or any(gap[i + 1:i + h + 1]):
                    continue

                days = (d1.ts[i + h] - d1.ts[i]) / 86400
                move = c[i + h] - c[i]
                fin = 0.0 if carry is None else carry / 100.0 * c[i] * days / 365.0
                markup = FINANCING_MARKUP / 100.0 * c[i] * days / 365.0
                row[f"exit_{h}"] = datetime.fromtimestamp(d1.close_time(i + h), tz=UTC).date()
                row[f"gross_{h}"] = move / atr
                row[f"long_{h}"] = (move - cost + fin - markup) / atr
                row[f"short_{h}"] = (-move - cost - fin - markup) / atr

            rows.append(row)

        print(f"{symbol}: {len(d1)} dennich svicek ({sources[0] if sources else '-'} .. "
              f"{sources[-1] if sources else '-'}), radku celkem {len(rows)} | {time.monotonic() - started:.0f} s",
              flush=True)

    SIGNALS_FILE.write_bytes(pickle.dumps(rows))
    print(f"ulozeno: {SIGNALS_FILE} ({len(rows)} radku)")


# ----------------------------------------------------------------------
# statistics
# ----------------------------------------------------------------------

SIGNALS = ("MOM_1", "MOM_5", "MOM_20", "MOM_60", "MOM_120", "MOM_250", "EMA20_DIST", "EMA50_DIST", "EMA200_DIST",
           "EMA50_200", "RSI14", "RANGE20_POS", "BREAKOUT_20", "CARRY", "RATES_20D", "RATES_60D", "LONG_RATES_20D",
           "POLICY_TREND", "COT_Z", "COT_4W", "RISK_VIX_1W", "RISK_VIX_LEVEL", "OIL_20D")


def in_period(row: dict, period: tuple[date, date], h: int) -> bool:
    first, last = period
    exit_day = row.get(f"exit_{h}")
    return exit_day is not None and first <= row["day"] and exit_day <= last


_SAMPLES: dict = {}


def sample(rows: list[dict], period: tuple[date, date], h: int) -> list[dict]:
    """Rows of every h-th trading day of the period (no overlapping trades)."""
    key = (id(rows), period, h)

    if key not in _SAMPLES:
        eligible = [r for r in rows if in_period(r, period, h)]
        chosen = set(sorted({r["day"] for r in eligible})[::h])
        _SAMPLES[key] = [r for r in eligible if r["day"] in chosen]

    return _SAMPLES[key]


def evaluate(rows: list[dict], signal: str, sign: float, h: int, period: tuple[date, date]) -> dict:
    """Trade sign(signal) * sign every h-th trading day; one observation per
    day = the mean over the pairs that trade that day."""
    by_day: dict[date, list[tuple[float, float]]] = {}
    wins = trades = 0

    for r in sample(rows, period, h):
        value = r.get(signal)

        if value is None or value == 0:
            continue

        direction = 1.0 if value * sign > 0 else -1.0
        net = r[f"long_{h}"] if direction > 0 else r[f"short_{h}"]
        by_day.setdefault(r["day"], []).append((net, direction * r[f"gross_{h}"]))
        trades += 1
        wins += net > 0

    net_days = [sum(x[0] for x in v) / len(v) for v in by_day.values()]
    gross_days = [sum(x[1] for x in v) / len(v) for v in by_day.values()]
    return {"n_days": len(net_days), "trades": trades, "win": wins / trades if trades else None,
            **_mean_t(net_days, "net"), **_mean_t(gross_days, "gross")}


def _mean_t(values: list[float], prefix: str) -> dict:
    n = len(values)

    if n < 10:
        return {f"{prefix}": None, f"{prefix}_t": None}

    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return {prefix: mean, f"{prefix}_t": mean / (sd / math.sqrt(n)) if sd > 0 else 0.0}


def _fmt(x, f="+.3f"):
    return "-" if x is None else format(x, f)


def _load() -> list[dict]:
    if not SIGNALS_FILE.exists():
        raise SystemExit("nejdriv: python scripts/research_signals.py extract")

    return pickle.loads(SIGNALS_FILE.read_bytes())


def discover() -> None:
    if CANDIDATES_FILE.exists():
        raise SystemExit(f"{CANDIDATES_FILE} uz existuje - kandidati jsou zamceni. Novy objev = novy soubor "
                         f"(smazat jen s novym zapisem v docs/CHANGE_LOG.md).")

    rows = [r for r in _load() if PERIODS["DISCOVERY"][0] <= r["day"] <= PERIODS["DISCOVERY"][1]]
    first, last = PERIODS["DISCOVERY"]
    middle = first + (last - first) / 2
    halves = ((first, middle), (middle + timedelta(days=1), last))
    results = []

    for signal in SIGNALS:
        for h in HORIZONS:
            for sign, label in ((1.0, "trend"), (-1.0, "proti")):
                full = evaluate(rows, signal, sign, h, PERIODS["DISCOVERY"])
                parts = [evaluate(rows, signal, sign, h, half) for half in halves]
                results.append({"signal": signal, "direction": label, "sign": sign, "h": h, **full,
                                "half_net": [p["net"] for p in parts]})

    tested = len(results)
    candidates = [r for r in results if r["net_t"] is not None and r["net_t"] >= DISCOVERY_T
                  and all(x is not None and x > 0 for x in r["half_net"]) and (r["gross"] or 0) > 0]
    candidates.sort(key=lambda r: -r["net_t"])
    lock = {"created": datetime.now(UTC).isoformat(timespec="seconds"), "discovery": [str(d) for d in PERIODS["DISCOVERY"]],
            "rule": f"net t >= {DISCOVERY_T}, both halves > 0, gross > 0; {tested} tests",
            "candidates": [{"signal": c["signal"], "direction": c["direction"], "sign": c["sign"], "h": c["h"]}
                           for c in candidates]}
    payload = json.dumps(lock, indent=1, sort_keys=True)
    CANDIDATES_FILE.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()

    out = ["# Vyzkum signalu - OBJEV (jen 2016-09 .. 2021-12)", "",
           f"_vygenerovano {datetime.now(UTC):%Y-%m-%d %H:%M} UTC; {tested} testu (signal x smer x horizont)_", "",
           "Obchod = vstup na dennim zaveru ve smeru signalu (trend) nebo proti nemu (proti), vystup po h obchodnich "
           "dnech. Jednotky: ATR(D1) na obchod. net = po nakladech (typicky retail spread + 0.4 pip skluz) a swapu "
           "(rozdil kratkych sazeb - 1 % p.a. prirazka); gross = jen pohyb mid ceny (nahodny smer = 0). "
           "t = prumer / chyba prumeru pres dny bez prekryvu.", "",
           f"Kandidat musi mit net t >= {DISCOVERY_T}, kladny net v obou polovinach obdobi a kladny gross.", "",
           "| signal | smer | h [dny] | dnu | obchodu | win | net | net t | gross | gross t | 1. pol. | 2. pol. |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    for r in sorted(results, key=lambda r: -(r["net_t"] or -99))[:40]:
        out.append(f"| {r['signal']} | {r['direction']} | {r['h']} | {r['n_days']} | {r['trades']} | "
                   f"{_fmt(r['win'], '.0%')} | {_fmt(r['net'])} | {_fmt(r['net_t'], '+.2f')} | {_fmt(r['gross'])} | "
                   f"{_fmt(r['gross_t'], '+.2f')} | {_fmt(r['half_net'][0])} | {_fmt(r['half_net'][1])} |")

    out += ["", f"**Zamceni kandidati ({len(candidates)}):** " +
            (", ".join(f"{c['signal']} {c['direction']} {c['h']} d" for c in candidates) or "zadny"),
            "", f"Soubor `data/research/candidates.json`, SHA-256 `{digest}`. Potvrzeni: "
            "`python scripts/research_signals.py confirm` (jednou, na obdobich EARLY a HOLDOUT)."]
    (PROJECT_ROOT / "docs" / "VYZKUM_OBJEVY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


def confirm() -> None:
    if not CANDIDATES_FILE.exists():
        raise SystemExit("nejdriv: python scripts/research_signals.py discover")

    payload = CANDIDATES_FILE.read_text()
    digest = hashlib.sha256(payload.encode()).hexdigest()
    lock = json.loads(payload)
    rows = _load()
    out = ["# Vyzkum signalu - POTVRZENI na datech, ktera vyber nevidel", "",
           f"_vygenerovano {datetime.now(UTC):%Y-%m-%d %H:%M} UTC; kandidati `candidates.json` SHA-256 `{digest}` "
           f"(zamceno {lock['created']})_", "",
           f"Prosel = kladny net v EARLY i HOLDOUT a t >= {CONFIRM_T} na obou dohromady.", "",
           "| signal | smer | h | obdobi | dnu | obchodu | win | net | net t | gross | gross t |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    passed = []

    for c in lock["candidates"]:
        res = {name: evaluate(rows, c["signal"], c["sign"], c["h"], PERIODS[name]) for name in ("EARLY", "HOLDOUT")}
        both = _combined(rows, c, ("EARLY", "HOLDOUT"))

        for name, r in list(res.items()) + [("OBE", both)]:
            out.append(f"| {c['signal']} | {c['direction']} | {c['h']} | {name} | {r['n_days']} | {r['trades']} | "
                       f"{_fmt(r['win'], '.0%')} | {_fmt(r['net'])} | {_fmt(r['net_t'], '+.2f')} | "
                       f"{_fmt(r['gross'])} | {_fmt(r['gross_t'], '+.2f')} |")

        ok = (all((res[k]["net"] or -1) > 0 for k in res) and (both["net_t"] or 0) >= CONFIRM_T)

        if ok:
            passed.append(c)

    out += ["", f"**Proslo: {len(passed)} z {len(lock['candidates'])}** " +
            (", ".join(f"{c['signal']} {c['direction']} {c['h']} d" for c in passed) or "")]
    (PROJECT_ROOT / "docs" / "VYZKUM_POTVRZENI.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


def _combined(rows: list[dict], c: dict, names: tuple) -> dict:
    """Both periods as one sample (day observations of each period)."""
    net_days, gross_days, trades, wins = [], [], 0, 0

    for name in names:
        by_day = {}

        for r in sample(rows, PERIODS[name], c["h"]):
            value = r.get(c["signal"])

            if value is None or value == 0:
                continue

            direction = 1.0 if value * c["sign"] > 0 else -1.0
            net = r[f"long_{c['h']}"] if direction > 0 else r[f"short_{c['h']}"]
            by_day.setdefault(r["day"], []).append((net, direction * r[f"gross_{c['h']}"]))
            trades += 1
            wins += net > 0

        net_days += [sum(x[0] for x in v) / len(v) for v in by_day.values()]
        gross_days += [sum(x[1] for x in v) / len(v) for v in by_day.values()]

    return {"n_days": len(net_days), "trades": trades, "win": wins / trades if trades else None,
            **_mean_t(net_days, "net"), **_mean_t(gross_days, "gross")}


def main(argv: list[str]) -> int:
    commands = {"extract": extract, "discover": discover, "confirm": confirm}

    if not argv or argv[0] not in commands:
        print(__doc__)
        return 1

    commands[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
