"""Zmrazeni novych pokusu brany uceni (R-047, architektura-v2, faze 0).

Testovaci roky 2019-26 jsou opotrebovane (docs/CHANGE_LOG.md, R-047), proto se do `EXPERIMENTS` ve
scripts/self_learn.py nesmi pridat zadny novy pokus, dokud uzivatel zmrazeni nezrusi. Zmrazeni je
v learning/zmrazeni_pokusu.json: `aktivni` a seznam `povolene_pokusy` = nazvy, ktere v dobe zmrazeni
v `EXPERIMENTS` byly (vsechny uz probehly v obou profilech).

Modul nic nepocita a nema zavislost na datech, aby ho mohly pouzit self_learn, diagnostika i test.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOUBOR = PROJECT_ROOT / "learning" / "zmrazeni_pokusu.json"
SELF_LEARN = PROJECT_ROOT / "scripts" / "self_learn.py"


def nacti(soubor: Path = SOUBOR) -> dict | None:
    """Obsah souboru zmrazeni, nebo None, kdyz soubor neexistuje."""
    if not soubor.exists():
        return None
    return json.loads(soubor.read_text(encoding="utf-8"))


def aktivni(soubor: Path = SOUBOR) -> bool:
    data = nacti(soubor)
    return bool(data and data.get("aktivni"))


def nove_pokusy(nazvy: list[str], soubor: Path = SOUBOR) -> list[str]:
    """Nazvy z `nazvy`, ktere nejsou mezi povolenymi (prazdne, kdyz zmrazeni neplati)."""
    data = nacti(soubor)
    if not data or not data.get("aktivni"):
        return []
    povolene = set(data.get("povolene_pokusy", []))
    return [n for n in nazvy if n not in povolene]


def otisk(nazvy: list[str]) -> str:
    """SHA-256 serazeneho seznamu nazvu (kontrola, ze se seznam povolenych nezmenil napul)."""
    return hashlib.sha256("\n".join(sorted(nazvy)).encode("utf-8")).hexdigest()


def nazvy_ze_zdrojaku(cesta: Path = SELF_LEARN) -> list[str]:
    """Nazvy pokusu z literalu `EXPERIMENTS` bez importu self_learn (zadna data, zadne vedlejsi ucinky)."""
    strom = ast.parse(cesta.read_text(encoding="utf-8"))
    for uzel in ast.walk(strom):
        if isinstance(uzel, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "EXPERIMENTS" for t in uzel.targets):
            return [e.elts[0].value for e in uzel.value.elts]
    raise ValueError("EXPERIMENTS ve self_learn.py nenalezen")


def zprava_poruseni(nove: list[str]) -> str:
    return (f"ZMRAZENO (R-047): v EXPERIMENTS jsou nove pokusy {', '.join(nove)}. Testovaci roky 2019-26 jsou "
            "opotrebovane, nove pokusy se nepridavaji, dokud uzivatel zmrazeni nezrusi (learning/zmrazeni_pokusu.json, "
            "docs/CHANGE_LOG.md R-047). Odeber je z EXPERIMENTS.")
