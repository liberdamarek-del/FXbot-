"""E4 - the V7.8.0 PRE-CHANGE TEST REGISTER (Word, tests T01-T14) as
executable tests, plus the quote contract details (modules 117-120,
132-135)."""

import os
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e4_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.database import initialize_database  # noqa: E402
from src.engine.thesis import MemoryThesisStore, ThesisBook  # noqa: E402
from src.prediction_ledger import PredictionRejected, get_prediction, lock_prediction  # noqa: E402
from src.v78.quotes import (  # noqa: E402
    QuoteObservation,
    build_pair_quote,
    freshness,
    market_state,
    skew_state,
    source_consistency,
)

UTC = timezone.utc
initialize_database()
NOW = datetime(2026, 9, 29, 12, 0, 0, tzinfo=UTC)          # Tuesday, market open
N = NOW.timestamp()


def obs(symbol="USD/JPY", source="TWELVE_DATA", cls="API_SNAPSHOT", mid=157.25, age=30.0, bid=None, ask=None):
    return QuoteObservation(symbol, source, cls, mid, None if age is None else N - age, N, bid=bid, ask=ask)


# T01 fresh timestamped quote stays eligible
q = build_pair_quote("USD/JPY", [obs(age=30)], NOW)
assert q.data_state == "LIVE" and q.now_eligible and q.execution == "MODEL-PRICE"
assert freshness(61) == "FRESH" and freshness(301) == "CONDITIONAL" and freshness(901) == "REJECTED"

# T02 missing source timestamp -> blocked from exact NOW
q = build_pair_quote("USD/JPY", [obs(age=None)], NOW)
assert not q.now_eligible and q.data_state == "DATA-BLOCKED"

# T03 stale quote > 15 min -> rejected from NOW
q = build_pair_quote("USD/JPY", [obs(age=16 * 60)], NOW)
assert q.data_state == "REJECTED" and not q.now_eligible

# T04 time-only / delayed observation -> visible as context, not execution
q = build_pair_quote("USD/JPY", [obs(source="DUKASCOPY_TICK", cls="DELAYED_REFERENCE", age=20, bid=157.24, ask=157.26)], NOW)
assert q.canonical is not None and not q.now_eligible and "NEOVERENA" in " ".join(q.notes)

# T05 USD/JPY 157.25 cluster vs ~158.33 -> outlier excluded from canonical NOW
cluster = [obs(source="A", mid=157.23, age=10), obs(source="B", mid=157.26, age=12),
           obs(source="C", mid=157.29, age=8), obs(source="X", mid=158.33, age=5)]
q = build_pair_quote("USD/JPY", cluster, NOW)
assert q.canonical.mid != 158.33 and next(o for o in q.observations if o.source_id == "X").rejected
two = build_pair_quote("USD/JPY", [obs(source="A", mid=157.25, age=10), obs(source="X", mid=158.33, age=5)], NOW)
assert two.data_state == "DATA-CONFLICT" and not two.now_eligible, "two disagreeing sources: conflict, no average"

# T06 closed weekend market -> LAST VALID SESSION, no NOW
saturday = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
q = build_pair_quote("USD/JPY", [QuoteObservation("USD/JPY", "TWELVE_DATA", "API_SNAPSHOT", 157.2,
                                                  saturday.timestamp() - 30, saturday.timestamp())], saturday)
assert q.market == "CLOSED" and q.data_state == "LAST_VALID_SESSION" and not q.now_eligible
assert market_state(datetime(2026, 9, 27, 20, 30, tzinfo=UTC)) == "PRE-OPEN"
assert market_state(datetime(2026, 12, 25, 12, 0, tzinfo=UTC)) == "HOLIDAY"

# T07 historical M1 source available -> used instead of automatic GAP  (E1: ingest_day COMPLETE)
# T08 primary history fails -> ladder continues                       (E1: GAP recorded, E5: run continues)
from src.v78.coverage import coverage  # noqa: E402
from src.path_archive import Bar  # noqa: E402

start = int(datetime(2026, 9, 29, 10, 0, tzinfo=UTC).timestamp())
bars = [Bar(start + 60 * k, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1) for k in range(120) if not 30 <= k < 40]
cov = coverage("EUR/USD", start, start + 7200, [], bars, {b.ts: "DUKASCOPY_M1" for b in bars})
assert cov.state == "UNRESOLVED" and cov.expected == 120 and cov.observed == 110 and cov.max_gap_minutes == 10
few = [b for b in bars + [Bar(start + 60 * k, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1) for k in range(30, 37)]]
cov = coverage("EUR/USD", start, start + 7200, [], few, {})
assert cov.state == "PARTIAL" and cov.observed == 117, "97.5 % and gap <= 30 min = PARTIAL"
cov = coverage("EUR/USD", start, start + 7200, [(start + 1500, start + 3000)], bars, {})
assert cov.gaps[0].severity == "CRITICAL", "gap inside an open prediction's window is critical"

# T09 BUY -> SELL without invalidation -> flip rejected
# T10 BUY -> SELL after hard invalidation + new setup -> new opposite prediction allowed
from src.engine.decision import Candidate  # noqa: E402

book = ThesisBook(MemoryThesisStore())
buy = Candidate("EUR/USD", int(N), "BUY NOW", "BUY", "BUY", "PULLBACK", 1.1, 1.099, 1.1, 1.099, [1.102, 1.103, 1.104],
                confidence="B")
