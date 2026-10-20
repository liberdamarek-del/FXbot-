"""Cesty k datum zivého jadra (jediny zdroj; fxcm_universe a research_factors je jen prevzaly).

Data jsou mimo git (data/), stahuji se skripty. Funkce jadra cesty ctou az pri volani (`paths.FRED_DIR`), aby je
testy mohly presmerovat do docasne slozky.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FXCM_H1 = PROJECT_ROOT / "data" / "research" / "fxcm_h1"                # hodinove BID/ASK svicky FXCM (npz)
HISTDATA_H1 = PROJECT_ROOT / "data" / "research" / "histdata_h1"        # HistData (jen BID) pro pary bez FXCM
FRED_DIR = PROJECT_ROOT / "data" / "research" / "fred"                  # mesicni a denni rady z FRED (csv)
PROFIT2 = PROJECT_ROOT / "data" / "research" / "profit2"                # cache serii a vystupy labu
