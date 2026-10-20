"""I1 - research hygiene (R-049, architektura-v2, phase 2); no network, no data/.

1. ledger: hash chain detects an edited, deleted or reordered record; appending keeps it valid.
2. trial registry: the import of docs/UCENI_LOG.md gives every logged trial (count, accepted, profiles), the registry
   file is an intact chain whose first records are exactly that import, a new trial must be registered with all fields.
3. statistics: closed-form checks of the expected maximum of N Sharpe ratios, PSR / DSR (also against a hand computation
   with math.erf) and CSCV PBO (about one half for pure noise, about zero when one strategy is truly better).
4. vault: the series is cut at the locked date, the hourly arrays with it; open vault = whole series; the opening needs
   the user's consent text; nobody except scripts/trezor.py looks behind the lock.
"""

import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_i1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
for p in (PROJECT_ROOT, PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests"):
    sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

import jadro_scenar as S  # noqa: E402
import registr_pokusu as RP  # noqa: E402
import trezor as TZS  # noqa: E402  (scripts/trezor.py)
from src.core import ledger as LG  # noqa: E402
from src.core import market as P  # noqa: E402
from src.core import statistika as ST  # noqa: E402
from src.core import trezor as TZ  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="fxbot_i1_f_"))

# ---------------------------------------------------------------- 1. ledger
chain = tmp / "chain.jsonl"
LG.append(chain, [{"a": k, "text": f"zaznam {k}"} for k in range(5)])
assert LG.verify(chain) == {"ok": True, "n": 5, "posledni_hash": LG.last_hash(chain)}
LG.append(chain, [{"a": 5}])
assert LG.verify(chain)["ok"] and LG.verify(chain)["n"] == 6
lines = chain.read_text().splitlines()


def broken(new_lines):
    f = tmp / "x.jsonl"
    f.write_text("\n".join(new_lines) + "\n")
    return not LG.verify(f)["ok"]


assert broken(lines[:2] + [lines[2].replace("zaznam 2", "zaznam X")] + lines[3:])        # edited content
assert broken(lines[:2] + lines[3:])                                                     # deleted record in the middle
assert broken([lines[0], lines[2], lines[1]] + lines[3:])                                # reordered
assert LG.verify(tmp / "neexistuje.jsonl") == {"ok": True, "n": 0, "posledni_hash": LG.GENESIS}
assert not broken(lines[:3])                                                             # a prefix is still an intact chain

# ---------------------------------------------------------------- 2. trial registry
sample = """# Denik
## 2026-10-01 - vychozi sampion CH-009 (41 paru)
### 2026-10-01 - prvni_pokus: PRIJATO
* popis prvniho - duvod
* kandidat: 2019-22: **+19.7%** rocne, propad 24% (marze 8%); 2023-26: **+13.3%** rocne, propad 10% (marze 6%)
* sampion:  2019-22: **+17.8%** rocne, propad 35% (marze 6% / 6%); 2023-26: -
## 2026-10-05 - profil mesicne: sampion X (12 paru)
### 2026-10-05 - [champion_12] druhy_pokus: zamitnuto
* popis druheho
* kandidat: 2019-22: **+62.7%** rocne, propad 23%, 3.0 ziskovych/mesic (marze 20% / 4%), po 2 letech +63% / +71%, vynos/propad 2.72; 2023-26: -
* sampion:  2019-22: **+62.8%** rocne, propad 24%, 3.0 ziskovych/mesic (marze 20% / 6%), po 2 letech +69% / +66%, vynos/propad 2.63; 2023-26: -
### 2026-10-05 - tretí_ne: zamitnuto
"""
t = RP.parse_log(sample.replace("tretí_ne", "treti_pokus") + "* popis\n* kandidat: 2019-22: -\n* sampion:  2019-22: -\n")
assert [x["nazev"] for x in t] == ["prvni_pokus", "druhy_pokus", "treti_pokus"]
assert t[0]["universum"] == "41 paru" and t[0]["profil"] == "max" and t[0]["rozhodnuti"] == "PRIJATO"
assert t[1]["universum"] == "12 paru" and t[1]["profil"] == "max"                  # the tag [champion_12] decides
assert t[2]["profil"] == "mesicne" and t[2]["universum"] == "12 paru"              # the section above decides
assert t[0]["kandidat"]["2019-22"] == {"rocne_proc": 19.7, "propad_proc": 24.0, "marze_proc": [8.0]}
assert t[0]["sampion"]["2023-26"] is None                                           # nothing met the conditions
b = t[1]["kandidat"]["2019-22"]
assert b["ziskovych_mesicne"] == 3.0 and b["bloky_2_roky_proc"] == [63.0, 71.0] and b["vynos_na_propad"] == 2.72

