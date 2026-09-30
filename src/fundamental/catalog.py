"""Catalog of fundamental series (module 17 driver map, modules 20-31).

Each entry names the public source, the exact series code, the frequency
and the publication lag used for point-in-time reads. All sources were
tested from this project on 2026-09-30 (keyless, public):

    FRED      fred.stlouisfed.org (US yields, VIX, equities, credit, oil,
              OECD monthly long-term yields for CHF and NZD)
    ECB       data-api.ecb.europa.eu (euro area AAA government curve)
    MOF       mof.go.jp (Japanese government bond yields)
    BOE       bankofengland.co.uk (gilt par yields; no 2-year series
              published -> the 5-year yield is GBP's short-rate proxy)
    BOC       bankofcanada.ca Valet API (Canada 2y / 10y)
    RBA       rba.gov.au table F2 (Australia 2y / 10y)
    BIS       stats.bis.org (central bank policy rates, all 8 currencies)
    CFTC      publicreporting.cftc.gov (Traders in Financial Futures)

Not available keyless (verified): Swiss daily confederation yields (SNB
cube stopped 2025-07), New Zealand daily yields (RBNZ answers 403). CHF and
NZD therefore use the policy rate plus monthly OECD 10-year yields (lower
quality class, stated in every evidence line that uses them).

Lags (hours after 00:00 UTC of the observation date):
    30    daily market closes (value known after the close of that day)
    24    policy rate in effect on that day (decision announced before)
    75*24 monthly OECD averages
    7*24  weekly St. Louis stress index
"""

from dataclasses import dataclass

DAILY_MARKET_LAG = 30
POLICY_LAG = 24


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    currency: str            # USD, EUR, ... or GLOBAL
    kind: str                # POLICY, Y2, Y5, Y10, REAL10, BEI10, VIX, ...
    source: str              # FRED, ECB, MOF, BOE, BOC, RBA, BIS
    code: str
    frequency: str           # D, W, M
    lag_hours: float
    quality: str             # A (daily official/market), B (daily derived), C (monthly)
    description: str