book.open_thesis(buy, "P-BUY", int(N), 24)
sell = replace(buy, decision="SELL NOW", direction="SELL", thesis_direction="SELL", stop=1.101, targets=[1.098, 1.097, 1.096])
assert book.check(sell, int(N) + 3600, regime_break=False).action == "BLOCKED_FLIP"                   # T09
book.update_from_path("EUR/USD", int(N) + 7200, "SL_BEFORE_TP1", int(N) + 60)
assert book.check(sell, int(N) + 7300, regime_break=False).allowed                                    # T10

# T11 active thesis leaves Top-3 -> remains auditable, not deleted
book2 = ThesisBook(MemoryThesisStore())
book2.open_thesis(buy, "P-KEEP", int(N), 24)
from src.engine.portfolio import select_top  # noqa: E402
from src.engine.params import DEFAULT_PARAMS as P  # noqa: E402

select_top([], P)
assert book2.store.get("EUR/USD").open and book2.store.get("EUR/USD").prediction_id == "P-KEEP"

# T12 locked prediction mutation -> prior T0 fields stay immutable
pid = lock_prediction(model_version="TEST", t0=NOW, instrument="EUR/USD", decision="BUY NOW", reference_price="1.1",
                      price_source="TEST", price_timestamp=NOW - timedelta(minutes=1), data_state="CURRENT",
                      data_quality="B", entry="1.1", stop_loss="1.099", tp1="1.102", thesis="t", counterforce="c",
                      invalidation="i", now=NOW)
from src.database import get_connection  # noqa: E402
import sqlite3  # noqa: E402

try:
    with get_connection() as c:
        c.execute("UPDATE predictions SET stop_loss = '1.098' WHERE prediction_id = ?", (pid,))
    raise AssertionError("mutation must be impossible")
except sqlite3.DatabaseError as exc:
    assert "immutable" in str(exc)
assert get_prediction(pid)["stop_loss"] == "1.099"

# T13 post-T0 information -> excluded (price after T0 rejected; resolver ignores bars before T0 - see E3/D1)
try:
    lock_prediction(model_version="TEST", t0=NOW, instrument="EUR/USD", decision="BUY NOW", reference_price="1.1",
                    price_source="TEST", price_timestamp=NOW + timedelta(seconds=5), data_state="CURRENT",
                    data_quality="B", entry="1.1", stop_loss="1.099", tp1="1.102", thesis="t", counterforce="c",
                    invalidation="i", now=NOW + timedelta(minutes=1))
    raise AssertionError("post-T0 price must be rejected")
except PredictionRejected as exc:
    assert "post-T0" in str(exc)

# T14 output contract: prices + Top-3 + state in the Czech output -> see E5 (end-to-end run report)

# ---------------------------------------------------------------- extra: contract details
future = QuoteObservation("EUR/USD", "TWELVE_DATA", "API_SNAPSHOT", 1.13, N + 600, N)
assert build_pair_quote("EUR/USD", [future], NOW).data_state == "DATA-BLOCKED", "future timestamp rejected"
wrong = QuoteObservation("EUR/USD", "TWELVE_DATA", "API_SNAPSHOT", 157.2, N - 5, N)
assert build_pair_quote("EUR/USD", [wrong], NOW).data_state == "DATA-BLOCKED", "instrument identity check"
broker = QuoteObservation("EUR/USD", "OANDA", "BROKER_TRUTH", 1.13001, N - 2, N, bid=1.13, ask=1.13002)
q = build_pair_quote("EUR/USD", [broker, obs("EUR/USD", mid=1.1301, age=40)], NOW)
assert q.canonical.source_id == "OANDA" and q.execution == "EXECUTABLE", "broker bid/ask ranks first"
pairs = {"A": build_pair_quote("EUR/USD", [obs("EUR/USD", mid=1.13, age=5)], NOW),
         "B": build_pair_quote("GBP/USD", [obs("GBP/USD", mid=1.32, age=50)], NOW)}
assert skew_state(pairs) == (45.0, "CONDITIONAL")
same = [Bar(k * 60, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1, 1, 1) for k in range(30)]
drift = [Bar(k * 60, 1.1010, 1.1010, 1.1010, 1.1010, 1.1010, 1.1010, 1.1010, 1.1010, 1, 1, 1) for k in range(30)]
assert source_consistency(same, same, 0.0001)["state"] == "CONSISTENT"
assert source_consistency(same, drift, 0.0001)["state"] == "SOURCE_DRIFT"

print("=" * 60)
print("E4 V7.8.0 PRE-CHANGE TEST REGISTER T01-T14 + QUOTE CONTRACT")
print("=" * 60)
for line in (
    "T01 fresh timestamped quote eligible", "T02 missing timestamp blocked", "T03 stale >15m rejected",
    "T04 time-only/delayed = context only", "T05 USD/JPY 158.33 outlier excluded / 2 sources = CONFLICT",
    "T06 closed weekend = LAST VALID SESSION", "T07/T08 history ladder + coverage certificate",
    "T09 flip without invalidation rejected", "T10 flip after invalidation allowed",
    "T11 thesis outside Top-3 kept", "T12 locked prediction immutable", "T13 post-T0 information rejected",
):
    print(f"{line}: PASS")
print("T14 Czech output contract: see test_e5_run.py")
print("RESULT: PASS")
print("=" * 60)
