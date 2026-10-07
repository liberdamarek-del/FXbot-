"""Health check of the live model (data freshness, inputs, state, outputs).

    python scripts/diagnostika.py            # local files only
    python scripts/diagnostika.py --online   # also Yahoo and FRED reachability

Prints one line per check: OK / VAROVANI (warning) / CHYBA (error), in Czech,
and writes the same as data/live/diagnostika.json. Exit code 1 when any check
is CHYBA. Read-only: it never downloads into the data folders, never changes
the model state and never touches the production database.
"""

import json
import pickle
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import profit_lab2 as P  # noqa: E402
import research_factors as RF  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

UTC = timezone.utc
LEARNING = PROJECT_ROOT / "learning"
LIVE = PROJECT_ROOT / "data" / "live"
CURRENCIES = sorted({c for p in DEFAULT_ACTIVE for c in (get_instrument(p).base, get_instrument(p).quote)})
OK, WARN, ERR = "OK", "VAROVANI", "CHYBA"

results: list[dict] = []


def report(area: str, status: str, text: str) -> None:
    results.append({"oblast": area, "stav": status, "zprava": text})
    print(f"[{status:8}] {area}: {text}")


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------

def check_prices(today: date) -> None:
    for pair in DEFAULT_ACTIVE:
        name = pair.replace("/", "")
        path = U.ROOT / f"{name}.npz"
        if not path.exists():
            report("ceny", ERR, f"{pair}: chybi hodinova data {path.relative_to(PROJECT_ROOT)} (spust fxcm_universe.py build)")
            continue
        last = datetime.fromtimestamp(int(np.load(path)["ts"][-1]), tz=UTC).date()
        age = (today - last).days
        status = OK if age <= 9 else WARN if age <= 16 else ERR
        cache = P.OUT / f"series_{name}.pkl"
        if cache.exists():
            cached = datetime.fromtimestamp(int(pickle.loads(cache.read_bytes())["ts"][-1]), tz=UTC).date()
            if cached < last:
                report("ceny", ERR, f"{pair}: mezipamet uceni konci {cached}, data uz {last} - uceni nevidi nova data")
                continue
        report("ceny", status, f"{pair}: posledni hodinova svicka {last} (pred {age} dny)")


def check_rates(today: date) -> None:
    rates = P.monthly_rates()
    for ccy in CURRENCIES:
        series = rates.get(ccy, {})
        if not series:
            report("sazby", ERR, f"{ccy}: zadna data sazeb OECD")
            continue
        y, m = max(series)
        last = date(y, m, 1)
        behind = months_between(last, today) - 2              # the model uses the rate 2 months back
        now_r = P.rate_at(series, today.year, today.month, 2)
        old_r = P.rate_at(series, today.year, today.month, 5)
        expiry_y, expiry_m = divmod(y * 12 + m - 1 + 12 + 2, 12)
        expiry = f"{expiry_y}-{expiry_m + 1:02d}"
        if now_r is None or old_r is None:
            report("sazby", ERR, f"{ccy}: posledni mesic {last:%Y-%m}, sazba pro model chybi - pary s {ccy} spadnou")
        elif behind >= 3:
            report("sazby", ERR, f"{ccy}: posledni mesic {last:%Y-%m} ({behind} mesice pozde), zmena za 3 mesice "
                                 f"{now_r - old_r:+.2f} je jen dopocitana; od {expiry} skript spadne")
        elif behind >= 1:
            report("sazby", WARN, f"{ccy}: posledni mesic {last:%Y-%m} ({behind} mesic pozde), zmena {now_r - old_r:+.2f}")
        else:
            report("sazby", OK, f"{ccy}: posledni mesic {last:%Y-%m}, sazba {now_r:.2f}, zmena za 3 mesice {now_r - old_r:+.2f}")
    rows = RF._csv("VIXCLS")
    if rows:
        age = (today - rows[-1][0]).days
        report("VIX", OK if age <= 5 else WARN, f"posledni hodnota {rows[-1][1]} ze dne {rows[-1][0]}")
    else:
        report("VIX", WARN, "zadna data VIX")


