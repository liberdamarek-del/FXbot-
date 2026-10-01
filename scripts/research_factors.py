"""Round 3 of the signal research: classic currency factors on 36 years and
13 currencies (FRED daily rates, OECD 3-month interest rates).

    python scripts/research_factors.py fetch      # FRED CSVs -> data/research/fred/ (~1 min)
    python scripts/research_factors.py discover   # 1990-01 .. 2012-12 only; locks the candidates
    python scripts/research_factors.py confirm    # locked candidates on 2013-01 .. 2026-08, ONCE

Why: on 5 years of daily data a test at t >= 3 can only find strategies with
an annual Sharpe ratio >= 1.3 (measured in round 1/2). The effects documented
for currencies (carry, momentum, long-term reversal = value proxy, dollar
carry) have Sharpe ratios of 0.3-0.7 - they need decades and many
currencies. FRED has daily exchange rates since 1971 and OECD 3-month
interbank rates for most currencies.

Portfolio (monthly, at the month end): rank the available currencies (incl.
USD) by the signal, long the top 3, short the bottom 3, equal weights. A
currency's monthly excess return vs USD = log change of USD per unit +
(its 3-month rate - US rate) / 12, with the rates of the PREVIOUS month
(OECD monthly averages are published after the month: point-in-time).
DOLLAR_CARRY (Lustig, Roussanov, Verdelhan 2014) is time-series: long all
foreign currencies vs USD when their average rate is above the US rate,
short otherwise.

Costs: GROSS = interbank (no spread). RETAIL = half spread per side on the
traded weight (G10 2 bp, NOK/SEK 4 bp, MXN/ZAR/SGD 8 bp) + 1 % p.a. swap
markup per held non-USD leg.

Protocol (fixed before any result): directions come from the literature
(no sign search); a candidate needs gross t >= 2.5 in DISCOVERY (about
Bonferroni for 7 one-sided tests); it is CONFIRMED with gross t >= 1.65
(one-sided 5 %) and a positive mean in HOLDOUT; it is worth trading for a
retail account only if the RETAIL mean is positive too.
"""

import hashlib
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.sources.http import fetch  # noqa: E402

UTC = timezone.utc
FRED_DIR = PROJECT_ROOT / "data" / "research" / "fred"
CANDIDATES = PROJECT_ROOT / "data" / "research" / "candidates_r3.json"
# currency: (FRED daily series, True = quoted as USD per unit, rate series list oldest first)
CURRENCIES = {
    "EUR": ("DEXUSEU", True, ["IR3TIB01DEM156N"]),
    "JPY": ("DEXJPUS", False, ["INTDSRJPM193N", "IR3TIB01JPM156N"]),
    "GBP": ("DEXUSUK", True, ["IR3TIB01GBM156N"]),
    "CHF": ("DEXSZUS", False, ["IR3TIB01CHM156N"]),
    "AUD": ("DEXUSAL", True, ["IR3TIB01AUM156N"]),
    "CAD": ("DEXCAUS", False, ["IR3TIB01CAM156N"]),
    "NZD": ("DEXUSNZ", True, ["IR3TIB01NZM156N"]),
    "NOK": ("DEXNOUS", False, ["IR3TIB01NOM156N"]),
    "SEK": ("DEXSDUS", False, ["IR3TIB01SEM156N"]),
    "MXN": ("DEXMXUS", False, ["IR3TIB01MXM156N"]),
    "ZAR": ("DEXSFUS", False, ["IR3TIB01ZAM156N"]),
    "SGD": ("DEXSIUS", False, []),
}
US_RATE = "IR3TIB01USM156N"
SPREAD_BP = {"NOK": 4, "SEK": 4, "MXN": 8, "ZAR": 8, "SGD": 8}       # others (G10) 2 bp
SWAP_MARKUP = 1.0                                                     # % p.a. per held non-USD leg
DISCOVERY = ((1990, 1), (2012, 12))
HOLDOUT = ((2013, 1), (2026, 8))
SIGNALS = ("CARRY", "MOM_1", "MOM_3", "MOM_12_1", "VALUE_5Y", "CARRY_MOM3", "DOLLAR_CARRY")
DISCOVERY_T = 2.5
CONFIRM_T = 1.65
RATE_STALE_MONTHS = 3


def fetch_all() -> None:
    FRED_DIR.mkdir(parents=True, exist_ok=True)
    ids = [US_RATE] + [c[0] for c in CURRENCIES.values()] + [r for c in CURRENCIES.values() for r in c[2]]

    for series_id in ids:
        _, content, _ = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", retries=3)
        (FRED_DIR / f"{series_id}.csv").write_bytes(content)
        print(f"{series_id}: {len(content)} B sha256={hashlib.sha256(content).hexdigest()[:12]}")


