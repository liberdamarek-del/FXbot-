"""Trezor testovacich dat (R-049): stav a otevreni. Pravidla viz src/core/trezor.py a docs/TREZOR.md.

    python scripts/trezor.py stav                              # od kdy je zamceno, kolik dnu u kazdeho paru
    python scripts/trezor.py otevri --souhlas "<citace uzivatele>"   # JEDNOU a jen s vyslovnym souhlasem uzivatele

Otevreni zapise cas, souhlas a pocet pokusu v registru do learning/trezor.json (`historie`) a nelze ho vratit.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from src.core import market as P  # noqa: E402
from src.core import trezor as TZ  # noqa: E402
from src.instruments import DEFAULT_ACTIVE  # noqa: E402


def status() -> int:
    state = TZ.load()
    print(f"trezor: {'OTEVRENY' if state.get('otevreno') else 'zavreny'}, zamceno od {state['od']}")
    for entry in state.get("historie", []):
        print("  historie:", entry)
    for pair in sorted(DEFAULT_ACTIVE):
        try:
            seen, whole = P.series(pair), P.series(pair, vault=False)     # the only place that looks behind the lock
        except FileNotFoundError:
            print(f"  {pair}: data nejsou stazena")
            continue
        print(f"  {pair}: vyzkum vidi do {seen['days'][-1]}, zamceno {len(whole['days']) - len(seen['days'])} obchodnich dnu "
              f"(data do {whole['days'][-1]})")
    return 0


def open_vault(path: Path, consent: str) -> int:
    if len(consent.strip()) < 15:
        print("otevreni vyzaduje --souhlas s citaci vyslovneho souhlasu uzivatele (aspon 15 znaku)", file=sys.stderr)
        return 2
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("otevreno"):
        print("trezor uz je otevreny", file=sys.stderr)
        return 2
    n = 0
    try:
        import registr_pokusu as RP
        n = RP.n_trials()
    except Exception:                                      # the opening must not depend on the registry
        pass
    state["otevreno"] = True
    state.setdefault("historie", []).append({"kdy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                             "souhlas": consent.strip(), "pokusu_v_registru": n})
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("trezor otevreny:", state["historie"][-1])
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "stav"
    if cmd == "stav":
        return status()
    if cmd == "otevri":
        consent = argv[argv.index("--souhlas") + 1] if "--souhlas" in argv else ""
        path = Path(argv[argv.index("--soubor") + 1]) if "--soubor" in argv else TZ.TREZOR     # --soubor: only for tests
        return open_vault(path, consent)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
