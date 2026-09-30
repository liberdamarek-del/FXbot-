"""E2 - fundamental layer: parsers (frozen samples of the real formats),
point-in-time reads, revisions, calendar, per-pair evidence."""

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e2_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.fundamental import adapters as A  # noqa: E402
from src.fundamental.calendar import event_window, events_between, parse_feed, store_events  # noqa: E402
from src.fundamental.store import available_at_for, load_series, upsert_series  # noqa: E402

UTC = timezone.utc


def ts(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp())


# ---------------------------------------------------------------- parsers (formats verified 2026-09-30)
fred = b"observation_date,DGS2\n2026-09-24,4.80\n2026-09-25,.\n2026-09-28,4.92\n"
assert A.parse_fred_csv(fred) == [(date(2026, 9, 24), 4.80), (date(2026, 9, 28), 4.92)], "missing '.' skipped"

ecb = (b"KEY,FREQ,REF_AREA,CURRENCY,PROVIDER_FM,INSTRUMENT_FM,PROVIDER_FM_ID,DATA_TYPE_FM,TIME_PERIOD,OBS_VALUE\n"
       b"YC.B.U2,B,U2,EUR,4F,G_N_A,SV_C_YM,SR_2Y,2026-09-29,3.2105\n")
assert A.parse_ecb_csv(ecb) == [(date(2026, 9, 29), 3.2105)]

mof = ("Interest Rate (September 2026),,,,(Unit : %)\nDate,1Y,2Y,10Y\n2026/9/1,1.527,1.802,2.987\n"
       "2026/9/2,1.5,-,2.9\n,,,\n\"If you cannot download...\",,,\n").encode()
parsed = A.parse_mof_csv(mof)
assert parsed["2Y"] == [(date(2026, 9, 1), 1.802)] and parsed["10Y"][1] == (date(2026, 9, 2), 2.9)

boe = b"DATE,IUDSNPY,IUDMNPY\n25 Sep 2026,4.9162,5.3321\n28 Sep 2026,4.9696,5.3829\n"
assert A.parse_boe_csv(boe)["IUDMNPY"][-1] == (date(2026, 9, 28), 5.3829)

boc = json.dumps({"observations": [{"d": "2026-09-28", "BD.CDN.2YR.DQ.YLD": {"v": "3.37"},
                                    "BD.CDN.10YR.DQ.YLD": {"v": ""}}]}).encode()
assert A.parse_boc_json(boc) == {"BD.CDN.2YR.DQ.YLD": [(date(2026, 9, 28), 3.37)]}

rba = ("﻿F2 CAPITAL MARKET YIELDS\nTitle,AGB 2y,AGB 10y\nSource,RBA,RBA\n"
       "Series ID,FCMYGBAG2D,FCMYGBAG10D\n20-May-2013,,3.229\n22-Sep-2026,5.003,5.293\n").encode()
assert A.parse_rba_csv(rba)["FCMYGBAG2D"] == [(date(2026, 9, 22), 5.003)]

bis = (b"FREQ,REF_AREA,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE\nD,US,368,2026-09-21,3.875\nD,XM,368,2026-09-21,2.5\n"
       b"D,XM,368,2026-09-22,NaN\n")
assert A.parse_bis_csv(bis) == {"US": [(date(2026, 9, 21), 3.875)], "XM": [(date(2026, 9, 21), 2.5)]}

# ---------------------------------------------------------------- point-in-time + lag
upsert_series("TEST.Y2", [(date(2026, 9, 24), 4.80), (date(2026, 9, 25), 4.85)], 30, "FRED", None)
series = load_series("TEST.Y2")
assert series.asof(ts("2026-09-25T05:59:59")) is None, "D value is public only after the lag"
assert series.asof(ts("2026-09-25T06:00:00")).value == 4.80
assert series.asof(ts("2026-09-26T07:00:00")).value == 4.85
assert available_at_for(date(2026, 9, 24), 30) == ts("2026-09-25T06:00:00")

# ---------------------------------------------------------------- revisions (append-only, visible only after seen)
seen = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
result = upsert_series("TEST.Y2", [(date(2026, 9, 25), 4.90)], 30, "FRED", None, seen_at=seen)
assert result.revised == 1 and result.inserted == 0
series = load_series("TEST.Y2")
assert series.asof(ts("2026-09-29T00:00:00")).value == 4.85, "before the revision was seen: first value"
assert series.asof(ts("2026-09-30T12:00:01")).value == 4.90, "after it was seen: revised value"
again = upsert_series("TEST.Y2", [(date(2026, 9, 25), 4.90)], 30, "FRED", None, seen_at=seen)
assert again.revised == 0 and again.unchanged == 1, "an identical re-download is not a revision"