def _csv(series_id: str) -> list[tuple[date, float]]:
    out = []

    for line in (FRED_DIR / f"{series_id}.csv").read_text().strip().splitlines()[1:]:
        day, value = line.split(",")[:2]

        if value not in (".", ""):
            out.append((date.fromisoformat(day), float(value)))

    return out


def _month(d: date) -> tuple[int, int]:
    return d.year, d.month


def _prev(m: tuple[int, int], k: int = 1) -> tuple[int, int]:
    y, mo = m
    index = y * 12 + mo - 1 - k
    return index // 12, index % 12 + 1


def load_panel() -> tuple[list, dict, dict]:
    """Months, month-end USD per unit {ccy: {month: S}}, rates known at the
    month end {ccy: {month: rate}} (previous month's average)."""
    spot, rates = {}, {}

    for ccy, (fx_id, usd_per_unit, rate_ids) in CURRENCIES.items():
        month_end = {}

        for d, v in _csv(fx_id):
            if v > 0:
                month_end[_month(d)] = v if usd_per_unit else 1.0 / v      # last observation of the month wins

        spot[ccy] = month_end
        monthly = {}

        for rate_id in rate_ids:                                         # later series override earlier ones
            for d, v in _csv(rate_id):
                monthly[_month(d)] = v

        rates[ccy] = monthly

    rates["USD"] = {_month(d): v for d, v in _csv(US_RATE)}
    months = sorted(set().union(*[set(s) for s in spot.values()]))
    known = {}

    for ccy, monthly in rates.items():
        # at the end of month m the average of month m-1 is known; a series
        # that stopped is used at most RATE_STALE_MONTHS more
        values = {}

        for m in months:
            for lag in range(1, 2 + RATE_STALE_MONTHS):
                if _prev(m, lag) in monthly:
                    values[m] = monthly[_prev(m, lag)]
                    break

        known[ccy] = values

    return months, spot, known


def signal_values(signal: str, m, months_index: dict, spot: dict, rates: dict) -> dict:
    out = {}
    i_us = rates["USD"].get(m)

    for ccy in list(CURRENCIES) + ["USD"]:
        s = spot.get(ccy)
        price = (lambda k: 1.0 if ccy == "USD" else s.get(_prev(m, k)))
        now = price(0)

        if now is None:
            continue

        if signal == "CARRY" or signal == "CARRY_MOM3":
            rate = rates[ccy].get(m)
            if rate is None or i_us is None:
                continue
            out[ccy] = rate - i_us
        elif signal == "MOM_1" and price(1):
            out[ccy] = math.log(now / price(1))
        elif signal == "MOM_3" and price(3):
            out[ccy] = math.log(now / price(3))
        elif signal == "MOM_12_1" and price(1) and price(12):
            out[ccy] = math.log(price(1) / price(12))
        elif signal == "VALUE_5Y" and price(60):
            out[ccy] = -math.log(now / price(60))

    if signal == "CARRY_MOM3":
        mom = signal_values("MOM_3", m, months_index, spot, rates)
        common = [c for c in out if c in mom]
        rank = lambda d: {c: k / max(1, len(common) - 1) for k, c in enumerate(sorted(common, key=lambda c: d[c]))}
        r_carry, r_mom = rank(out), rank(mom)
        out = {c: (r_carry[c] + r_mom[c]) / 2 for c in common}

    return out


def excess_return(ccy: str, m, spot: dict, rates: dict) -> float | None:
    """Return of holding ccy vs USD from the end of month m to the end of m+1."""
    if ccy == "USD":
        return 0.0

    nxt = (m[0] + (m[1] == 12), m[1] % 12 + 1)
    s0, s1 = spot[ccy].get(m), spot[ccy].get(nxt)
    rate, i_us = rates[ccy].get(m), rates["USD"].get(m)

    if not s0 or not s1:
        return None

    carry = (rate - i_us) / 1200.0 if rate is not None and i_us is not None else 0.0
    return math.log(s1 / s0) + carry


