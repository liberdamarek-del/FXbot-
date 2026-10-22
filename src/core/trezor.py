"""Trezor (vault) testovacich dat (R-049, architektura-v2, faze 2): data od 2026-10-01 dal vyzkum nesmi cist.

Nova data jsou jediny skutecne neviděný test. Opotrebovane roky 2019-26 uz o modelu rozhodly (R-047), proto se data od
`od` zamknou: `market.series()` je v zakladu orizne (obchodni dny s datem >= `od`), takze uceni, simulator, heuristiky i
vyzkumne skripty vidi jen starsi historii. Zive signaly, forward test a zive predikce heuristik berou ceny z Yahoo a
trezor se jich netyka.

Stav je v learning/trezor.json (sledovany v gitu). Trezor se otevre JEDNOU a jen s vyslovnym souhlasem uzivatele
(`python scripts/trezor.py otevri --souhlas "..."`); otevreni se zapise do `historie` a nelze ho vratit.
"""

from __future__ import annotations

import json
from datetime import date

from . import paths

TREZOR = paths.PROJECT_ROOT / "learning" / "trezor.json"


def load() -> dict:
    return json.loads(TREZOR.read_text(encoding="utf-8"))


def boundary() -> date | None:
    """First locked trading day, or None when the vault is open (or the file does not exist)."""
    if not TREZOR.exists():
        return None
    state = load()
    return None if state.get("otevreno") else date.fromisoformat(state["od"])


def cut(s: dict) -> dict:
    """The series without the locked trading days; hourly bars are cut after the last kept day."""
    limit = boundary()
    if limit is None:
        return s
    days = s["days"]
    keep = sum(1 for d in days if d < limit)             # trading days are in time order
    if keep == len(days):
        return s
    if keep == 0:
        raise ValueError("trezor zamyka vsechna data serie")
    stop = int(s["last"][keep - 1]) + 1
    out = dict(s)
    for key in ("ts", "o", "h", "l", "c"):
        out[key] = s[key][:stop]
    out["days"] = days[:keep]
    for key in ("first", "last", "do", "dh", "dl", "dc", "close_ts"):
        out[key] = s[key][:keep]
    return out


def cut_hours(h: dict) -> dict:
    """Raw hourly arrays (`ts` and every column) without the hours of the locked trading days."""
    limit = boundary()
    if limit is None:
        return h
    from src.path_archive import trading_date
    ts = h["ts"]
    lo, hi = 0, len(ts)                                   # first hour of a locked trading day (trading days are in time order)
    while lo < hi:
        mid = (lo + hi) // 2
        if trading_date(int(ts[mid])) >= limit:
            hi = mid
        else:
            lo = mid + 1
    return h if lo == len(ts) else {k: v[:lo] for k, v in h.items()}

