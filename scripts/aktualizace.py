"""Hourly update of the dashboard data (weekdays, routine): diagnostics, live
signals and plans, this week's economic calendar, the user's journal, the heuristic
layer (scripts/heuristiky.py: new live predictions, evaluation of finished ones).

    python scripts/aktualizace.py                  # -> data/live/stav.json (+ forward test)
    python scripts/aktualizace.py --denik DIR      # only the journal: JSON files exported from the
                                                   # dashboard (ArtifactData list denik, out_dir) ->
                                                   # data/live/denik_uzivatele.json + stav.json

The calendar (nfs.faireconomy.media, the ForexFactory week feed: time, currency,
impact, forecast, previous; no actual values) is information only: the rule
does not use it until a calendar filter passes the walk-forward gate. Every
download is archived in the fundamentals store (src/fundamental/calendar.py),
so the event history grows from 2026-09-30 on. Read-only towards brokers.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import diagnostika as DG  # noqa: E402
import profit_lab2 as P  # noqa: E402
import signals_live as SL  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

UTC = timezone.utc
PRAGUE = ZoneInfo("Europe/Prague")
STAV = PROJECT_ROOT / "data" / "live" / "stav.json"
JOURNAL = PROJECT_ROOT / "data" / "live" / "denik_uzivatele.json"   # not in git (personal data)
CURRENCIES = ("USD", "EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD")
IMPACT_CZ = {"High": "vysoký", "Medium": "střední"}
DAYS_CZ = SL.DAYS_CZ


def praha(ts: int) -> str:
    t = datetime.fromtimestamp(ts, tz=PRAGUE)
    return f"{DAYS_CZ[t.weekday()]} {t.day}. {t.month}. {t:%H:%M}"


def calendar(now: datetime) -> tuple[list[dict], dict]:
    """Medium/high impact events of the 8 currencies from now to +7 days, and
    per pair the high-impact events of its currencies in the next 24 hours."""
    from src.fundamental.calendar import events_between, update_calendar
    status = update_calendar(now)
    t = int(now.timestamp())
    events = events_between(t - 6 * 3600, t + 7 * 86400, CURRENCIES, "Medium")
    out = [{"cas": e.scheduled_at, "praha": praha(e.scheduled_at),
            "mena": e.currency, "udalost": e.title, "dopad": IMPACT_CZ.get(e.impact, e.impact),
            "odhad": e.forecast, "minule": e.previous, "probehlo": e.scheduled_at <= t} for e in events]
    per_pair = {}
    for pair in DEFAULT_ACTIVE:
        inst = get_instrument(pair)
        soon = [e for e in out if e["dopad"] == "vysoký" and e["mena"] in (inst.base, inst.quote)
                and t <= e["cas"] <= t + 86400]
        if soon:
            per_pair[pair] = [f"{e['praha']} {e['mena']} {e['udalost']}" for e in soon]
    if not status.get("ok"):
        print(f"kalendar: {status.get('detail')}", file=sys.stderr)
    return out, per_pair


CB_NAME = {"FED": "Fed (USD)", "ECB": "ECB (EUR)", "BOJ": "BoJ (JPY)", "BOE": "BoE (GBP)"}


def central_banks(today) -> tuple[list[dict], dict]:
    """Next scheduled decision of each central bank (scripts/fundamenty.py)
    and per pair the decisions of its currencies within 7 days."""
    import fundamenty as F
    from datetime import date, timedelta
    ev = F.load_events()
    nxt = []
    for cb, name in CB_NAME.items():
        future = [d for d in ev.get(cb, []) if d >= today.isoformat()]
        if future:
            d = date.fromisoformat(future[0])
            nxt.append({"banka": name, "den": future[0], "dni": (d - today).days,
                        "text": f"{DAYS_CZ[d.weekday()]} {d.day}. {d.month}. {d.year}"})
    per_pair = {}
    for pair in DEFAULT_ACTIVE:
        inst = get_instrument(pair)
        soon = [f"{CB_NAME[F.CB_OF[c]].split()[0]} {DAYS_CZ[date.fromisoformat(d).weekday()]} "
                f"{date.fromisoformat(d).day}. {date.fromisoformat(d).month}."
                for c in (inst.base, inst.quote) if c in F.CB_OF
                for d in ev.get(F.CB_OF[c], []) if today.isoformat() <= d <= (today + timedelta(days=7)).isoformat()]
        if soon:
            per_pair[pair] = soon
    return sorted(nxt, key=lambda x: x["den"]), per_pair


EVENT_TITLES = {"US_NFP": "Non-Farm Employment Change", "US_CPI": "CPI m/m"}
EVENT_CZ = {"FED": "rozhodnutí Fedu", "ECB": "rozhodnutí ECB", "BOJ": "rozhodnutí BoJ", "BOE": "rozhodnutí BoE",
            "US_NFP": "americká zaměstnanost (NFP)", "US_CPI": "americká inflace (CPI)"}


def research_event_notes(state: dict, events: list[dict], today) -> dict:
    """Per pair: an event in the next 3 days for which the weekly research found that the pair's current
    technical state predicted the event day's direction (scripts/vyzkum_most.py) - information only."""
    import fundamenty as F
    from datetime import date
    ev = F.load_events()
    upcoming = []                                         # (name, day)
    for name in ("FED", "ECB", "BOJ", "BOE"):
        upcoming += [(name, date.fromisoformat(d)) for d in ev.get(name, [])
                     if today <= date.fromisoformat(d) <= today + timedelta(days=3)]
    for e in events:
        for name, title in EVENT_TITLES.items():
            if e["mena"] == "USD" and e["udalost"] == title:
                d = datetime.fromtimestamp(e["cas"], tz=ZoneInfo("America/New_York")).date()
                if today <= d <= today + timedelta(days=3):
                    upcoming.append((name, d))
    out = {}
    for p in state["pary"]:
        stavy = (p.get("vyzkum") or {}).get("stavy", [])
        for r in state.get("vyzkum_pravidla", []):
            for name, d in upcoming:
                if r["par"] == p["par"] and r["udalost"] == name and r["stav"] in stavy:
                    out.setdefault(p["par"], []).append(
                        f"{DAYS_CZ[d.weekday()]} {d.day}. {d.month}. {EVENT_CZ[name]}: {p['par']} je teď ve stavu "
                        f"„{r['stav']}“ – v takových dnech historicky {'rostl' if r['smer'] > 0 else 'klesal'} víc než "
                        f"v ostatních dnech této události (n {r['n']}, t {r['t']:.1f}). Jen informace – model to "
                        "neobchoduje (testovací brána to zamítla).")
    return out