def portfolio(signal: str, period: tuple, months: list, spot: dict, rates: dict) -> dict:
    first, last = period
    idx = {m: k for k, m in enumerate(months)}
    gross, retail = [], []
    weights_prev: dict = {}

    for m in months:
        if not (first <= m <= last):
            continue

        if signal == "DOLLAR_CARRY":
            foreign = [c for c in CURRENCIES if rates[c].get(m) is not None and spot[c].get(m)]
            if not foreign or rates["USD"].get(m) is None:
                continue
            avg = sum(rates[c][m] for c in foreign) / len(foreign)
            sign = 1.0 if avg > rates["USD"][m] else -1.0
            weights = {c: sign / len(foreign) for c in foreign}
        else:
            values = signal_values(signal, m, idx, spot, rates)
            if len(values) < 7:
                continue
            ranked = sorted(values, key=lambda c: values[c])
            weights = {c: -1.0 / 3 for c in ranked[:3]}
            weights.update({c: 1.0 / 3 for c in ranked[-3:]})

        returns = {c: excess_return(c, m, spot, rates) for c in weights}

        if any(r is None for r in returns.values()):
            weights = {c: w for c, w in weights.items() if returns[c] is not None}

        g = sum(w * returns[c] for c, w in weights.items())
        turnover = sum(abs(weights.get(c, 0.0) - weights_prev.get(c, 0.0)) * SPREAD_BP.get(c, 2) / 1e4
                       for c in set(weights) | set(weights_prev) if c != "USD")
        markup = sum(abs(w) for c, w in weights.items() if c != "USD") * SWAP_MARKUP / 1200.0
        gross.append(g)
        retail.append(g - turnover - markup)
        weights_prev = weights

    return {"months": len(gross), **_stats(gross, "gross"), **_stats(retail, "retail")}


def _stats(values: list[float], prefix: str) -> dict:
    n = len(values)

    if n < 24:
        return {prefix: None, f"{prefix}_t": None, f"{prefix}_sr": None}

    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return {prefix: mean * 12 * 100, f"{prefix}_t": mean / (sd / math.sqrt(n)) if sd else 0.0,
            f"{prefix}_sr": mean / sd * math.sqrt(12) if sd else 0.0}


def _row(name: str, r: dict) -> str:
    f = lambda x, fmt: "-" if x is None else format(x, fmt)
    return (f"| {name} | {r['months']} | {f(r['gross'], '+.2f')} % | {f(r['gross_t'], '+.2f')} | "
            f"{f(r['gross_sr'], '+.2f')} | {f(r['retail'], '+.2f')} % | {f(r['retail_t'], '+.2f')} |")


HEADER = ["| signal | mesicu | gross p.a. | gross t | Sharpe | retail p.a. | retail t |", "|---|---|---|---|---|---|---|"]


def discover() -> None:
    if CANDIDATES.exists():
        raise SystemExit(f"{CANDIDATES} uz existuje - kandidati jsou zamceni")

    months, spot, rates = load_panel()
    results = {s: portfolio(s, DISCOVERY, months, spot, rates) for s in SIGNALS}
    chosen = [s for s, r in results.items() if (r["gross_t"] or 0) >= DISCOVERY_T]
    payload = json.dumps({"created": datetime.now(UTC).isoformat(timespec="seconds"), "candidates": chosen,
                          "rule": f"gross t >= {DISCOVERY_T} in {DISCOVERY}"}, sort_keys=True)
    CANDIDATES.write_text(payload)
    out = ["# Vyzkum signalu - kolo 3 - menove faktory, OBJEV 1990-01 .. 2012-12", "",
           f"_vygenerovano {datetime.now(UTC):%Y-%m-%d %H:%M} UTC; 13 men (vc. USD), mesicni portfolio long 3 / "
           f"short 3; smery dane literaturou_", ""] + HEADER
    out += [_row(s, r) for s, r in results.items()]
    out += ["", f"**Zamceni kandidati: {', '.join(chosen) or 'zadny'}** (gross t >= {DISCOVERY_T}); SHA-256 "
            f"`{hashlib.sha256(payload.encode()).hexdigest()}`"]
    (PROJECT_ROOT / "docs" / "VYZKUM_OBJEVY_K3.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


def confirm() -> None:
    lock = json.loads(CANDIDATES.read_text())
    months, spot, rates = load_panel()
    out = ["# Vyzkum signalu - kolo 3 - POTVRZENI 2013-01 .. 2026-08", "",
           f"_kandidati zamceni {lock['created']}; potvrzeni = gross t >= {CONFIRM_T} a kladny prumer; "
           f"pro retail ucet navic kladny retail_", ""] + HEADER
    passed = []

    for s in lock["candidates"]:
        r = portfolio(s, HOLDOUT, months, spot, rates)
        out.append(_row(s, r))

        if (r["gross_t"] or 0) >= CONFIRM_T:
            passed.append(f"{s}{' (i retail kladny)' if (r['retail'] or 0) > 0 else ' (retail zaporny)'}")

    out += ["", f"**Potvrzeno: {', '.join(passed) or 'nic'}**"]
    (PROJECT_ROOT / "docs" / "VYZKUM_POTVRZENI_K3.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


def main(argv: list[str]) -> int:
    commands = {"fetch": fetch_all, "discover": discover, "confirm": confirm}

    if not argv or argv[0] not in commands:
        print(__doc__)
        return 1

    commands[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
