"""Helpers for the GitHub Actions runs (R-050 / R-051, user's decisions 2026-10-22; .github/workflows/fxbot-*.yml,
docs/GITHUB_PROVOZ.md).

    python scripts/github_beh.py plan            # keys of the runs due now -> GITHUB_OUTPUT (denni, patek, uceni, hodina)
    python scripts/github_beh.py rezim           # stin / ostry from learning/provoz/github.json -> GITHUB_OUTPUT
    python scripts/github_beh.py zapis DRUH      # heartbeat learning/provoz/github_beh.json (committed only when ostry)
    python scripts/github_beh.py souhrn DRUH     # summary of data/live/stav.json -> GITHUB_STEP_SUMMARY, stdout and
                                                 # zprava/oznameni.json (what the phone notification would say, and
                                                 # whether it is sent at all)
    python scripts/github_beh.py oznam DRUH      # send zprava/oznameni.json via ntfy.sh (only with the secret FXBOT_NTFY_TEMA)
    python scripts/github_beh.py oznam-chyba DRUH   # a failed run (only denni / patek / uceni; an hourly failure is
                                                    # retried by the next hour and the page shows stale data)
    python scripts/github_beh.py sampion         # the champion's rule must not change while trials are frozen (R-047)

GitHub cron runs in UTC and can start late or be dropped under load, so every workflow has several schedule slots and
runs only when its run is still missing: the key of a run is the period it belongs to, and a cache entry with that
key marks it as done (the workflow looks it up before running and saves it after success).
  denni   the last daily FX close (17:00 New York, Monday to Friday) that has already passed;
  patek   on Friday from 16:00 New York the Friday decision (signals_live.decision_ready), else empty;
  uceni   the Prague date (Wednesday / Saturday learning);
  hodina  the UTC hour (R-051: hourly refresh Monday to Friday, only in the "ostry" mode).
Mode (learning/provoz/github.json): "stin" = shadow run next to the Claude routines (publishes the page, commits
nothing - two writers would break the append-only heuristics ledger), "ostry" = the only writer (commits learning/).

Notifications (R-051): the daily and Friday runs always send a short summary, learning a low-priority one; an hourly
run only when something new happened - a model trade opened or closed (learning/forward_trades.json against the last
commit) or a diagnostics CHYBA that the last run did not have. The user's own trades are not known here (his journal
lives only in his browser).
"""
from __future__ import annotations

import json
import os
import subprocess
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
FORWARD = ROOT / "learning" / "forward_trades.json"
STAV = ROOT / "data" / "live" / "stav.json"
DIAG = ROOT / "data" / "live" / "diagnostika.json"
NOTE = ROOT / "zprava" / "oznameni.json"
MODES = ("stin", "ostry")
KINDS = ("denni", "patek", "uceni", "hodina")
EXIT_CZ = {"TP": "na cíli (TP)", "SL": "na stop lossu (SL)", "pred rozhodnutim CB": "před rozhodnutím centrální banky",
           "sazby se otocily proti obchodu": "protože se sazby otočily proti obchodu", "cas": "po uplynutí doby držení"}


