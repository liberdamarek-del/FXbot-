"""FXBOT - one entry point for everything.

    python fxbot.py run              # Proved V7.8.0: data, audit, analyza, Top-3, certifikat
    python fxbot.py run --offline    # bez stahovani (jen ulozena data)
    python fxbot.py run --no-lock    # analyza bez zamceni predikci
    python fxbot.py update           # jen stahnout data (zivy 1min, cesta bid/ask, fundamenty)
    python fxbot.py history --days 90 --hourly-years 5   # historie bid/ask (Dukascopy)
    python fxbot.py fundamentals --years 12              # dlouha fundamentalni historie
    python fxbot.py backtest [--ablation --robustness --walkforward]
    python fxbot.py resolve          # jen vyhodnotit otevrene predikce
    python fxbot.py status           # stav dat, archivu, evidence a registru modelu
    python fxbot.py paper            # papirovy ucet z evidence predikci
    python fxbot.py review [--weekly|--monthly|--all] [--manual]   # revize predikci (modul 82)
    python fxbot.py journal BUY USD/JPY 158.32 --sl 157.40 --tp 160.00 [--time "2026-10-01 06:30"] [--horizon 120h]
                                     # zapsat VAS rucni obchod; bot ho sam vyhodnoti (deni k)
    python fxbot.py report           # posledni zprava behu
    python fxbot.py verify-model [cesta.docx]   # kontrola Wordu (moduly 0-145)
    python fxbot.py setkey           # ulozit a otestovat klic Twelve Data
    python fxbot.py test             # izolovane testy

Every command works on the project's data/ folder; tests never touch it.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

UTC = timezone.utc


def _script(name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_run(args) -> int:
    from src.broker import from_env
    from src.instruments import parse_symbols
    from src.v78.run import RunOptions, execute

    started = time.monotonic()
    broker = None if args.no_broker else from_env()
    result = execute(RunOptions(
        symbols=parse_symbols(args.symbols) if args.symbols else [],
        fetch=not args.offline,
        lock=not args.no_lock,
        balance=args.balance,
        broker=broker,
    ))

    if result.get("report"):
        print(result["report"])

        if args.notify and result.get("locked"):
            notify_phone(result)
    else:
        print(f"BEH {result['run_id']} SELHAL: {result.get('error')}")
        print(result.get("traceback", ""))

    print(f"\nartefakty: {result.get('run_dir', '-')}")
    print(f"beh trval {time.monotonic() - started:.0f} s")
    return 0 if result["state"].startswith("COMMITTED") else 1


def notify_phone(result: dict) -> None:
    """Termux:API notification about newly locked predictions (optional)."""
    import shutil
    import subprocess

    if not shutil.which("termux-notification"):
        return

    lines = [line.strip() for line in result["report"].splitlines() if line.strip()[:2] in ("1.", "2.", "3.")]
    subprocess.run(["termux-notification", "--title", f"FXBOT: {len(result['locked'])} nova predikce",
                    "--content", "\n".join(lines[:3]) or result["run_id"]], check=False)


def cmd_update(args) -> int:
    from src.instruments import parse_symbols
    from src.v78.run import acquire_fundamentals, acquire_live, acquire_path

    now = datetime.now(UTC)
    symbols = parse_symbols(args.symbols)
    notes = []
    print("Twelve Data (zivy 1min):", acquire_live(symbols, now, notes))
    path = acquire_path(symbols, now, args.days, notes)
    print("Dukascopy (bid/ask):", path["state"], f"| dnu {len(path['days'])} | hodin dnes {sum(path['hours'].values())}")
    print("Fundamenty:", acquire_fundamentals(now, notes, force=True))

    for note in notes:
        print("POZOR:", note)

    return 0


def cmd_resolve(args) -> int:
    from src.database import initialize_database
    from src.prediction_ledger import initialize_ledger
    from src.v78.audit import audit_all

    initialize_database()
    initialize_ledger()
    items = audit_all(datetime.now(UTC))

    if not items:
        print("zadne otevrene predikce")

    for item in items:
        r = f"{item.r_net:+.2f}R" if item.r_net is not None else ""
        print(f"{item.prediction_id} {item.symbol} {item.decision}: {item.outcome_state or item.status} {r} "
              f"[{item.cost_layer}] {item.notes[:60]}")

    return 0


def cmd_status(args) -> int:
    from src.data_state import get_status
    from src.database import initialize_database
    from src.fundamental.store import series_summary
    from src.instruments import parse_symbols
    from src.path_archive import archive_summary, initialize_path_archive
    from src.prediction_ledger import initialize_ledger, list_predictions
    from src.stats.registry import champion, change_log
    from src.v78.sources import register_state

    initialize_database()
    initialize_ledger()
    initialize_path_archive()
    now = datetime.now(UTC)
    print("=" * 78)
    print(f"FXBOT STAV {now:%Y-%m-%d %H:%M} UTC")
    print("=" * 78)
    print("ZIVA DATA (Twelve Data 1min) | ARCHIV BID/ASK (Dukascopy)")

    for symbol in parse_symbols(args.symbols):
        status = get_status(symbol, "1min", now=now)
        summary = archive_summary(symbol)
        days = summary["days"].get("COMPLETE", {})
        months = summary["months"].get("COMPLETE", {})
        print(f"  {symbol:<8} {status.state.value:<10} | 1min dny {days.get('n', 0):>4} (do {days.get('last', '-')})"
              f" | 1h mesice {months.get('n', 0):>3} (od {months.get('first', '-')})")

    series = series_summary()
    print(f"FUNDAMENTY: {len(series)} rad, posledni stazeni "
          f"{max((r['last_download'] for r in series), default='-')[:16]}, nejnovejsi pozorovani "
          f"{max((r['last'] for r in series), default='-')}")
    predictions = list_predictions(limit=10000)
    open_ = [p for p in predictions if p["direction"] != "NONE" and not p["outcomes"]]
    print(f"EVIDENCE PREDIKCI: {len(predictions)} celkem, {len(open_)} bez vysledku")
    champ = champion()
    print(f"MODEL CHAMPION: {champ['label'] + ' ' + champ['fingerprint'] if champ else 'zatim neurcen (spust backtest)'}")
    print(f"ZMENY V LOGU: {len(change_log())}")
    print("ZDROJE:")

    for row in register_state():
        if row["tested_at"] or row["state"] != "DOC-PASS":
            print(f"  {row['source_id']:<20} {row['state']:<15} {(row['detail'] or '')[:40]}")

    return 0


def cmd_paper(args) -> int:
    from src.broker.paper import paper_equity

    equity = paper_equity(args.balance)
    print(f"PAPIROVY UCET: start {equity['start']:.0f} -> {equity['balance']:.2f} ({equity['return_pct']:+.2f} %)"
          f" | obchodu {equity['trades']} | max DD {equity['max_drawdown_r']:.1f} R")

    for row in equity["curve"][-20:]:
        print(f"  {row['t0'][:16]} {row['symbol']:<8} {row['outcome']:<16} {row['r']:+.2f}R {row['pnl']:+9.2f}"
              f" -> {row['balance']:.2f}")

    return 0


def cmd_report(args) -> int:
    from src.v78.persist import RUNS_DIR

    runs = sorted(RUNS_DIR.glob("RUN-*/report_cz.txt")) if RUNS_DIR.exists() else []

    if not runs:
        print("zatim zadny beh (python fxbot.py run)")
        return 1

    print(runs[-1].read_text(encoding="utf-8"))
    return 0


def cmd_verify_model(args) -> int:
    from src.v78.manifest import MODULES, verify_document, verify_manifest
    from src.v78.run import find_model_document

    path = Path(args.path) if args.path else find_model_document()
    print("manifest:", verify_manifest() or "OK (146 modulu 0-145)")
    counts = {}

    for module in MODULES:
        counts[module.status] = counts.get(module.status, 0) + 1

    print("implementace:", counts)

    if path is None:
        print("Word dokument nenalezen (docs/FX_MASTER_MODEL_V7.8.0.docx)")
        return 1

    result = verify_document(path)
    print(f"{path.name}: {result['status']} (nalezeno {result.get('modules_found')} nadpisu modulu)")

    for problem in result["problems"][:10]:
        print("  -", problem)

    if args.list:
        for module in MODULES:
            print(f"  {module.id:>3} {module.status:<13} {module.title[:40]:<40} {module.note[:30]}")

    return 0 if result["status"] == "MODEL LOAD COMPLETE" else 1


def cmd_journal(args) -> int:
    """Lock the user's own trade in the immutable ledger (model_version
    MANUAL). It is resolved by every run on the BID/ASK path like any model
    prediction and reviewed with `review --manual`, incl. the paired control
    against a random direction - the only way to measure a discretionary
    method (pivots, SMA, judgement) objectively."""
    from src.database import initialize_database
    from src.instruments import get_instrument
    from src.prediction_ledger import PredictionRejected, initialize_ledger, lock_prediction

    initialize_database()
    initialize_ledger()
    side = args.side.upper()
    symbol = args.symbol.upper()
    instrument = get_instrument(symbol)
    now = datetime.now(timezone.utc)
    t0 = now if not args.time else datetime.fromisoformat(args.time).replace(tzinfo=timezone.utc)
    q = lambda v: round(v, instrument.decimals)

    try:
        pid = lock_prediction(
            model_version="MANUAL", run_id="MANUAL", t0=t0, instrument=symbol, decision=f"{side} NOW",
            reference_price=q(args.price), price_source="MANUAL (obchod uzivatele)", price_timestamp=t0,
            data_state="CURRENT", data_quality="C", forecast_mode="MANUAL", setup_type=args.setup,
            entry=q(args.price), stop_loss=q(args.sl), tp1=q(args.tp), primary_horizon=args.horizon,
            thesis=args.note or "rucni obchod uzivatele", counterforce="neuvedeno",
            invalidation=f"SL {q(args.sl)}", reasons=[args.note or "rucni obchod"],
            inputs={"entry_mode": "limit", "analysis_price": args.price, "manual": True}, now=now)
    except PredictionRejected as exc:
        print(f"ZAMITNUTO: {exc}")
        return 1

    risk = abs(args.price - args.sl) / instrument.pip
    reward = abs(args.tp - args.price) / instrument.pip
    print(f"zapsano {pid}: {side} {symbol} {q(args.price)} SL {q(args.sl)} ({risk:.0f} pip) TP {q(args.tp)} "
          f"({reward:.0f} pip, R:R {reward / risk:.2f}), horizont {args.horizon}")
    print("vyhodnoti se samo pri kazdem 'python fxbot.py run'; prehled: python fxbot.py review --all --manual")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="fxbot", description="FXBOT V7.8.0 implementation")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="full V7.8.0 run")
    run.add_argument("--offline", action="store_true")
    run.add_argument("--no-lock", action="store_true")
    run.add_argument("--no-broker", action="store_true")
    run.add_argument("--symbols", default=None)
    run.add_argument("--balance", type=float, default=10000.0)
    run.add_argument("--notify", action="store_true", help="Termux:API notification for new predictions")

    update = sub.add_parser("update", help="download new data only")
    update.add_argument("--symbols", default=None)
    update.add_argument("--days", type=int, default=5)

    sub.add_parser("history", help="BID/ASK history (scripts/download_history.py options)", add_help=False)
    sub.add_parser("fundamentals", help="fundamentals (scripts/update_fundamentals.py options)", add_help=False)
    sub.add_parser("backtest", help="backtest (scripts/backtest.py options)", add_help=False)
    sub.add_parser("setkey", help="store and test the Twelve Data key", add_help=False)
    sub.add_parser("test", help="isolated test suite", add_help=False)
    sub.add_parser("review", help="daily/weekly/monthly review (scripts/review.py)", add_help=False)
    sub.add_parser("resolve", help="resolve open predictions")
    status = sub.add_parser("status", help="state of data and model")
    status.add_argument("--symbols", default=None)
    paper = sub.add_parser("paper", help="paper account from the ledger")
    paper.add_argument("--balance", type=float, default=10000.0)
    sub.add_parser("report", help="print the newest run report")
    verify = sub.add_parser("verify-model", help="check the model Word document")
    verify.add_argument("path", nargs="?")
    verify.add_argument("--list", action="store_true")
    journal = sub.add_parser("journal", help="record your own trade (evaluated automatically)")
    journal.add_argument("side", choices=("BUY", "SELL", "buy", "sell"))
    journal.add_argument("symbol")
    journal.add_argument("price", type=float)
    journal.add_argument("--sl", type=float, required=True)
    journal.add_argument("--tp", type=float, required=True)
    journal.add_argument("--time", default=None, help="entry time UTC 'YYYY-MM-DD HH:MM' (default now)")
    journal.add_argument("--horizon", default="120h", help="max holding, e.g. 24h, 72h, 120h")
    journal.add_argument("--setup", default="MANUAL", help="e.g. PIVOT_S1, SMA50_PULLBACK")
    journal.add_argument("--note", default=None)

    if argv and argv[0] in ("history", "fundamentals", "backtest", "setkey", "test", "review"):
        name = {"history": "download_history", "fundamentals": "update_fundamentals", "backtest": "backtest",
                "setkey": "set_api_key", "test": "run_tests", "review": "review"}[argv[0]]
        return _script(name).main(argv[1:])

    args = parser.parse_args(argv)
    return {
        "run": cmd_run, "update": cmd_update, "resolve": cmd_resolve, "status": cmd_status,
        "paper": cmd_paper, "report": cmd_report, "verify-model": cmd_verify_model, "journal": cmd_journal,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