real = RP.parse_log()                                                               # the real log
assert len(real) == len(re.findall(r"^### ", (PROJECT_ROOT / "docs" / "UCENI_LOG.md").read_text(), re.M)) >= 332
assert sum(r["rozhodnuti"] == "PRIJATO" for r in real[:332]) == 8
assert all(r["hypoteza"] and r["kandidat"] is not None and r["sampion"] is not None for r in real)
reg = LG.read(RP.REG)
assert LG.verify(RP.REG)["ok"] and len(reg) >= 332, "registr pokusu je poskozeny nebo neuplny"
for rec, trial in zip(reg[:332], real[:332]):                                       # the import is the log, in its order
    assert (rec["typ"], rec["nazev"], rec["datum"], rec["rozhodnuti"], rec["profil"], rec["universum"]) == \
           ("import", trial["nazev"], trial["datum"], trial["rozhodnuti"], trial["profil"], trial["universum"])
    assert rec["vysledek"] == {"kandidat": trial["kandidat"], "sampion": trial["sampion"]}
assert reg[0]["ekonomicky_duvod"].startswith("NEOVERENO")

RP.REG = tmp / "registr.jsonl"                                                      # registration in a scratch registry
assert RP.n_trials() == 0 and not RP.is_registered("novy")
for bad in (("novy", "", "duvod", {"a": 1}, {"test": "x"}), ("novy", "hyp", "NEOVERENO", {"a": 1}, {"test": "x"}),
            ("novy", "hyp", "duvod", {}, {"test": "x"}), ("novy", "hyp", "duvod", {"a": 1}, {})):
    try:
        RP.register(*bad)
        raise AssertionError("registrace s chybejicim polem musi selhat")
    except ValueError:
        pass
rec = RP.register("novy", "hypoteza", "ekonomicky duvod", {"tp": 0.5}, {"vyber": "2012-2018", "test": "2019-2022"})
assert rec["id"] == "T-0001" and RP.is_registered("novy") and RP.n_trials() == 1
res = RP.record_result("novy", "max", "zamitnuto", {"x": 1})
assert res["registrace"] == "T-0001" and RP.n_trials() == 1 and LG.verify(RP.REG)["ok"]     # a result is not a new trial
try:
    RP.record_result("neexistuje", "max", "zamitnuto", {})
    raise AssertionError("vysledek bez registrace musi selhat")
except ValueError:
    pass