def keys(now: datetime) -> dict:
    t = now.astimezone(NEW_YORK)
    d = t.date()
    while not (d.weekday() < 5 and datetime.combine(d, time(17, 0), NEW_YORK) <= t):
        d -= timedelta(days=1)
    friday = t.weekday() == 4 and t.time() >= time(16, 0)
    return {"denni": d.isoformat(), "patek": t.date().isoformat() if friday else "",
            "uceni": now.astimezone(PRAGUE).date().isoformat(),
            "hodina": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")}


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


def committed(rel: str):
    """A tracked JSON file as of the last commit (the previous run in the "ostry" mode), or None."""
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def model_changes(before: list | None, after: list) -> list[str]:
    """Model trades opened or closed between two versions of learning/forward_trades.json."""
    old = {t["id"]: t for t in (before or [])}
    out = []
    for t in after:
        o = old.get(t["id"])
        name = f"{t['par']} {t['smer']}"
        if o is None:
            out.append(f"Model otevřel {name} (vstup {t.get('vstup')}, TP {t.get('tp')}, SL {t.get('sl')}).")
        elif o.get("stav") != "uzavreny" and t.get("stav") == "uzavreny":
            how = EXIT_CZ.get(t.get("duvod_vystupu"), str(t.get("duvod_vystupu") or "z neznámého důvodu"))
            res = t.get("vysledek_proc_marze")
            out.append(f"Model zavřel {name} {how}: " + (f"{res:+.1f} % marže." if isinstance(res, (int, float)) else "výsledek NEOVĚŘENO."))
    return out


def new_errors(current: list[str], beat_before: dict | None) -> list[str]:
    """Diagnostics errors that the last recorded run (any kind) did not have."""
    runs = [v for v in (beat_before or {}).values() if isinstance(v, dict) and v.get("cas")]
    last = max(runs, key=lambda v: v["cas"]) if runs else {}
    seen = set((last.get("diagnostika") or {}).get("chyby") or [])
    return [e for e in current if e not in seen]


def summary(kind: str) -> dict:
    """{title, lines, priority, poslat} - short and plain, like the Claude routine reports (signals, the model's trades,
    errors); `poslat` = whether this run sends a phone notification at all."""
    if not STAV.exists():
        return {"title": "FXBOT: běh bez výsledku", "lines": ["data/live/stav.json chybí – běh selhal před aktualizací."],
                "priority": 4, "poslat": kind != "hodina"}
    s = json.loads(STAV.read_text(encoding="utf-8"))
    d = s.get("diagnostika") or {}
    errors = [e for e in (d.get("problemy") or []) if e] if (d.get("souhrn") or {}).get("CHYBA") else []
    sig = s.get("signaly") or []
    lines = []
    for g in sig:
        tps = " / ".join(str(t["cena"]) for t in (g.get("plan") or {}).get("tp", []))
        r = g.get("riziko") or {}
        lines.append(f"{g['par']} {g['smer']} ({g.get('stupen')}): vstup {g.get('vstup')}, TP {tps}, SL {g.get('sl')}"
                     + (f", marže {r.get('marze_proc_uctu')} % účtu při riziku {r.get('riziko_proc')} %"
                        if r.get("marze_proc_uctu") is not None else ""))
    changes = model_changes(committed("learning/forward_trades.json"),
                            json.loads(FORWARD.read_text(encoding="utf-8")) if FORWARD.exists() else [])
    lines += changes
    m = s.get("model") or {}
    opened = [o for o in m.get("obchody", []) if o.get("stav") == "otevreny"]
    lines.append(f"Model: otevřené {len(opened)}, uzavřené {m.get('uzavrenych')}, ziskové {m.get('ziskovych')}.")
    fresh_errors = new_errors(errors, committed("learning/provoz/github_beh.json"))
    if errors:
        lines.append("CHYBA diagnostiky: " + "; ".join(errors)[:300])
    if kind == "patek" or (kind != "hodina" and s.get("je_patek")):
        title = f"FXBOT pátek: {len(sig)} signál(y)" if sig else "FXBOT pátek: žádný signál"
    elif kind == "uceni":
        title = "FXBOT učení proběhlo"
    elif kind == "hodina":
        title = "FXBOT: změna u obchodů modelu" if changes else "FXBOT: nová chyba"
    else:
        title = "FXBOT denní běh" + (f": {len(sig)} signál(y)" if sig else "")
    send = kind in ("denni", "patek", "uceni") or bool(changes) or bool(fresh_errors)
    priority = 4 if errors or kind == "patek" or changes else (2 if kind == "uceni" else 3)
    return {"title": title, "lines": lines, "priority": priority, "poslat": send}


def post(msg: dict) -> int:
    topic = os.environ.get("FXBOT_NTFY_TEMA", "").strip()
    if not topic:
        print("oznameni: tema ntfy neni nastavene (secret FXBOT_NTFY_TEMA) - nic se neposila")
        return 0
    body = {"topic": topic, "title": msg["title"], "message": "\n".join(msg["lines"]) or msg["title"],
            "priority": int(msg.get("priority", 3))}
    if os.environ.get("FXBOT_STRANKA_URL"):
        body["click"] = os.environ["FXBOT_STRANKA_URL"]
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")    # JSON publish keeps UTF-8
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"oznameni: odeslano ({r.status})")
    except Exception as exc:                                            # a notification never fails the run
        print(f"oznameni: neodeslano ({type(exc).__name__}: {exc})")
    return 0


def notify(kind: str) -> int:
    msg = json.loads(NOTE.read_text(encoding="utf-8")) if NOTE.exists() else summary(kind)
    if not msg.get("poslat"):
        print("oznameni: nic noveho - neposila se")
        return 0
    return post(msg)


def notify_failure(kind: str) -> int:
    if kind == "hodina":
        print("oznameni: hodinovy beh selhal - zkusi to dalsi hodina, neposila se")
        return 0
    url = os.environ.get("FXBOT_BEH_URL", "")
    what = {"denni": "Denní běh", "patek": "Páteční běh se signály", "uceni": "Učení"}.get(kind, "Běh")
    return post({"title": f"FXBOT: {what} selhal", "priority": 5 if kind == "patek" else 4,
                 "lines": [f"{what} na GitHubu skončil chybou. Stránka ukazuje poslední úspěšná data.",
                           f"Podrobnosti: {url}" if url else "Podrobnosti: GitHub → Actions."]})


def champion_unchanged() -> int:
    """While new trials are frozen (R-047) a learning run only re-evaluates the champion; its rule (`config`) must not
    change. If it did, the follow-up steps of CLAUDE.md (champion_report, pair_stats, riziko_lab, kontrola_histdata)
    would be needed - they are not automated here, so the run stops before anything is committed or published."""
    changed = []
    for name in ("champion_12.json", "champion_12_mesicne.json"):
        old, path = committed(f"learning/{name}"), ROOT / "learning" / name
        if old is None or not path.exists():
            changed.append(f"{name}: chybí")
        elif old.get("config") != json.loads(path.read_text(encoding="utf-8")).get("config"):
            changed.append(f"{name}: změnilo se pravidlo šampiona")
    for c in changed:
        print(f"CHYBA {c} - zmrazeni pokusu (R-047) to nemelo dovolit; dalsi kroky podle CLAUDE.md udela clovek")
    print("sampion beze zmeny" if not changed else "")
    return 1 if changed else 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    kind = argv[1] if len(argv) > 1 else "denni"
    now = datetime.now(timezone.utc)
    if cmd == "plan":
        output(keys(now))
        return 0
    if cmd == "rezim":
        output({"rezim": mode()})
        return 0
    if cmd == "zapis":
        heartbeat(kind, now)
        return 0
    if cmd == "souhrn":
        msg = summary(kind)
        NOTE.parent.mkdir(parents=True, exist_ok=True)
        NOTE.write_text(json.dumps(msg, ensure_ascii=False, indent=1), encoding="utf-8")
        text = f"### {msg['title']}\n\n" + "\n".join(f"- {x}" for x in msg["lines"]) + \
               f"\n\n_oznámení na telefon: {'ano' if msg['poslat'] else 'ne (nic nového)'}_\n"
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text)
        print(text)
        return 0
    if cmd == "oznam":
        return notify(kind)
    if cmd == "oznam-chyba":
        return notify_failure(kind)
    if cmd == "sampion":
        return champion_unchanged()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
