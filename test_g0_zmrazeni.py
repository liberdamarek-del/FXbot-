"""G0 - freeze of new gate trials (R-047, architektura-v2 phase 0); no network, no price data.

learning/zmrazeni_pokusu.json lists the experiments that existed when the test years 2019-26 were declared
worn out. Nothing may be added to EXPERIMENTS in scripts/self_learn.py while the freeze is active, and
self_learn.main refuses to run when something was added.
"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_g0_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import zmrazeni as ZM  # noqa: E402

# 1. the tracked freeze file is complete and consistent
data = ZM.nacti()
assert data is not None, "learning/zmrazeni_pokusu.json chybi"
assert data["aktivni"] is True and data["od"] and data["duvod"] and data["pravidlo"]
povolene = data["povolene_pokusy"]
assert len(povolene) == len(set(povolene)) == data["pocet_povolenych"] > 0
assert ZM.otisk(povolene) == data["sha256_povolenych"], "seznam povolenych pokusu nesedi s otiskem"
assert data["pokusy_v_logu"]["celkem"] == data["pokusy_v_logu"]["prijato"] + data["pokusy_v_logu"]["zamitnuto"]

# 2. nobody added an experiment: every name in EXPERIMENTS is on the frozen list
nazvy = ZM.nazvy_ze_zdrojaku()
assert len(nazvy) == len(set(nazvy)), "EXPERIMENTS ma duplicitni nazev"
nove = ZM.nove_pokusy(nazvy)
assert not nove, f"v EXPERIMENTS jsou nove pokusy pri zmrazeni: {nove}"

# 3. the check itself: active file, inactive file, missing file
tmp = Path(tempfile.mkdtemp(prefix="fxbot_g0_f_"))
aktivni = tmp / "a.json"
aktivni.write_text(json.dumps({"aktivni": True, "povolene_pokusy": ["a", "b"]}))
neaktivni = tmp / "n.json"
neaktivni.write_text(json.dumps({"aktivni": False, "povolene_pokusy": ["a"]}))
assert ZM.nove_pokusy(["a", "b", "c"], aktivni) == ["c"]
assert ZM.nove_pokusy(["a", "x"], neaktivni) == []
assert ZM.nove_pokusy(["a", "x"], tmp / "neexistuje.json") == []
assert ZM.aktivni(aktivni) and not ZM.aktivni(neaktivni) and not ZM.aktivni(tmp / "neexistuje.json")
assert "c" in ZM.zprava_poruseni(["c"])

# 4. self_learn.main refuses to run with a new experiment and changes nothing
import self_learn as SL  # noqa: E402

stavy = [SL.PROFILES[p]["state"] for p in SL.PROFILES] + [SL.LOG]
pred = [p.read_bytes() if p.exists() else None for p in stavy]
puvodni = list(SL.EXPERIMENTS)
SL.EXPERIMENTS.append(("pokus_pridany_pri_zmrazeni", "test", lambda c: c))
try:
    chyba = io.StringIO()
    with redirect_stderr(chyba):
        kod = SL.main([])
finally:
    SL.EXPERIMENTS[:] = puvodni
assert kod == 3, f"self_learn.main mel vratit 3, vratil {kod}"
assert "pokus_pridany_pri_zmrazeni" in chyba.getvalue()
po = [p.read_bytes() if p.exists() else None for p in stavy]
assert pred == po, "self_learn.main pri zmrazeni zmenil soubory"

print("=" * 60)
print("G0 FREEZE OF NEW TRIALS (R-047)")
print("=" * 60)
print("FREEZE FILE COMPLETE, HASH MATCHES: PASS")
print("NO NEW EXPERIMENT IN self_learn.EXPERIMENTS: PASS")
print("CHECK (ACTIVE / INACTIVE / MISSING FILE): PASS")
print("self_learn.main REFUSES A NEW EXPERIMENT, FILES UNCHANGED: PASS")
print("RESULT: PASS")
print("=" * 60)