SERIES: tuple[SeriesSpec, ...] = (
    # ---------------------------------------------------------- policy rates
    SeriesSpec("USD.POLICY", "USD", "POLICY", "BIS", "US", "D", POLICY_LAG, "A", "Fed policy rate (BIS)"),
    SeriesSpec("EUR.POLICY", "EUR", "POLICY", "BIS", "XM", "D", POLICY_LAG, "A", "ECB policy rate (BIS)"),
    SeriesSpec("JPY.POLICY", "JPY", "POLICY", "BIS", "JP", "D", POLICY_LAG, "A", "BoJ policy rate (BIS)"),
    SeriesSpec("GBP.POLICY", "GBP", "POLICY", "BIS", "GB", "D", POLICY_LAG, "A", "BoE Bank Rate (BIS)"),
    SeriesSpec("CHF.POLICY", "CHF", "POLICY", "BIS", "CH", "D", POLICY_LAG, "A", "SNB policy rate (BIS)"),
    SeriesSpec("AUD.POLICY", "AUD", "POLICY", "BIS", "AU", "D", POLICY_LAG, "A", "RBA cash rate (BIS)"),
    SeriesSpec("CAD.POLICY", "CAD", "POLICY", "BIS", "CA", "D", POLICY_LAG, "A", "BoC overnight rate (BIS)"),
    SeriesSpec("NZD.POLICY", "NZD", "POLICY", "BIS", "NZ", "D", POLICY_LAG, "A", "RBNZ OCR (BIS)"),
    # ---------------------------------------------------------- government yields
    SeriesSpec("USD.Y2", "USD", "Y2", "FRED", "DGS2", "D", DAILY_MARKET_LAG, "A", "US Treasury 2y"),
    SeriesSpec("USD.Y10", "USD", "Y10", "FRED", "DGS10", "D", DAILY_MARKET_LAG, "A", "US Treasury 10y"),
    SeriesSpec("USD.REAL10", "USD", "REAL10", "FRED", "DFII10", "D", DAILY_MARKET_LAG, "A", "US 10y TIPS real yield"),
    SeriesSpec("USD.BEI10", "USD", "BEI10", "FRED", "T10YIE", "D", DAILY_MARKET_LAG, "A", "US 10y breakeven inflation"),
    SeriesSpec("EUR.Y2", "EUR", "Y2", "ECB", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y", "D", DAILY_MARKET_LAG, "A", "Euro area AAA 2y"),
    SeriesSpec("EUR.Y10", "EUR", "Y10", "ECB", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "D", DAILY_MARKET_LAG, "A", "Euro area AAA 10y"),
    SeriesSpec("JPY.Y2", "JPY", "Y2", "MOF", "2Y", "D", DAILY_MARKET_LAG, "A", "JGB 2y"),
    SeriesSpec("JPY.Y10", "JPY", "Y10", "MOF", "10Y", "D", DAILY_MARKET_LAG, "A", "JGB 10y"),
    SeriesSpec("GBP.Y5", "GBP", "Y5", "BOE", "IUDSNPY", "D", DAILY_MARKET_LAG, "A", "Gilt 5y nominal par yield"),
    SeriesSpec("GBP.Y10", "GBP", "Y10", "BOE", "IUDMNPY", "D", DAILY_MARKET_LAG, "A", "Gilt 10y nominal par yield"),
    SeriesSpec("CAD.Y2", "CAD", "Y2", "BOC", "BD.CDN.2YR.DQ.YLD", "D", DAILY_MARKET_LAG, "A", "Canada 2y benchmark"),
    SeriesSpec("CAD.Y10", "CAD", "Y10", "BOC", "BD.CDN.10YR.DQ.YLD", "D", DAILY_MARKET_LAG, "A", "Canada 10y benchmark"),
    SeriesSpec("AUD.Y2", "AUD", "Y2", "RBA", "FCMYGBAG2D", "D", DAILY_MARKET_LAG, "A", "Australia 2y"),
    SeriesSpec("AUD.Y10", "AUD", "Y10", "RBA", "FCMYGBAG10D", "D", DAILY_MARKET_LAG, "A", "Australia 10y"),
    SeriesSpec("CHF.Y10M", "CHF", "Y10M", "FRED", "IRLTLT01CHM156N", "M", 75 * 24, "C", "Switzerland 10y (OECD monthly)"),
    SeriesSpec("NZD.Y10M", "NZD", "Y10M", "FRED", "IRLTLT01NZM156N", "M", 75 * 24, "C", "New Zealand 10y (OECD monthly)"),
    # ---------------------------------------------------------- global risk / intermarket
    SeriesSpec("GLOBAL.VIX", "GLOBAL", "VIX", "FRED", "VIXCLS", "D", DAILY_MARKET_LAG, "A", "CBOE VIX"),
    SeriesSpec("GLOBAL.SPX", "GLOBAL", "SPX", "FRED", "SP500", "D", DAILY_MARKET_LAG, "A", "S&P 500"),
    SeriesSpec("GLOBAL.NASDAQ", "GLOBAL", "NASDAQ", "FRED", "NASDAQCOM", "D", DAILY_MARKET_LAG, "A", "Nasdaq Composite"),
    SeriesSpec("GLOBAL.HY_OAS", "GLOBAL", "HY_OAS", "FRED", "BAMLH0A0HYM2", "D", DAILY_MARKET_LAG, "A", "US high-yield OAS"),
    SeriesSpec("GLOBAL.FSI", "GLOBAL", "FSI", "FRED", "STLFSI4", "W", 7 * 24, "B", "St. Louis financial stress index"),
    SeriesSpec("GLOBAL.BRENT", "GLOBAL", "BRENT", "FRED", "DCOILBRENTEU", "D", DAILY_MARKET_LAG, "A", "Brent crude (USD)"),
    SeriesSpec("GLOBAL.WTI", "GLOBAL", "WTI", "FRED", "DCOILWTICO", "D", DAILY_MARKET_LAG, "A", "WTI crude (USD)"),
    SeriesSpec("GLOBAL.USD_BROAD", "GLOBAL", "USD_BROAD", "FRED", "DTWEXBGS", "D", 6 * 24, "B", "Broad trade-weighted USD"),
)

SERIES_BY_ID = {s.series_id: s for s in SERIES}

# CFTC Traders in Financial Futures, contract codes verified 2026-09-30.
# The futures are quoted as the currency against USD, so a positive net
# position is long the currency (short USD).
COT_CONTRACTS = {
    "EUR": "099741",
    "JPY": "097741",
    "GBP": "096742",
    "CHF": "092741",
    "CAD": "090741",
    "AUD": "232741",
    "NZD": "112741",
}
# report as of Tuesday, released Friday 15:30 New York -> Friday 20:30 UTC
COT_LAG_HOURS = 3 * 24 + 20.5

# The short-rate series used for rate differentials, per currency, with
# the reason when it is a proxy.
SHORT_RATE = {
    "USD": ("USD.Y2", None),
    "EUR": ("EUR.Y2", None),
    "JPY": ("JPY.Y2", None),
    "GBP": ("GBP.Y5", "5y gilt used as GBP short-rate proxy (no 2y series published)"),
    "CAD": ("CAD.Y2", None),
    "AUD": ("AUD.Y2", None),
    "CHF": ("CHF.POLICY", "no daily CHF yield available keyless; policy rate used"),
    "NZD": ("NZD.POLICY", "no daily NZD yield available keyless; policy rate used"),
}

LONG_RATE = {
    "USD": "USD.Y10",
    "EUR": "EUR.Y10",
    "JPY": "JPY.Y10",
    "GBP": "GBP.Y10",
    "CAD": "CAD.Y10",
    "AUD": "AUD.Y10",
    "CHF": "CHF.Y10M",
    "NZD": "NZD.Y10M",
}

# Currencies whose FX value is commonly linked to a commodity (module 30).
# Used only as a hypothesis to be tested against the data, never as a rule.
COMMODITY_LINKS = {
    "CAD": ("GLOBAL.WTI", "oil exporter"),
    "AUD": ("GLOBAL.SPX", "global growth / risk proxy (no free daily iron ore / copper)"),
    "NZD": ("GLOBAL.SPX", "global growth / risk proxy"),
}

# Funding / safe-haven currencies (module 31) - diagnosed from data, the
# label is only the starting hypothesis.
SAFE_HAVEN_CANDIDATES = ("JPY", "CHF", "USD")
