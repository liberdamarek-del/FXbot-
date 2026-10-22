"""Urokove sazby a krivka vynosu pro zive jadro (mesicni OECD / FRED rady, zname se zpozdenim).

Funkce jsou PRESUNUTE DOSLOVNE z scripts/profit_lab2.py (R-048, architektura-v2, faze 1); `read_fred` je
scripts/research_factors._csv. Vysledky musi zustat bit po bitu stejne (test_h1_core.py).
"""

from datetime import date

from . import paths


def read_fred(series_id: str) -> list[tuple[date, float]]:
    out = []

    for line in (paths.FRED_DIR / f"{series_id}.csv").read_text().strip().splitlines()[1:]:
        day, value = line.split(",")[:2]

        if value not in (".", ""):
            out.append((date.fromisoformat(day), float(value)))

    return out


# mesicni 3m mezibankovni sazby (OECD / FRED), nejstarsi rada prvni; pozdejsi rada prepise starsi.
# Stejne identifikatory jako research_factors.CURRENCIES (hlida test_h1_core.py).
RATE_IDS = {"USD": ["IR3TIB01USM156N"], "EUR": ["IR3TIB01DEM156N"], "JPY": ["INTDSRJPM193N", "IR3TIB01JPM156N"],
            "GBP": ["IR3TIB01GBM156N"], "CHF": ["IR3TIB01CHM156N"], "AUD": ["IR3TIB01AUM156N"],
            "CAD": ["IR3TIB01CAM156N"], "NZD": ["IR3TIB01NZM156N"], "NOK": ["IR3TIB01NOM156N"],
            "SEK": ["IR3TIB01SEM156N"], "MXN": ["IR3TIB01MXM156N"], "ZAR": ["IR3TIB01ZAM156N"],
            "PLN": ["IR3TIB01PLM156N"], "HUF": ["IR3TIB01HUM156N"], "CZK": ["IR3TIB01CZM156N"]}


# OECD monthly immediate (overnight) rates - for GBP the SONIA monthly average - that continue a
# 3-month series whose source stopped or lags (the OECD GBP 3-month rate ends 2026-01): after the
# last 3-month value the rate moves by the change of this series. GBP 2012-2026: 3-month changes
# correlate 0.88 with the 3-month series, same sign in 90 % of the moves >= 0.1 (audit 2026-10-02).
EXTEND_IDS = {c: f"IRSTCI01{cc}M156N" for c, cc in (("USD", "US"), ("JPY", "JP"), ("GBP", "GB"), ("AUD", "AU"),
                                                    ("CAD", "CA"))}
EXTENDED: dict = {}                                       # currency -> first month taken from the extension


def monthly_rates() -> dict:
    out = {}
    for ccy, ids in RATE_IDS.items():
        series = {}
        for sid in ids:                                     # later series override older ones
            for d, v in read_fred(sid):
                series[(d.year, d.month)] = v
        ext_id = EXTEND_IDS.get(ccy)
        if ext_id and series and (paths.FRED_DIR / f"{ext_id}.csv").exists():
            ext = {(d.year, d.month): v for d, v in read_fred(ext_id)}
            last = max(series)
            if last in ext:
                for k in sorted(k for k in ext if k > last):
                    series[k] = series[last] + ext[k] - ext[last]
                    EXTENDED.setdefault(ccy, k)
        out[ccy] = series
    return out


# OECD long-term government bond yields (monthly averages) for the relative yield curve (round 34,
# scripts/vyzkum_krivka.py, Chen & Tsang 2013); EUR = Germany (the euro area series lags by months)
LONG_IDS = {"USD": "IRLTLT01USM156N", "EUR": "IRLTLT01DEM156N", "JPY": "IRLTLT01JPM156N", "GBP": "IRLTLT01GBM156N",
            "CHF": "IRLTLT01CHM156N", "AUD": "IRLTLT01AUM156N", "CAD": "IRLTLT01CAM156N", "NZD": "IRLTLT01NZM156N"}


def monthly_long_rates() -> dict:
    return {c: ({(d.year, d.month): v for d, v in read_fred(sid)} if (paths.FRED_DIR / f"{sid}.csv").exists() else {})
            for c, sid in LONG_IDS.items()}


def curve_mom(rates: dict, long_: dict, base: str, quote: str, year: int, month: int, lag: int, window: int):
    """Change over `window` months of the relative yield-curve slope (10y yield minus the 3-month rate, base minus
    quote) known `lag` months after; > 0 = the base currency's curve steepened relative to the quote's (its long
    end rose more than its short end: a risk / term premium rather than policy). None when data are missing."""
    def slope(lg):
        v = [(rate_at(rates.get(c, {}), year, month, lg), rate_at(long_.get(c, {}), year, month, lg)) for c in (base, quote)]
        if any(x is None for pair in v for x in pair):
            return None
        (sb, lb), (sq, lq) = v
        return (lb - sb) - (lq - sq)
    now, old = slope(lag), slope(lag + window)
    return None if now is None or old is None else now - old


def rate_at(series: dict, year: int, month: int, lag: int):
    index = year * 12 + month - 1 - lag
    for k in range(index, index - 12, -1):                 # forward fill at most 12 months
        v = series.get((k // 12, k % 12 + 1))
        if v is not None:
            return v
    return None