def check_fundamentals_db(today: date) -> None:
    db = PROJECT_ROOT / "data" / "fundamentals.sqlite3"
    if not db.exists():
        report("fundamenty", WARN, "databaze fundamentu chybi (jen informativni, model ji nepouziva)")
        return
    from src.fundamental.calendar import calendar_coverage
    from src.fundamental.store import load_series
    for ccy in CURRENCIES:
        try:
            last = load_series(f"{ccy}.POLICY").last()
        except Exception as exc:                          # informative only
            report("fundamenty", WARN, f"{ccy}: sazba centralni banky necitelna ({type(exc).__name__})")
            continue
        if last is None:
            report("fundamenty", WARN, f"{ccy}: sazba centralni banky chybi")
            continue
        age = (today - last.obs_date).days
        report("fundamenty", OK if age <= 21 else WARN, f"{ccy}: sazba centralni banky {last.value} k {last.obs_date}")
    first, last = calendar_coverage()
    if first is None:
        report("kalendar", WARN, "ekonomicky kalendar prazdny")
    else:
        days = (last - first) / 86400
        report("kalendar", WARN if days < 365 else OK,
               f"kalendar udalosti jen {days:.0f} dni historie (od {datetime.fromtimestamp(first, tz=UTC):%Y-%m-%d}) "
               "- model ho nepouziva, nelze ho zpetne otestovat")


# ----------------------------------------------------------------------
# model state and outputs
# ----------------------------------------------------------------------

LIVE_CFG = {"name", "universe", "base", "tiers", "sizing", "max_ccy", "notional_parity"}
LIVE_BASE = {"signal", "weekly", "tp", "sl", "hold_days", "exit_before_cb", "decide_h", "min_tp_price", "min_tp_pct",
             "skip_holidays"}
LIVE_TIER = {"fund", "rates_thr", "signal"}


def live_unsupported(cfg: dict) -> list[str]:
    """Options of a champion that scripts/signals_live.py does not implement (the backtest would trade a
    different rule than the live signals)."""
    bad = [k for k, v in cfg.items() if k not in LIVE_CFG and v]
    bad += [k for k, v in cfg["base"].items() if k not in LIVE_BASE and v]
    bad += [f"stupen.{k}" for t in cfg["tiers"] for k in t if k not in LIVE_TIER]
    if cfg.get("max_ccy"):
        bad.append("max_ccy")
    if cfg["base"].get("exit_before_cb") not in (None, "", "zisk"):
        bad.append(f"exit_before_cb={cfg['base']['exit_before_cb']}")
    if cfg["base"].get("weekly") is False or any(t.get("weekly") is False for t in cfg["tiers"]):
        bad.append("weekly=False")
    import signals_live as SLV
    for sig in [cfg["base"].get("signal", "")] + [t["signal"] for t in cfg["tiers"] if "signal" in t]:
        try:
            SLV.signal_parts(sig)
        except ValueError:
            bad.append(f"signal={sig}")
    return sorted(set(bad))


def check_state() -> str | None:
    name = None
    for file in ("champion_12.json", "champion_12_mesicne.json"):
        path = LEARNING / file
        if not path.exists():
            report("sampion", ERR, f"chybi {file}")
            continue
        st = json.loads(path.read_text())
        tiers, shares = st["config"]["tiers"], st["eval"]["1"]["shares"]
        status = OK if len(tiers) == len(shares) else ERR
        report("sampion", status, f"{file}: {st['config']['name']} | {len(tiers)} stupne, marze {shares}, "
                                  f"vyzkouseno {len(st['tried'])} pokusu")
        if file == "champion_12_mesicne.json":
            name = st["config"]["name"]
            import signals_live as SLV
            unknown = live_unsupported(st["config"])
            report("zivy model", ERR if unknown else OK,
                   "zivy vypocet umi vsechny volby sampiona" if not unknown else
                   f"zivy vypocet neumi volby {', '.join(unknown)} - signaly by neodpovidaly testovanemu pravidlu")
            dh = st["config"]["base"].get("decide_h", 0)
            report("cas rozhodnuti", OK if dh == SLV.DECIDE_H else ERR,
                   f"model testovan s rozhodnutim {dh} h pred zavrenim, zive {SLV.DECIDE_H} h"
                   + ("" if dh == SLV.DECIDE_H else " - vysledky z historie neplati pro zivy postup"))
    risk = LEARNING / "riziko.json"                      # stop-based sizing of the dashboard (docs/RIZIKO.md)
    if name:
        if not risk.exists():
            report("riziko", WARN, "learning/riziko.json chybi - velikost podle rizika se neukaze; spust riziko_lab.py --stupne")
        else:
            rk = json.loads(risk.read_text())
            ok = rk.get("sampion") == name
            report("riziko", OK if ok else WARN,
                   f"vahy stupnu {rk.get('vahy')}, vychozi riziko {rk.get('vychozi_riziko', 0) * 100:.0f} % uctu na obchod"
                   if ok else f"riziko.json je pro '{rk.get('sampion')}', sampion je '{name}' - spust riziko_lab.py --stupne")
    stats = LEARNING / "pair_stats.json"
    if stats.exists() and name:
        rule = json.loads(stats.read_text())["pravidlo"]
        report("statistiky paru", OK if rule == name else ERR,
               "odpovidaji sampionovi" if rule == name else f"jsou pro '{rule}', sampion je '{name}' - spust pair_stats.py")
    try:
        import self_learn as SL
        for prof, cfg in SL.PROFILES.items():
            tried = set(json.loads(cfg["state"].read_text())["tried"]) if cfg["state"].exists() else set()
            todo = [e for e, _, _ in SL.EXPERIMENTS if e not in tried]
            report("uceni", OK if todo else WARN,
                   f"profil {prof}: {len(todo)} novych pokusu ve fronte" + ("" if todo else " - sobotni uceni musi pridat nove"))
    except Exception as exc:
        report("uceni", ERR, f"self_learn nejde nacist: {type(exc).__name__}: {exc}")
    return name