def weekly_research_summary() -> dict | None:
    """The latest weekly research archive (learning/tydenni/) in a few lines for the dashboard."""
    import gzip
    files = sorted((PROJECT_ROOT / "learning" / "tydenni").glob("*-W*.json.gz"))
    if not files:
        return None
    with gzip.open(files[-1], "rt", encoding="utf-8") as fh:
        R = json.load(fh)
    pairs = R.get("pary_vysledky", {})
    moves = sorted(((p, v["tyden"]["zmena_pct"]) for p, v in pairs.items()), key=lambda x: -abs(x[1]))
    wf = []
    for p, v in pairs.items():
        s = ((v.get("prediktivni") or {}).get("1H") or {}).get("walk_forward") or {}
        s = s.get("singles_souhrn")
        if s:
            wf.append((p, s["kladnych_obdobi"], s["obdobi"], s["podil_kladnych_podminek"], s["prumer"]))
    wf.sort(key=lambda x: -x[3])
    surprises = []
    for p, v in pairs.items():
        for e in v.get("udalosti", []):
            if e.get("actual_overeno") and e.get("surprise_trida") not in (None, "NEOVĚŘENO"):
                txt = f"{e['mena']} {e['udalost']}: {e['actual']:g} vs odhad {e['forecast']} ({e['surprise_trida']})"
                if txt not in surprises:
                    surprises.append(txt)
    return {"tyden": R["tyden"]["label"], "od": R["tyden"]["od"], "do": R["tyden"]["do"],
            "rezim": (R.get("rezim") or {}).get("stitky", []), "podklady": (R.get("rezim") or {}).get("podklady", {}),
            "meny": sorted(((R.get("faktory") or {}).get("meny") or {}).items(), key=lambda x: -x[1]),
            "nejvetsi_pohyby": [{"par": p, "zmena_pct": round(x, 2)} for p, x in moves[:5]],
            "prekvapeni": surprises[:6],
            "walk_forward_1h": [{"par": p, "kladnych": a, "obdobi": b, "podil_podminek": round(c * 100),
                                 "prumer_pct": round(m, 4)} for p, a, b, c, m in wf[:4]],
            "report": f"docs/tydenni/{R['tyden']['label']}.md"}