# ---------------------------------------------------------------- 3. statistics
N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))  # noqa: E731
sr0 = ST.expected_max_sr(100, 1.0)
assert abs(sr0 - 2.5306) < 5e-4 and ST.expected_max_sr(1, 1.0) == 0.0
assert ST.expected_max_sr(1000, 1.0) > ST.expected_max_sr(100, 1.0) > ST.expected_max_sr(10, 1.0)
assert abs(ST.expected_max_sr(100, 0.04) - 0.2 * sr0) < 1e-12                       # scales with sqrt(variance)
assert abs(ST.psr(0.3, 0.3, 100, 0.0, 3.0) - 0.5) < 1e-12
hand = N(0.5 * math.sqrt(99) / math.sqrt(1 + (3 - 1) / 4 * 0.25))                   # skew 0, kurt 3
assert abs(ST.psr(0.5, 0.0, 100, 0.0, 3.0) - hand) < 1e-12
assert ST.psr(0.5, 0.0, 100, -1.0, 3.0) < ST.psr(0.5, 0.0, 100, 0.0, 3.0) < ST.psr(0.5, 0.0, 100, 1.0, 3.0)   # skew matters
d = [ST.dsr(0.4, 93, -0.2, 3.0, n) for n in (1, 10, 100, 332, 1000)]
assert all(a > b for a, b in zip(d, d[1:])) and abs(d[0] - ST.psr(0.4, 0.0, 93, -0.2, 3.0)) < 1e-12   # N = 1: no deflation
x = np.random.default_rng(3).normal(0.02, 0.05, 93)
info = ST.dsr_of_series(x, 332)
assert info["t"] == 93 and abs(info["sr"] - x.mean() / x.std(ddof=1)) < 1e-12 and 0 < info["dsr"] < info["psr0"] <= 1
sk, ku = ST.skew_kurt(np.random.default_rng(4).normal(0, 1, 200000))
assert abs(sk) < 0.02 and abs(ku - 3) < 0.05
pbos = [ST.pbo_cscv(np.random.default_rng(s).normal(0, 1, (96, 40)), 12)["pbo"] for s in range(24)]
assert 0.35 < float(np.mean(pbos)) < 0.65, np.mean(pbos)                           # noise only: about one half
dom = np.random.default_rng(5).normal(0, 1, (96, 40))
dom[:, 3] += 0.8
assert ST.pbo_cscv(dom, 12)["pbo"] < 0.1                                           # a truly better strategy: PBO near zero
assert ST.pbo_cscv(dom, 12)["n_comb"] == math.comb(12, 6)

# ---------------------------------------------------------------- 4. vault
state = TZ.load()
assert state["od"] == "2026-10-01" and state["otevreno"] is False                  # the tracked state: closed
F = SimpleNamespace(P=P)
data = Path(tempfile.mkdtemp(prefix="fxbot_i1_d_"))
vault_file = tmp / "trezor.json"
orig = TZ.TREZOR
try:
    with S.dirs_core(data):
        S.zapis_data(F, data, symbols=("EUR/USD",))
        vault_file.write_text(json.dumps({"od": "2015-06-01", "otevreno": False, "historie": []}))
        TZ.TREZOR = vault_file
        whole = P.series("EUR/USD", vault=False)
        cut = P.series("EUR/USD")
        assert cut["days"][-1].isoformat() < "2015-06-01" <= whole["days"][len(cut["days"])].isoformat()
        n = len(cut["days"])
        assert len(whole["days"]) > n and all(len(cut[k]) == n for k in ("first", "last", "do", "dh", "dl", "dc", "close_ts"))
        assert int(cut["last"][-1]) == len(cut["ts"]) - 1 and all(len(cut[k]) == len(cut["ts"]) for k in ("o", "h", "l", "c"))
        assert np.array_equal(cut["dc"], whole["dc"][:n]) and np.array_equal(cut["c"], whole["c"][:len(cut["c"])])
        assert int(cut["ts"][-1]) < int(whole["ts"][int(whole["first"][n])])                        # nothing of a locked day remains
        raw_cut, raw_all = P.load_hourly("EUR/USD"), P.load_hourly("EUR/USD", vault=False)         # the raw loader is locked too
        from datetime import date as _d
        from src.path_archive import trading_date
        k = len(raw_cut["ts"])
        assert len(cut["ts"]) <= k < len(raw_all["ts"]) and all(len(v) == k for v in raw_cut.values())
        assert trading_date(int(raw_cut["ts"][-1])) < _d(2015, 6, 1) <= trading_date(int(raw_all["ts"][k]))   # exactly at the lock
        vault_file.write_text(json.dumps({"od": "2015-06-01", "otevreno": True, "historie": []}))
        assert len(P.series("EUR/USD")["days"]) == len(whole["days"])                             # open vault = everything
        vault_file.write_text(json.dumps({"od": "2015-06-01", "otevreno": False, "historie": []}))
        TZ.TREZOR = tmp / "chybi.json"
        assert len(P.series("EUR/USD")["days"]) == len(whole["days"])                             # no file = no lock
        TZ.TREZOR = vault_file
        assert TZS.main(["otevri", "--soubor", str(vault_file)]) == 2                               # no consent text: refused
        assert TZS.main(["otevri", "--soubor", str(vault_file), "--souhlas", "ano"]) == 2          # too short to be a quote
        assert json.loads(vault_file.read_text())["otevreno"] is False
        assert TZS.main(["otevri", "--soubor", str(vault_file), "--souhlas", "Uzivatel 2027-01-05: otevri trezor"]) == 0
        opened = json.loads(vault_file.read_text())
        assert opened["otevreno"] is True and opened["historie"][0]["souhlas"].startswith("Uzivatel 2027")
        assert TZS.main(["otevri", "--soubor", str(vault_file), "--souhlas", "Uzivatel 2027-01-06: znovu"]) == 2   # only once
