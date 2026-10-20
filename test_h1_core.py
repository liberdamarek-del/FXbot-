"""H1 - the live core (src/core) and its boundary (R-048, architektura-v2, phase 1); no network, no data/.

1. The live core (signals_live, aktualizace, diagnostika, portfolio_sim, profit_deep and everything they import,
   also lazily inside functions) does not import the research labs (profit_lab, profit_lab2, winrate_lab, pivot_lab,
   strategy_mining); src/core imports nothing from scripts/.
2. One source of truth: costs, paths and FRED series ids in src/core are the ones the scripts use.
3. Stored trades: the whole path prices -> rates -> indicators -> signals -> simulator -> account on synthetic data
   (tests/jadro_scenar.py) gives exactly the numbers in tests/fixtures/jadro_zlaty.json, which were computed by the
   code BEFORE the move into src/core (series, rates, 3 champion rules with their trades, 4 more rule variants, the
   account). Floats are compared bit for bit (float.hex), arrays by the sha256 of their bytes.
"""

import ast
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_h1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
for p in (PROJECT_ROOT, PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests"):
    sys.path.insert(0, str(p))

CORE = ["signals_live", "aktualizace", "diagnostika", "portfolio_sim", "profit_deep"]
LABS = {"profit_lab", "profit_lab2", "winrate_lab", "pivot_lab", "strategy_mining"}
SCRIPTS = {p.stem for p in (PROJECT_ROOT / "scripts").glob("*.py")}


def imports_of(path: Path) -> set[str]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):       # also imports inside functions
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


# ---------------------------------------------------------------- 1. the boundary
reach, stack = set(), list(CORE)
while stack:
    m = stack.pop()
    if m in reach:
        continue
    reach.add(m)
    stack += [i for i in imports_of(PROJECT_ROOT / "scripts" / f"{m}.py") if i in SCRIPTS]
assert not (reach & LABS), f"zive jadro importuje laby: {sorted(reach & LABS)} (reach: {sorted(reach)})"
for path in sorted((PROJECT_ROOT / "src" / "core").glob("*.py")):
    bad = imports_of(path) & SCRIPTS
    assert not bad, f"{path.name} importuje z scripts/: {sorted(bad)}"

# ---------------------------------------------------------------- 2. one source of truth
import fxcm_universe as U  # noqa: E402
import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402
import research_factors as RF  # noqa: E402
import research_signals as RS  # noqa: E402
import signals_live as SL  # noqa: E402
from src.core import market as P  # noqa: E402
from src.core import paths, rates, ta  # noqa: E402

assert D.P is P and SL.P is P and SL.SM is ta
assert U.ROOT == paths.FXCM_H1 and U.HISTDATA == paths.HISTDATA_H1 and RF.FRED_DIR == paths.FRED_DIR
assert U.load is P.load_hourly and U.FIELDS == P.FIELDS and RF._csv is rates.read_fred
assert RS.SPREAD_PIPS == P.SPREAD_PIPS_12 and RS.SLIPPAGE_PIPS == P.SLIPPAGE_PIPS and RS.FINANCING_MARKUP == P.FIN_MARKUP
assert set(P.SPREAD_PIPS_12) <= set(P.SPREAD_PIPS) and all(P.SPREAD_PIPS[k] == v for k, v in P.SPREAD_PIPS_12.items())
want_ids = {"USD": [RF.US_RATE], **{c: v[2] for c, v in RF.CURRENCIES.items()
                                    if c in ("EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD", "NOK", "SEK", "MXN", "ZAR")},
            "PLN": ["IR3TIB01PLM156N"], "HUF": ["IR3TIB01HUM156N"], "CZK": ["IR3TIB01CZM156N"]}
assert rates.RATE_IDS == want_ids and list(rates.RATE_IDS) == list(want_ids), "RATE_IDS se rozesly od research_factors"
assert paths.PROFIT2 == P.OUT or P.OUT.name == "profit2"

# the code hash of the live-timing cache covers exactly the files of the indicator code
src = (PROJECT_ROOT / "scripts" / "profit_deep.py").read_text(encoding="utf-8")
assert '("market.py", "rates.py", "ta.py")' in src

# ---------------------------------------------------------------- 3. stored trades (synthetic scenario)
import jadro_scenar as S  # noqa: E402


F = SimpleNamespace(ta=ta, P=P, D=D, PS=PS, dirs=S.dirs_core)
with tempfile.TemporaryDirectory(prefix="fxbot_h1_s_") as tmp:
    got = json.loads(json.dumps(S.vypocitej(F, Path(tmp))))
want = json.loads((PROJECT_ROOT / "tests" / "fixtures" / "jadro_zlaty.json").read_text(encoding="utf-8"))["hodnoty"]


def diff(a, b, where="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{where}/{k}: chybi v {'novem' if k not in a else 'zlatem'}")
            else:
                diff(a[k], b[k], f"{where}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{where}: delka {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, f"{where}[{i}]", out)
    elif a != b:
        out.append(f"{where}: {a!r} vs {b!r}")
    return out


bad = diff(got, want)
assert not bad, f"{len(bad)} rozdilu proti zlatemu zakladu (pred presunem), prvnich 10: {bad[:10]}"
n_trades = {k: v["n"] for k, v in want["trades"].items()}
assert min(n_trades[k] for k in ("max_stupen0", "max_stupen3", "mesicne_stupen2")) >= 10, n_trades   # scenario has trades

print("=" * 60)
print("H1 LIVE CORE (src/core)")
print("=" * 60)
print("LIVE CORE DOES NOT IMPORT THE LABS, src/core NOTHING FROM scripts/: PASS")
print("ONE SOURCE OF TRUTH (COSTS, PATHS, FRED SERIES, indicator code hash): PASS")
print(f"STORED TRADES BIT FOR BIT (series, rates, indicators, signals, {sum(n_trades.values())} trades, account): PASS")
print("RESULT: PASS")
print("=" * 60)