# ---------------------------------------------------------------- calendar (no hindsight)
feed = json.dumps([
    {"title": "Non-Farm Employment Change", "country": "USD", "date": "2026-10-02T08:30:00-04:00",
     "impact": "High", "forecast": "150K", "previous": "120K"},
    {"title": "Retail Sales m/m", "country": "AUD", "date": "2026-10-01T21:30:00-04:00", "impact": "Medium",
     "forecast": "0.3%", "previous": "0.2%"},
    {"title": "No zone", "country": "EUR", "date": "2026-10-01T10:00:00", "impact": "High"},
]).encode()
events = parse_feed(feed)
assert len(events) == 2, "an event without a time zone is not used (TIMEZONE-UNRESOLVED)"
nfp = next(e for e in events if e.currency == "USD")
assert nfp.scheduled_at == ts("2026-10-02T12:30:00")
store_events(events, None, datetime(2026, 9, 30, 12, 0, tzinfo=UTC))
window = event_window(("EUR", "USD"), ts("2026-10-02T08:00:00"), pre_hours=6)
assert [e.title for e in window["pre"]] == ["Non-Farm Employment Change"]
assert event_window(("EUR", "USD"), ts("2026-10-02T12:45:00"))["post"][0].currency == "USD"
assert events_between(ts("2026-10-01"), ts("2026-10-03"), ("USD",), "High", known_at=ts("2026-09-29T00:00:00")) == [], \
    "an event first seen later is unknown to an earlier backtest moment"
changed = store_events([type(nfp)(nfp.event_id, "USD", nfp.title, nfp.scheduled_at, "High", "170K", "120K")], None,
                       datetime(2026, 10, 1, tzinfo=UTC))
assert changed["changed"] == 1

# ---------------------------------------------------------------- per-pair evidence (synthetic series)
from src.engine.fundamental import analyze, currency_state  # noqa: E402
from src.engine.params import DEFAULT_PARAMS as P  # noqa: E402
from src.engine.series import PriceSeries  # noqa: E402
from src.path_archive import Bar  # noqa: E402

days = [date(2026, 5, 1) + timedelta(days=k) for k in range(150)]
upsert_series("USD.Y2", [(d, 4.0 + 0.004 * k) for k, d in enumerate(days)], 30, "FRED", None)     # rising
upsert_series("EUR.Y2", [(d, 2.5) for d in days], 30, "ECB", None)                               # flat
upsert_series("USD.POLICY", [(d, 3.875) for d in days], 24, "BIS", None)
upsert_series("EUR.POLICY", [(d, 2.5) for d in days], 24, "BIS", None)
t = ts("2026-09-20T12:00:00")
usd, eur = currency_state("USD", t, P), currency_state("EUR", t, P)
assert usd.short_rate > usd.short_rate_past and eur.short_rate == eur.short_rate_past
bars = []
for k in range(140):
    d0 = int(datetime(2026, 5, 1, tzinfo=UTC).timestamp()) + k * 86400
    price = 1.10 + 0.0003 * k
    bars.append(Bar(d0, price, price + 0.004, price - 0.004, price + 0.0003, price + 0.00002,
                    price + 0.00402, price - 0.00398, price + 0.00032, 1, 1, 1440))
d1 = PriceSeries.from_bars("EUR/USD", "1d", bars)
view = analyze("EUR/USD", t, d1, P, None, False)
repricing = [e for e in view.evidence if e.cluster == "RATES_REPRICING"]
assert repricing and repricing[0].direction == "SELL", "US yields up vs EUR flat -> repricing favours USD"
assert view.event_layer == "NOT_AVAILABLE" and any("kalendar" in g for g in view.data_gaps)

print("=" * 60)
print("E2 FUNDAMENTAL LAYER")
print("=" * 60)
print("PARSERS FRED/ECB/MOF/BOE/BOC/RBA/BIS: PASS")
print("POINT-IN-TIME WITH PUBLICATION LAG: PASS")
print("REVISIONS APPEND-ONLY, VISIBLE ONLY AFTER SEEN: PASS")
print("CALENDAR: TIMEZONE GATE, WINDOWS, NO HINDSIGHT: PASS")
print("PAIR EVIDENCE (RATE REPRICING) FROM STORED SERIES: PASS")
print("RESULT: PASS")
print("=" * 60)