def read_journal(folder: Path) -> list[dict]:
    """The user's journal as exported by ArtifactData (one JSON file per entry)."""
    rows = []
    for f in sorted(folder.rglob("*.json")):
        doc = json.loads(f.read_text())
        data = doc.get("data", doc) if isinstance(doc, dict) else {}
        if not isinstance(data, dict) or "par" not in data:
            continue
        row = {k: data.get(k) for k in ("par", "smer", "vstup", "sl", "tp", "marze_kc", "poznamka", "cas_vstupu",
                                        "stav", "vystup", "cas_vystupu")}
        row["id"] = doc.get("id") or doc.get("doc_id") or f.stem
        rows.append(row)
    return sorted(rows, key=lambda r: r.get("cas_vstupu") or "")


def journal_summary(rows: list[dict], prices: dict) -> dict:
    """Closed results in % of the margin (the pair's leverage, ESMA) and open trades with the
    current price; flags open trades whose price is beyond their SL or TP."""
    def pct(r, price):
        side = 1 if r["smer"] == "KOUPIT" else -1
        return side * (price - r["vstup"]) / r["vstup"] * 100 * P.leverage(r["par"])
    closed = [r for r in rows if r.get("stav") == "uzavreny" and r.get("vystup") and r.get("vstup")]
    results = [pct(r, r["vystup"]) for r in closed]
    open_ = []
    for r in rows:
        if r.get("stav") == "uzavreny" or not r.get("vstup") or r["par"] not in prices:
            continue
        price, side = prices[r["par"]], 1 if r["smer"] == "KOUPIT" else -1
        hit = None
        if r.get("sl") and side * (price - r["sl"]) <= 0:
            hit = "SL"
        elif r.get("tp") and side * (price - r["tp"]) >= 0:
            hit = "TP"
        upozorneni = None                                 # model rule R-021: exit in profit before a decision
        today = datetime.now(PRAGUE).date()
        nxt = today + timedelta(days=3 if today.weekday() == 4 else 1)
        banks = [b for d, b in SL.cb_decisions(r["par"], today, 3) if d == nxt]
        if banks and pct(r, price) > 0:
            upozorneni = (f"Zítra rozhoduje {', '.join(banks)}. Obchod je v zisku – model by ho dnes při zavření trhu "
                          "(23:00 našeho času) uzavřel.")
        open_.append({"id": r["id"], "par": r["par"], "smer": r["smer"], "vstup": r["vstup"], "cena": price,
                      "proc_marze": round(pct(r, price), 1), "zasah": hit, "upozorneni": upozorneni})
    return {"uzavrenych": len(closed), "ziskovych": sum(x > 0 for x in results),
            "prumer_proc_marze": round(sum(results) / len(results), 1) if results else None,
            "otevrene": open_}