def check_outputs(today: date, champion_name: str | None) -> None:
    path = LIVE / "stav.json"
    if not path.exists():
        report("prehled", ERR, "data/live/stav.json chybi - spust signals_live.py")
    else:
        st = json.loads(path.read_text())
        made = datetime.fromisoformat(st["aktualizovano"])
        hours = (datetime.now(UTC) - made).total_seconds() / 3600
        report("prehled", OK if hours <= 24 * 8 else WARN, f"stav vytvoren {made:%Y-%m-%d %H:%M} UTC (pred {hours:.0f} h), "
                                                         f"data do {st['den_dat']}")
        errors = [p["par"] for p in st["pary"] if p.get("chyba")]
        report("prehled", ERR if errors else OK if len(st["pary"]) == len(DEFAULT_ACTIVE) else WARN,
               f"{len(st['pary'])} paru" + (f", chyba u {', '.join(errors)}" if errors else ""))
        if champion_name and st["pravidlo"] != champion_name:
            report("prehled", ERR, f"prehled ukazuje pravidlo '{st['pravidlo']}', sampion je '{champion_name}'")
    fwd = LEARNING / "forward_trades.json"
    trades = json.loads(fwd.read_text()) if fwd.exists() else []
    open_ = [t for t in trades if t["stav"] == "otevreny"]
    stuck = [t["id"] for t in open_ if (today - date.fromisoformat(t["den"])).days > 35]
    closed = [t for t in trades if t["stav"] == "uzavreny"]
    report("forward test", WARN if stuck else OK,
           f"{len(trades)} obchodu modelu, {len(open_)} otevrenych, {len(closed)} uzavrenych"
           + (f"; po case otevrene: {', '.join(stuck)}" if stuck else ""))
    dash = LEARNING / "dashboard.json"
    report("prehled", OK if dash.exists() and json.loads(dash.read_text()).get("url") else WARN,
           "adresa webove stranky ulozena" if dash.exists() else "learning/dashboard.json chybi")


def check_online() -> None:
    import signals_live as SLV
    try:
        bars = SLV.yahoo_hourly("EURUSD=X", "5d")
        last = datetime.fromtimestamp(int(bars["ts"][-1]), tz=UTC)
        report("online", OK, f"Yahoo odpovida, EUR/USD posledni svicka {last:%Y-%m-%d %H:%M} UTC")
    except Exception as exc:
        report("online", ERR, f"Yahoo neodpovida: {type(exc).__name__}")
    from src.sources.http import fetch
    try:
        _, content, _ = fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS", retries=2)
        report("online", OK if content.startswith(b"observation_date") else WARN, "FRED odpovida")
    except Exception as exc:
        report("online", ERR, f"FRED neodpovida: {type(exc).__name__}")


def run(online: bool = False) -> dict:
    """All checks; returns {"den", "souhrn", "kontroly"} and writes data/live/diagnostika.json."""
    results.clear()
    today = datetime.now(UTC).date()
    print(f"Diagnostika modelu {today}\n")
    check_prices(today)
    check_rates(today)
    check_fundamentals_db(today)
    name = check_state()
    check_outputs(today, name)
    if online:
        check_online()
    counts = {s: sum(r["stav"] == s for r in results) for s in (OK, WARN, ERR)}
    print(f"\nShrnuti: {counts[OK]} OK, {counts[WARN]} varovani, {counts[ERR]} chyb")
    out = {"den": today.isoformat(), "souhrn": counts, "kontroly": list(results)}
    LIVE.mkdir(parents=True, exist_ok=True)
    (LIVE / "diagnostika.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main(argv: list[str]) -> int:
    return 1 if run("--online" in argv)["souhrn"][ERR] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
