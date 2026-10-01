"""FX instrument universe (specification module 17).

One place that knows, for every supported pair:
- base / quote currency (needed by the fundamental engine: a pair is the
  difference between two currencies),
- pip size and price decimals (reporting, costs, R:R in pips),
- the Dukascopy instrument code and its integer price scale (historical
  bid/ask source, src/sources/dukascopy.py),
- a plausibility range for the price. A decoded number outside this range
  is a parser/scale error, never a price (module 5: no fabricated prices).

DEFAULT_ACTIVE is the live universe (12 pairs, chosen with the user in
Block B3; the free Twelve Data plan limits how many pairs can be kept
current). The other pairs of module 17 are available for history and
analysis on demand (FXBOT_SYMBOLS / --symbols).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    base: str
    quote: str
    pip: float
    decimals: int
    dukascopy_code: str
    dukascopy_scale: int
    min_price: float
    max_price: float

    @property
    def is_jpy_quote(self) -> bool:
        return self.quote == "JPY"

    def pips(self, price_difference: float) -> float:
        return price_difference / self.pip

    def fmt(self, value: float | None) -> str:
        if value is None:
            return "-"

        return f"{value:.{self.decimals}f}"


def _pair(symbol: str, low: float, high: float) -> Instrument:
    base, quote = symbol.split("/")
    jpy = quote == "JPY"

    return Instrument(
        symbol=symbol,
        base=base,
        quote=quote,
        pip=0.01 if jpy else 0.0001,
        decimals=3 if jpy else 5,
        dukascopy_code=base + quote,
        dukascopy_scale=1000 if jpy else 100000,
        min_price=low,
        max_price=high,
    )


def _custom(symbol: str, pip: float, decimals: int, low: float, high: float) -> Instrument:
    base, quote = symbol.split("/")
    return Instrument(symbol=symbol, base=base, quote=quote, pip=pip, decimals=decimals,
                      dukascopy_code=base + quote, dukascopy_scale=10 ** decimals, min_price=low, max_price=high)


# Plausibility ranges are deliberately wide (decades of history fit inside);
# they only catch scale/parser errors.
_ALL = (
    _pair("EUR/USD", 0.5, 2.5),
    _pair("USD/JPY", 50.0, 400.0),
    _pair("GBP/USD", 0.7, 3.0),
    _pair("USD/CHF", 0.4, 2.5),
    _pair("AUD/USD", 0.3, 1.5),
    _pair("USD/CAD", 0.7, 2.5),
    _pair("NZD/USD", 0.2, 1.3),
    _pair("EUR/JPY", 60.0, 400.0),
    _pair("GBP/JPY", 80.0, 500.0),
    _pair("EUR/GBP", 0.4, 1.5),
    _pair("EUR/CHF", 0.5, 2.5),
    _pair("AUD/JPY", 30.0, 250.0),
    _pair("EUR/CAD", 0.8, 2.5),
    _pair("GBP/CHF", 0.7, 3.5),
    _pair("CAD/JPY", 40.0, 250.0),
    _pair("NZD/JPY", 30.0, 200.0),
    # remaining crosses of the 8 currencies (research universe; FXCM has no
    # CHF/JPY, GBP/AUD history)
    _pair("AUD/CAD", 0.5, 1.6),
    _pair("AUD/CHF", 0.3, 1.6),
    _pair("AUD/NZD", 0.7, 1.6),
    _pair("CAD/CHF", 0.3, 1.6),
    _pair("CHF/JPY", 40.0, 300.0),
    _pair("EUR/AUD", 0.9, 2.8),
    _pair("EUR/NZD", 1.0, 3.0),
    _pair("GBP/AUD", 1.1, 3.2),
    _pair("GBP/CAD", 1.1, 3.2),
    _pair("GBP/NZD", 1.2, 3.8),
    _pair("NZD/CAD", 0.5, 1.4),
    _pair("NZD/CHF", 0.3, 1.4),
    # Scandinavian and emerging currencies (research universe, HistData 1-minute history)
    _pair("USD/NOK", 4.0, 16.0),
    _pair("EUR/NOK", 6.0, 16.0),
    _pair("USD/SEK", 4.0, 16.0),
    _pair("EUR/SEK", 7.0, 16.0),
    _pair("USD/MXN", 8.0, 35.0),
    _pair("USD/ZAR", 5.0, 30.0),
    _pair("ZAR/JPY", 3.0, 20.0),
    _pair("USD/PLN", 2.0, 7.0),
    _pair("EUR/PLN", 3.0, 6.5),
    _custom("USD/HUF", 0.01, 3, 120.0, 500.0),
    _custom("EUR/HUF", 0.01, 3, 200.0, 500.0),
    _custom("USD/CZK", 0.001, 4, 12.0, 35.0),
    _custom("EUR/CZK", 0.001, 4, 20.0, 35.0),
)

INSTRUMENTS: dict[str, Instrument] = {i.symbol: i for i in _ALL}

DEFAULT_ACTIVE = (
    "EUR/USD",
    "USD/JPY",
    "GBP/USD",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "EUR/JPY",
    "GBP/JPY",
    "EUR/GBP",
    "EUR/CHF",
    "AUD/JPY",
)

# Currencies the fundamental engine follows (module 17 driver map).
CURRENCIES = ("USD", "EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD")


def get_instrument(symbol: str) -> Instrument:
    key = symbol.strip().upper()

    if key not in INSTRUMENTS:
        raise KeyError(
            f"unknown instrument {symbol!r}; supported: "
            f"{', '.join(sorted(INSTRUMENTS))}"
        )

    return INSTRUMENTS[key]


def parse_symbols(text: str | None, default=DEFAULT_ACTIVE) -> list[str]:
    """Comma separated list -> validated symbols (default when empty)."""
    if not text or not text.strip():
        return list(default)

    symbols = []

    for part in text.split(","):
        part = part.strip().upper()

        if part:
            symbols.append(get_instrument(part).symbol)

    return symbols
