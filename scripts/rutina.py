"""Routine runner for FRESH routine sessions (R-044, user's decision 2026-10-11: every routine starts a new small
session instead of firing into the long main conversation - far fewer tokens per run).

A fresh session has the repository but no data/ (market data are not in git). This script prepares exactly what a
job needs, runs the deterministic steps and prints a short summary for the report, so the session itself only does
the steps that need tools (ArtifactData, git commit / push, the learning decisions).

    python scripts/rutina.py denni           # daily update / Friday signals: rates, aktualizace (lean, no history)
    python scripts/rutina.py denik <dir>     # the user's journal from ArtifactData list -> stav, summary
    python scripts/rutina.py uceni           # learning: + FXCM history of the 12 pairs (~1.5 min, identical to a
                                             #   full download), fundamentals, rates
    python scripts/rutina.py souhrn          # the short summary of data/live/stav.json again

Each run writes learning/provoz/posledni_beh.json (tracked): when which routine ran and its diagnostics, so a
missed or failed run is visible in git.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
STAV = ROOT / "data" / "live" / "stav.json"
BEH = ROOT / "learning" / "provoz" / "posledni_beh.json"
FXCM = ROOT / "data" / "research" / "fxcm_h1"


def sh(args: list[str], env: dict | None = None, quiet: bool = True) -> int:
    """Run a step; on failure print the tail of its output (the report needs the reason, not the whole log)."""
    r = subprocess.run(args, cwd=ROOT, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    if r.returncode or not quiet:
        tail = (r.stdout + r.stderr).strip().splitlines()[-15:]
        print(f"{'CHYBA' if r.returncode else 'ok'}: {' '.join(args[1:])}\n  " + "\n  ".join(tail))
    return r.returncode


def git_identity() -> None:
    for k, v in (("user.name", "Claude"), ("user.email", "noreply@anthropic.com")):
        subprocess.run(["git", "config", k, v], cwd=ROOT, check=False)


def rates() -> int:
    return sh([PY, "-c", "import sys; sys.path.insert(0, 'scripts'); import signals_live; signals_live.refresh_rates()"])


def history() -> int:
    """FXCM hourly history of the 12 live pairs (download, build, minute fill of empty weeks, build again)."""
    rc = 0
    for step in ("download", "build", "fill_m1", "build"):
        rc |= sh([PY, "scripts/fxcm_universe.py", step, "--jen-12"])
    return rc


def lean_env() -> dict:
    return {} if (FXCM / "EURUSD.npz").exists() else {"FXBOT_LEHKY": "1"}


def heartbeat(kind: str) -> None:
    diag = {}
    path = ROOT / "data" / "live" / "diagnostika.json"
    if path.exists():
        d = json.loads(path.read_text())
        diag = {"souhrn": d["souhrn"], "chyby": [f"{c['oblast']}: {c['zprava']}" for c in d["kontroly"]
                                                if c.get("stav") == "CHYBA"][:10]}
    BEH.parent.mkdir(parents=True, exist_ok=True)
    BEH.write_text(json.dumps({"cas": datetime.now(timezone.utc).isoformat(timespec="minutes"), "rutina": kind,
                               "lehky": bool(lean_env()), "diagnostika": diag}, indent=1, ensure_ascii=False) + "\n")


def summary() -> None:
    if not STAV.exists():
        print("stav.json chybi")
        return
    s = json.loads(STAV.read_text())
    d = s.get("diagnostika") or {}
    print(f"STAV {s['aktualizovano']} | data do {s['den_dat']} | patek: {s.get('je_patek')}")
    if isinstance(d, dict) and d.get("souhrn"):
        print(f"DIAGNOSTIKA {d['souhrn']}")
    path = ROOT / "data" / "live" / "diagnostika.json"
    for c in (json.loads(path.read_text())["kontroly"] if path.exists() else []):
        if c.get("stav") == "CHYBA":
            print(f"  CHYBA {c.get('oblast')}: {c.get('zprava')}")
    sig = s.get("signaly") or []
    print(f"SIGNALY {len(sig)}")
    for g in sig:
        tps = " / ".join(str(t["cena"]) for t in (g.get("plan") or {}).get("tp", []))
        r = g.get("riziko") or {}
        print(f"  {g['par']} {g['smer']} ({g['stupen']}) vstup {g['vstup']} | TP1-3 {tps} | SL {g['sl']} | "
              f"pravdepodobnost {g.get('pravdepodobnost_uspechu')} | pri riziku {r.get('riziko_proc')} %: marze "
              f"{r.get('marze_proc_uctu')} % uctu, ztrata pri SL {r.get('ztrata_sl_proc_uctu')} % uctu"
              + (f" | {g['plan']['pred_rozhodnutim']}" if (g.get("plan") or {}).get("pred_rozhodnutim") else ""))
    m = s.get("model") or {}
    for o in m.get("obchody", []):
        if o.get("stav") == "otevreny":
            print(f"MODEL otevreny {o['par']} {o['smer']} od {o['den']}: {o.get('prubezne_proc_marze')} % marze")
    print(f"MODEL uzavreno {m.get('uzavrenych')}, ziskovych {m.get('ziskovych')}, prumer {m.get('prumer_proc_marze')} % marze")
    j = s.get("denik_uzivatele") or {}
    print(f"DENIK uzavreno {j.get('uzavrenych')}, ziskovych {j.get('ziskovych')}, otevreno {len(j.get('otevrene', []))}")
    for o in j.get("otevrene", []):
        print(f"  {o['par']} {o['smer']} {o.get('proc_marze')} % marze" + (f" | ZASAH {o['zasah']}" if o.get("zasah") else "")
              + (f" | {o['upozorneni']}" if o.get("upozorneni") else ""))
    h = s.get("heuristiky") or {}
    if h:
        print(f"HEURISTIKY nove {h.get('nove')}, vyhodnoceno ted {h.get('vyhodnocene_ted')}, otevreno {h.get('otevrene')}")


def main(argv: list[str]) -> int:
    kind = argv[0] if argv else "souhrn"
    git_identity()
    if kind == "souhrn":
        summary()
        return 0
    if kind == "denik":
        rc = sh([PY, "scripts/aktualizace.py", "--denik", argv[1]], lean_env(), quiet=False)
        summary()
        return rc
    if kind == "denni":
        rc = rates()
        rc |= sh([PY, "scripts/aktualizace.py"], lean_env())
        heartbeat("denni")
        summary()
        return rc
    if kind == "uceni":
        rc = history() | rates()
        rc |= sh([PY, "scripts/fundamenty.py", "download"])
        heartbeat("uceni")
        print("data pripravena" if not rc else "data pripravena s chybami (viz vyse)")
        return rc
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