def main(argv: list[str]) -> int:
    now = datetime.now(UTC)
    if "--denik" in argv:
        rows = read_journal(Path(argv[argv.index("--denik") + 1]))
        JOURNAL.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        state = json.loads(STAV.read_text())
        state["denik_uzivatele"] = journal_summary(rows, {p["par"]: p["cena"] for p in state["pary"] if "cena" in p})
        STAV.write_text(json.dumps(state, indent=1, ensure_ascii=False, default=str))
        s = state["denik_uzivatele"]
        print(f"denik: {len(rows)} zapisu, uzavreno {s['uzavrenych']}, otevreno {len(s['otevrene'])}"
              + "".join(f"; {o['par']} {o['smer']} zasah {o['zasah']}" for o in s["otevrene"] if o["zasah"])
              + "".join(f"; {o['par']}: {o['upozorneni']}" for o in s["otevrene"] if o.get("upozorneni")))
        return 0
    diag = DG.run(online=False)
    SL.main()
    state = json.loads(STAV.read_text())
    try:
        events, per_pair = calendar(now)
    except Exception as exc:                              # the calendar is information only
        print(f"kalendar nedostupny: {type(exc).__name__}: {exc}", file=sys.stderr)
        events, per_pair = [], {}
    state["udalosti"] = events
    banks, bank_pairs = central_banks(now.astimezone(PRAGUE).date())
    state["centralni_banky"] = banks
    for p in state["pary"]:
        if p["par"] in per_pair:
            p["udalosti_24h"] = per_pair[p["par"]]
        if p["par"] in bank_pairs:
            p["banka_7_dni"] = bank_pairs[p["par"]]
    try:
        notes = research_event_notes(state, events, now.astimezone(ZoneInfo("America/New_York")).date())
    except Exception as exc:                              # research is information only
        print(f"vyzkum (udalosti) nedostupny: {type(exc).__name__}: {exc}", file=sys.stderr)
        notes = {}
    for p in state["pary"]:
        if p["par"] in notes:
            p["vyzkum_udalosti"] = notes[p["par"]]
    try:
        state["vyzkum_tyden"] = weekly_research_summary()
    except Exception as exc:
        print(f"tydenni vyzkum nedostupny: {type(exc).__name__}: {exc}", file=sys.stderr)
    try:                                                  # heuristic layer: information only, never blocks
        import heuristiky as HX
        state["heuristiky"] = HX.live(state, SL.HOURLY_CACHE)
    except Exception as exc:
        print(f"heuristiky nedostupne: {type(exc).__name__}: {exc}", file=sys.stderr)
        state["heuristiky"] = {"chyba": f"heuristická vrstva selhala: {type(exc).__name__}: {exc}"}
    state["diagnostika"] = {"souhrn": diag["souhrn"],
                            "problemy": [f"{r['oblast']}: {r['zprava']}" for r in diag["kontroly"] if r["stav"] != DG.OK]}
    if JOURNAL.exists():                                  # last known journal with today's prices
        rows = json.loads(JOURNAL.read_text())
        state["denik_uzivatele"] = journal_summary(rows, {p["par"]: p["cena"] for p in state["pary"] if "cena" in p})
    STAV.write_text(json.dumps(state, indent=1, ensure_ascii=False, default=str))
    high = [e for e in events if e["dopad"] == "vysoký" and not e["probehlo"]]
    hx = state.get("heuristiky") or {}
    print(f"aktualizace {now:%Y-%m-%d %H:%M} UTC | signalu {len(state['signaly'])} | udalosti (vysoky dopad) "
          f"do 7 dni: {len(high)} | diagnostika {diag['souhrn']} | heuristiky: nove {hx.get('nove', '-')}, "
          f"vyhodnoceno {hx.get('vyhodnocene_ted', '-')}, otevreno {hx.get('otevrene', '-')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