finally:
    TZ.TREZOR = orig
# nobody but scripts/trezor.py asks for the data behind the lock
users = []
for path in list((PROJECT_ROOT / "scripts").glob("*.py")) + list((PROJECT_ROOT / "src").rglob("*.py")):
    text = path.read_text(encoding="utf-8")
    if re.search(r"(series|load_hourly)\([^)]*vault\s*=\s*False", text):
        users.append(path.name)
assert sorted(users) == ["market.py", "trezor.py"], users          # market: the cache keeps the whole file; trezor.py: the status

# ---------------------------------------------------------------- 5. the analysis helpers (scripts/faze2_analyza.py)
import faze2_analyza as FA  # noqa: E402

assert FA.window_months((2019, 2022))[0] == "2019-01" and len(FA.window_months((2019, 2022))) == 48
assert FA.window_months((2023, 2026))[-1] == "2026-09" and len(FA.window_months((2023, 2026))) == 45     # nothing from the vault
rng = np.random.default_rng(9)
good = list(rng.normal(0.03, 0.05, 93))
desc = FA.describe({"vynosy": good})
dsr_by_n = [desc["dsr_podle_poctu_pokusu"][str(n)]["dsr"] for n in (1, 10, 100, 1000)]
assert all(a > b for a, b in zip(dsr_by_n, dsr_by_n[1:])) and desc["t"] == 93
assert "pozn" in FA.describe({"vynosy": [0.0] * 93})                                  # a series that never trades
champ = {"rada": {"vynosy": good}}
variants = {f"v{k}": {"klic": f"k{k}", "rada": {"vynosy": list(rng.normal(0.0, 0.05, 93))}} for k in range(30)}
variants["duplikat"] = dict(variants["v1"])                                           # same configuration: counted once
variants["nelze"] = {"chyba": "KeyError: x"}
variants["nikdy_neobchoduje"] = {"klic": "n", "rada": {"vynosy": [0.0] * 93}}
res = FA.pbo_for(champ, variants, blocks=(8,))
assert res["strategii"] == 31 and res["mesicu"] == 93 and 0.0 <= res["pbo"]["8"]["pbo"] <= 1.0
assert res["pocet_lepsich_nez_sampion"] == 0 and res["sr_mesicni_sampion"] > res["sr_mesicni_nejlepsi_varianta"]
eff = FA.effective_trials(champ, variants)
assert eff["variant"] == 30 and 1.0 <= eff["efektivni_pocet_pokusu"] <= 30.0 and abs(eff["prumerna_korelace"]) < 0.5
assert FA._needed_sr(93, np.array(good), 332) > ST.expected_max_sr(332, 1 / 92)

print("=" * 60)
print("I1 RESEARCH HYGIENE (R-049)")
print("=" * 60)
print("HASH CHAIN: EDIT / DELETE / REORDER DETECTED, APPEND KEEPS IT VALID: PASS")
print(f"TRIAL REGISTRY: {len(real)} LOGGED TRIALS IMPORTED IN ORDER, 8 ACCEPTED, INTACT CHAIN, MANDATORY FIELDS: PASS")
print("PSR / DSR / EXPECTED MAXIMUM / PBO (CSCV) AGAINST CLOSED FORMS AND SIMULATION: PASS")
print("VAULT: CUT AT THE DATE, OPEN = WHOLE, OPENING NEEDS CONSENT AND WORKS ONCE, NO OTHER USER: PASS")
print("ANALYSIS HELPERS: MONTH WINDOWS END BEFORE THE VAULT, DSR FALLS WITH N, PBO / EFFECTIVE TRIALS ON SIMULATED VARIANTS: PASS")
print("RESULT: PASS")
print("=" * 60)
