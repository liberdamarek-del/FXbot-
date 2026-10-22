"""Append-only zaznamy s retezcem otisku (hash chain): zaklad registru pokusu (R-049, architektura-v2, faze 2).

Stejne schema jako denik predikci heuristik (scripts/heuristiky.py): kazdy radek JSON ma `hash_pred` (otisk predchoziho
radku) a `hash` = sha256(hash_pred + obsah radku bez `hash`). Upravit nebo smazat radek uprostred (nebo promenit jeho
obsah) znamena, ze overeni najde nesoulad; pridat lze jen na konec. Modul nic nepocita a nema zavislost na datech.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

GENESIS = "0" * 64


def record_hash(rec: dict, prev: str) -> str:
    body = json.dumps({k: v for k, v in rec.items() if k != "hash"}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def last_hash(path: Path) -> str:
    rows = read(path)
    return rows[-1]["hash"] if rows else GENESIS


def append(path: Path, records: list[dict]) -> list[dict]:
    """Appends `records` (dicts without hash fields) to the end of the chain and returns them with their hashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = last_hash(path)
    out = []
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            r = {k: v for k, v in rec.items() if k not in ("hash", "hash_pred")}
            r["hash_pred"] = prev
            r["hash"] = record_hash(r, prev)
            prev = r["hash"]
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
            out.append(r)
    return out


def verify(path: Path) -> dict:
    """Integrity of the whole chain: every record matches its content and the previous record."""
    prev, n = GENESIS, 0
    for n, rec in enumerate(read(path), 1):
        if rec.get("hash_pred") != prev or record_hash(rec, prev) != rec.get("hash"):
            return {"ok": False, "n": n, "chyba": f"zaznam {n} nesedi s retezcem"}
        prev = rec["hash"]
    return {"ok": True, "n": n, "posledni_hash": prev}
