"""Block D1 - resolving locked predictions from stored 1-minute bars."""

import importlib.util
import io
import os
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_d1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.database import get_connection, initialize_database
from src.models import RawBar
from src.prediction_ledger import get_prediction, lock_prediction
from src.resolver import parse_horizon, resolve_all, resolve_prediction
from src.storage import save_raw_bars

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent
initialize_database()

spec = importlib.util.spec_from_file_location("resolve_cli", ROOT / "scripts" / "resolve.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


T0 = at("2026-09-30T10:00:20")                  # lock time; the bar that opens at 10:00 is NOT usable
counter = {"n": 0}


def lock(symbol, decision, entry, stop, tp1, t0=T0, horizon="24h"):
    counter["n"] += 1
    buy = decision.endswith("BUY") or decision == "BUY NOW"
    step = Decimal("0.0010")
    tp2, tp3 = (tp1 + step, tp1 + 2 * step) if buy else (tp1 - step, tp1 - 2 * step)
    price = entry if decision.endswith("NOW") else (entry + step if buy else entry - step)
    return lock_prediction(
        model_version="TEST", t0=t0, instrument=symbol, decision=decision,
        reference_price=price, price_source="TwelveData 1min", price_timestamp=t0 - timedelta(minutes=2),
        data_state="CURRENT", data_quality="C", entry=entry, entry_zone_low=min(entry, stop + abs(entry - stop) / 2),
        entry_zone_high=entry + Decimal("0.0002") if buy else entry,
        stop_loss=stop, tp1=tp1, tp2=tp2, tp3=tp3, primary_horizon=horizon,
        thesis="t", counterforce="c", invalidation="i", now=t0,
    )


def bars(symbol, path, start=at("2026-09-30T10:01")):
    """path: list of (high, low, close), one per minute from `start`; None = missing minute."""
    out = []
    for i, item in enumerate(path):
        if item is None:
            continue
        h, l, c = (Decimal(str(x)) for x in item)
        t = start + timedelta(minutes=i)
        out.append(RawBar(symbol, "1min", t, t + timedelta(minutes=3), c, h, l, c, "TwelveData"))
    save_raw_bars(out)


def calm(n, price=1.1000):
    return [(price + 0.0001, price - 0.0001, price)] * n


NOW = at("2026-09-30T13:00")
E, S, T = Decimal("1.1000"), Decimal("1.0990"), Decimal("1.1015")          # BUY: risk 10 pips, TP1 = 1.5 R


def outcomes(pid):
    return [o["outcome_state"] for o in get_prediction(pid)["outcomes"]]


def states(pid):
    return [s["state"] for s in get_prediction(pid)["states"]]


def resolve(pid, now=NOW):
    p = get_prediction(pid)
    return resolve_prediction(p, now)


# ---------------------------------------------------------------- 1. BUY NOW: TP1 first
pid = lock("A1/USD", "BUY NOW", E, S, T)
bars("A1/USD", calm(10) + [(1.1016, 1.0999, 1.1010)] + calm(5))
r = resolve(pid)
assert r.status == "CLOSED" and r.outcome_state == "TP1_BEFORE_SL" and r.r_multiple == Decimal("1.5"), r
assert r.resolved_at == at("2026-09-30T10:11") and r.triggered_at == T0
assert r.path_coverage == "COMPLETE" and r.mfe_r >= Decimal("1.5")

# ---------------------------------------------------------------- 2. BUY NOW: SL first
pid2 = lock("A2/USD", "BUY NOW", E, S, T)
bars("A2/USD", calm(4) + [(1.1001, 1.0989, 1.0991)] + calm(3, 1.0991))
r = resolve(pid2)
assert r.outcome_state == "SL_BEFORE_TP1" and r.r_multiple == Decimal(-1) and r.mae_r >= Decimal(1)

# ---------------------------------------------------------------- 3. SL and TP1 in the SAME minute: never guessed
pid3 = lock("A3/USD", "BUY NOW", E, S, T)
bars("A3/USD", calm(3) + [(1.1016, 1.0989, 1.1000)] + calm(3))
r = resolve(pid3)
assert r.outcome_state == "SEQUENCE_UNKNOWN" and r.r_multiple is None and "neznam" in r.notes

# ---------------------------------------------------------------- 4. NO HINDSIGHT: the bar opening at 10:00 (before T0) is ignored
pid4 = lock("A4/USD", "BUY NOW", E, S, T)
before = RawBar("A4/USD", "1min", at("2026-09-30T10:00"), at("2026-09-30T10:03"), Decimal("1.1"), Decimal("1.1"),
                Decimal("1.0900"), Decimal("1.0950"), "TwelveData")     # would hit SL, but opened before T0
save_raw_bars([before])
bars("A4/USD", calm(6) + [(1.1016, 1.0999, 1.1010)])
r = resolve(pid4)
assert r.outcome_state == "TP1_BEFORE_SL", "a bar from before T0 must not influence the result"

# ---------------------------------------------------------------- 5. WAIT FOR BUY: entry touched, then TP1
W = Decimal("1.1000")                                                          # entry below the price at lock (1.1010)
pid5 = lock("B1/USD", "WAIT FOR BUY", W, S, T)
bars("B1/USD", calm(3, 1.1008) + [(1.1005, 1.0999, 1.1002)] + calm(2, 1.1005) + [(1.1016, 1.1005, 1.1015)])
r = resolve(pid5)
assert r.outcome_state == "TP1_BEFORE_SL" and r.triggered_at == at("2026-09-30T10:04"), r
assert r.r_multiple == Decimal("1.5")

# ---------------------------------------------------------------- 6. WAIT: target reached without entry -> NOT_ACTIVATED
pid6 = lock("B2/USD", "WAIT FOR BUY", W, S, T)
bars("B2/USD", calm(2, 1.1010) + [(1.1016, 1.1005, 1.1012)])
r = resolve(pid6)
assert r.outcome_state == "NOT_ACTIVATED" and r.triggered_at is None and "bez vstupu" in r.notes

# ---------------------------------------------------------------- 7. WAIT: entry and exit in the trigger minute -> unknown
pid7 = lock("B3/USD", "WAIT FOR BUY", W, S, T)
bars("B3/USD", calm(2, 1.1010) + [(1.1016, 1.0999, 1.1000)])
assert resolve(pid7).outcome_state == "SEQUENCE_UNKNOWN"

# ---------------------------------------------------------------- 8. horizon: data cover the whole 24 h
DEADLINE = T0 + timedelta(hours=24)                                             # 2026-10-01 10:00:20 (Thursday)
LATE = DEADLINE + timedelta(minutes=5)
pid8 = lock("C1/USD", "BUY NOW", E, S, T)                                       # NOW, never hit -> EXPIRED
pid9 = lock("C2/USD", "WAIT FOR BUY", W, S, T)                                  # WAIT, never touched -> NOT_ACTIVATED
for sym, price in (("C1/USD", 1.1004), ("C2/USD", 1.1010)):
    bars(sym, [(price + 0.0001, price - 0.0001, price)] * (24 * 60 + 3))
r = resolve(pid8, LATE)
assert r.outcome_state == "EXPIRED" and r.status == "CLOSED"
assert abs(r.r_multiple - Decimal("0.4")) < Decimal("0.001"), r.r_multiple      # (1.1004 - 1.1000) / 0.0010
assert resolve(pid9, LATE).outcome_state == "NOT_ACTIVATED"

# ---------------------------------------------------------------- 9. data not yet downloaded up to the horizon -> still open
pid10 = lock("D1/USD", "BUY NOW", E, S, T)
bars("D1/USD", calm(30))
r = resolve(pid10, LATE)
assert r.status == "OPEN" and r.outcome_state is None, "missing tail = data not updated yet, not an outcome"

# ---------------------------------------------------------------- 10. a hole before the decisive bar -> UNRESOLVED, then resolves after repair
pid11 = lock("E1/USD", "BUY NOW", E, S, T)
path = calm(5) + [None, None, None] + [(1.1016, 1.0999, 1.1010)] + calm(2)
bars("E1/USD", path)
r = resolve(pid11)
assert r.outcome_state == "UNRESOLVED" and "PARTIAL" in r.path_coverage and r.status == "UNRESOLVED", r
# repair the hole with calm minutes
bars("E1/USD", [calm(1)[0]] * 3, start=at("2026-09-30T10:06"))
r = resolve(pid11)
assert r.outcome_state == "TP1_BEFORE_SL" and r.path_coverage == "COMPLETE"

# ---------------------------------------------------------------- 11. SELL mirror
SE, SS, ST = Decimal("1.1000"), Decimal("1.1010"), Decimal("1.0985")
pid12 = lock("F1/USD", "SELL NOW", SE, SS, ST)
bars("F1/USD", calm(3) + [(1.1001, 1.0984, 1.0990)])
assert resolve(pid12).outcome_state == "TP1_BEFORE_SL"
pid13 = lock("F2/USD", "SELL NOW", SE, SS, ST)
bars("F2/USD", calm(3) + [(1.1011, 1.0999, 1.1008)])
assert resolve(pid13).outcome_state == "SL_BEFORE_TP1"
pid14 = lock("F3/USD", "WAIT FOR SELL", SE, SS, ST)
bars("F3/USD", calm(2, 1.0990) + [(1.1001, 1.0995, 1.0998)] + calm(2, 1.0995) + [(1.0996, 1.0984, 1.0985)])
r = resolve(pid14)
assert r.outcome_state == "TP1_BEFORE_SL" and r.triggered_at == at("2026-09-30T10:03")

# ---------------------------------------------------------------- 12. ledger records: apply, idempotent, append-only
results = resolve_all(NOW)
assert results
first = {p["prediction_id"]: (len(get_prediction(p["prediction_id"])["states"]), len(get_prediction(p["prediction_id"])["outcomes"]))
         for p, _, _ in results}
resolve_all(NOW)
second = {p["prediction_id"]: (len(get_prediction(p["prediction_id"])["states"]), len(get_prediction(p["prediction_id"])["outcomes"]))
          for p, _, _ in results}
assert first == second, "running the resolver twice must not add records"

assert states(pid) == ["NEW", "TRIGGERED", "RESOLVED"] and outcomes(pid) == ["TP1_BEFORE_SL"]
assert states(pid5) == ["NEW", "WAITING", "TRIGGERED", "RESOLVED"]
assert states(pid6) == ["NEW", "WAITING", "NOT_ACTIVATED"]
assert outcomes(pid11) == ["UNRESOLVED", "TP1_BEFORE_SL"] or outcomes(pid11) == ["TP1_BEFORE_SL"]
assert outcomes(pid3) == ["SEQUENCE_UNKNOWN"] and states(pid3)[-1] == "RESOLVED"
o = get_prediction(pid)["outcomes"][0]
assert o["r_multiple"] == "1.5" and o["path_coverage"] == "COMPLETE" and Decimal(o["mfe"]) >= Decimal("1.5")
assert get_prediction(pid10)["outcomes"] == [] and states(pid10) == ["NEW", "TRIGGERED"]

# the ledger itself stayed untouched: locked fields never changed
assert get_prediction(pid)["stop_loss"] == "1.0990"
with get_connection() as c:
    try:
        c.execute("UPDATE predictions SET tp1 = '9'")
    except Exception:
        pass
    else:
        raise AssertionError("ledger became mutable")

# ---------------------------------------------------------------- 13. horizon parsing
assert parse_horizon("24h") == timedelta(hours=24) and parse_horizon("2d") == timedelta(days=2)
assert parse_horizon(None) == timedelta(hours=24) and parse_horizon("soon") == timedelta(hours=24)

# ---------------------------------------------------------------- 14. weekend: horizon ends while the market is closed
FRI = at("2026-09-25T20:00:20")
pid15 = lock("G1/USD", "BUY NOW", E, S, T, t0=FRI)
fri_bars = [(1.1001, 1.0999, 1.1000)] * 59                                      # 20:01 .. 20:59, the last in-session minute
bars("G1/USD", fri_bars, start=at("2026-09-25T20:01"))
r = resolve(pid15, at("2026-09-26T21:00"))                                      # Saturday, 24 h are over
assert r.outcome_state == "EXPIRED" and r.status == "CLOSED", r
assert resolve(pid15, at("2026-09-25T20:30")).status == "OPEN", "before the horizon nothing is final"

# ---------------------------------------------------------------- 15. CLI report
buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = cli.main([], now=NOW)
text = buffer.getvalue()
assert rc == 0 and "VYHODNOCENI PREDIKCI" in text and "TP1 dosazen drive nez SL" in text
assert "SL dosazen drive nez TP1" in text and "poradi neznamé" in text and "vstup se neuskutecnil" in text
assert "pouze popisne" in text and "spreadu" in text
assert max(len(line) for line in text.splitlines()) <= 100
buffer = io.StringIO()
with redirect_stdout(buffer):
    cli.main(["--open"], now=NOW)
assert "OTEVRENO" in buffer.getvalue() and "UZAVRENO" not in buffer.getvalue().split("predikci celkem")[0]

print("=" * 60)
print("D1 PREDICTION RESOLVER")
print("=" * 60)
print("TP1 / SL FIRST (BUY AND SELL): PASS")
print("SL AND TP1 IN THE SAME MINUTE = SEQUENCE_UNKNOWN, NEVER GUESSED: PASS")
print("NO HINDSIGHT (BARS BEFORE T0 IGNORED): PASS")
print("WAIT: ENTRY TOUCHED / NOT ACTIVATED / TRIGGER MINUTE AMBIGUITY: PASS")
print("HORIZON: EXPIRED / NOT ACTIVATED / STILL OPEN / WEEKEND: PASS")
print("HOLE IN THE PATH -> UNRESOLVED, RESOLVES AFTER REPAIR: PASS")
print("LEDGER: STATES AND OUTCOMES APPENDED ONCE, IDEMPOTENT: PASS")
print("CZECH REPORT WITH SMALL-SAMPLE WARNING: PASS")
print("RESULT: PASS")
print("=" * 60)
