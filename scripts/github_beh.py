"""Helpers for the GitHub Actions runs (R-050, user's decision 2026-10-22; .github/workflows/fxbot-*.yml, docs/GITHUB_PROVOZ.md).

    python scripts/github_beh.py plan          # keys of the runs due now -> GITHUB_OUTPUT (denni, patek, uceni)
    python scripts/github_beh.py rezim         # stin / ostry from learning/provoz/github.json -> GITHUB_OUTPUT
    python scripts/github_beh.py zapis DRUH    # heartbeat learning/provoz/github_beh.json (committed only when ostry)
    python scripts/github_beh.py souhrn DRUH   # summary of data/live/stav.json -> GITHUB_STEP_SUMMARY and stdout
    python scripts/github_beh.py oznam DRUH    # the same summary as a phone notification via ntfy.sh, only when the
                                               # secret FXBOT_NTFY_TEMA is set (otherwise nothing happens)

GitHub cron runs in UTC and can start late or be dropped under load, so every workflow has several schedule slots and
runs only when its run is still missing: the key of a run is the trading day it belongs to, and a cache entry with that
key marks it as done (the workflow looks it up before running and saves it after success).
  denni  the last daily FX close (17:00 New York, Monday to Friday) that has already passed;
  patek  on Friday from 16:00 New York the Friday decision (signals_live.decision_ready), else empty;
  uceni  the Prague date (Wednesday / Saturday learning).
Mode (learning/provoz/github.json): "stin" = shadow run next to the Claude routines (publishes the page, commits
nothing - two writers would break the append-only heuristics ledger), "ostry" = the only writer (commits learning/).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NEW_YORK = ZoneInfo("America/New_York")
PRAGUE = ZoneInfo("Europe/Prague")
MODE_FILE = ROOT / "learning" / "provoz" / "github.json"
BEAT_FILE = ROOT / "learning" / "provoz" / "github_beh.json"
STAV = ROOT / "data" / "live" / "stav.json"
DIAG = ROOT / "data" / "live" / "diagnostika.json"
MODES = ("stin", "ostry")


def keys(now: datetime) -> dict:
    t = now.astimezone(NEW_YORK)
    d = t.date()
    while not (d.weekday() < 5 and datetime.combine(d, time(17, 0), NEW_YORK) <= t):
        d -= timedelta(days=1)
    friday = t.weekday() == 4 and t.time() >= time(16, 0)
    return {"denni": d.isoformat(), "patek": t.date().isoformat() if friday else "",
            "uceni": now.astimezone(PRAGUE).date().isoformat()}


def mode() -> str:
    try:
        m = json.loads(MODE_FILE.read_text(encoding="utf-8")).get("rezim")
    except (OSError, ValueError):
        m = None
    return m if m in MODES else "stin"           # unknown or missing: never write (the safe side)


def output(pairs: dict) -> None:
    lines = [f"{k}={v}" for k, v in pairs.items()]
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def diagnostics() -> dict:
    if not DIAG.exists():
        return {}
    d = json.loads(DIAG.read_text(encoding="utf-8"))
    return {"souhrn": d.get("souhrn"),
            "chyby": [f"{c['oblast']}: {c['zprava']}" for c in d.get("kontroly", []) if c.get("stav") == "CHYBA"][:10]}


def heartbeat(kind: str, now: datetime) -> None:
    beat = {}
    if BEAT_FILE.exists():
        try:
            beat = json.loads(BEAT_FILE.read_text(encoding="utf-8"))
        except ValueError:
            beat = {}
    beat[kind] = {"cas": now.astimezone(timezone.utc).isoformat(timespec="minutes"), "klice": keys(now),
                  "beh": os.environ.get("FXBOT_BEH_URL"), "diagnostika": diagnostics()}
    BEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BEAT_FILE.write_text(json.dumps(beat, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def summary(kind: str) -> tuple[str, list[str], bool]:
    """(title, lines, urgent) - short and plain, like the Claude routine reports (signals, the model's trades, errors)."""
    if not STAV.exists():
        return "FXBOT: běh bez výsledku", ["data/live/stav.json chybí – běh selhal před aktualizací."], True
    s = json.loads(STAV.read_text(encoding="utf-8"))
    diag = (s.get("diagnostika") or {}).get("souhrn") or {}
    errors = (s.get("diagnostika") or {}).get("problemy") or []
    sig = s.get("signaly") or []
    lines = []
    for g in sig:
        tps = " / ".join(str(t["cena"]) for t in (g.get("plan") or {}).get("tp", []))
        r = g.get("riziko") or {}
        lines.append(f"{g['par']} {g['smer']} ({g.get('stupen')}): vstup {g.get('vstup')}, TP {tps}, SL {g.get('sl')}"
                     + (f", marže {r.get('marze_proc_uctu')} % účtu při riziku {r.get('riziko_proc')} %"
                        if r.get("marze_proc_uctu") is not None else ""))
    m = s.get("model") or {}
    opened = [o for o in m.get("obchody", []) if o.get("stav") == "otevreny"]
    lines.append(f"Model: otevřené {len(opened)}, uzavřené {m.get('uzavrenych')}, ziskové {m.get('ziskovych')}.")
    if diag.get("CHYBA"):
        lines.append("CHYBA diagnostiky: " + "; ".join(e for e in errors if e)[:300])
    friday = kind == "patek" or bool(s.get("je_patek"))
    if friday:
        title = f"FXBOT pátek: {len(sig)} signál(y)" if sig else "FXBOT pátek: žádný signál"
    else:
        title = "FXBOT denní běh" + (f": {len(sig)} signál(y)" if sig else "")
    return title, lines, bool(diag.get("CHYBA"))


def notify(kind: str) -> int:
    topic = os.environ.get("FXBOT_NTFY_TEMA", "").strip()
    if not topic:
        print("oznameni: tema ntfy neni nastavene (secret FXBOT_NTFY_TEMA) - nic se neposila")
        return 0
    title, lines, urgent = summary(kind)
    msg = {"topic": topic, "title": title, "message": "\n".join(lines), "priority": 4 if urgent or kind == "patek" else 3}
    if os.environ.get("FXBOT_STRANKA_URL"):
        msg["click"] = os.environ["FXBOT_STRANKA_URL"]
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(msg, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")    # JSON publish keeps UTF-8
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"oznameni: odeslano ({r.status})")
    except Exception as exc:                                            # a notification never fails the run
        print(f"oznameni: neodeslano ({type(exc).__name__}: {exc})")
    return 0


def champion_unchanged() -> int:
    """While new trials are frozen (R-047) a learning run only re-evaluates the champion; its rule (`config`) must not
    change. If it did, the follow-up steps of CLAUDE.md (champion_report, pair_stats, riziko_lab, kontrola_histdata)
    would be needed - they are not automated here, so the run stops before anything is committed or published."""
    import subprocess
    changed = []
    for name in ("champion_12.json", "champion_12_mesicne.json"):
        path = ROOT / "learning" / name
        old = subprocess.run(["git", "show", f"HEAD:learning/{name}"], cwd=ROOT, capture_output=True, text=True)
        if old.returncode or not path.exists():
            changed.append(f"{name}: chybí")
        elif json.loads(old.stdout).get("config") != json.loads(path.read_text(encoding="utf-8")).get("config"):
            changed.append(f"{name}: změnilo se pravidlo šampiona")
    for c in changed:
        print(f"CHYBA {c} - zmrazeni pokusu (R-047) to nemelo dovolit; dalsi kroky podle CLAUDE.md udela clovek")
    print("sampion beze zmeny" if not changed else "")
    return 1 if changed else 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    now = datetime.now(timezone.utc)
    if cmd == "plan":
        output(keys(now))
        return 0
    if cmd == "rezim":
        output({"rezim": mode()})
        return 0
    if cmd == "zapis":
        heartbeat(argv[1], now)
        return 0
    if cmd == "souhrn":
        title, lines, _ = summary(argv[1] if len(argv) > 1 else "denni")
        text = f"### {title}\n\n" + "\n".join(f"- {x}" for x in lines) + "\n"
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text)
        print(text)
        return 0
    if cmd == "oznam":
        return notify(argv[1] if len(argv) > 1 else "denni")
    if cmd == "sampion":
        return champion_unchanged()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
