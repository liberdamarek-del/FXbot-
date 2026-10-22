"""J1 - GitHub Actions run and the public page (R-050); no network, no price data.

scripts/github_beh.py decides which run is due from the clock (cron is UTC, the trading day ends 17:00 New York, the
Friday decision is valid from 16:00 New York) and reads the mode; scripts/web_stranka.py publishes stav.json without
the user's journal, with the central bank decisions per pair and the deadline of the next update, and wraps the page
in a whole HTML document. The page script itself is checked by a headless browser in the workflow.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_j1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import github_beh as GB  # noqa: E402
import web_stranka as WS  # noqa: E402

U = lambda *a: datetime(*a, tzinfo=timezone.utc)  # noqa: E731

# 1. keys of the due runs (summer time EDT = UTC-4 until 2026-11-01, winter EST = UTC-5)
k = GB.keys(U(2026, 10, 22, 21, 7))                    # Thursday 17:07 New York
assert k == {"denni": "2026-10-22", "patek": "", "uceni": "2026-10-22"}, k
k = GB.keys(U(2026, 10, 22, 20, 59))                   # Thursday 16:59 New York: the last close is Wednesday's
assert k["denni"] == "2026-10-21" and k["patek"] == "", k
k = GB.keys(U(2026, 10, 23, 20, 5))                    # Friday 16:05 New York: the Friday decision is due
assert k == {"denni": "2026-10-22", "patek": "2026-10-23", "uceni": "2026-10-23"}, k
k = GB.keys(U(2026, 10, 23, 19, 59))                   # Friday 15:59 New York: not yet
assert k["patek"] == "" and k["denni"] == "2026-10-22", k
k = GB.keys(U(2026, 10, 24, 3, 23))                    # Saturday 03:23 UTC = Friday 23:23 New York (late backup slot)
assert k["denni"] == "2026-10-23" and k["patek"] == "2026-10-23", k
k = GB.keys(U(2026, 10, 25, 12, 0))                    # Sunday: the last close is Friday's, no Friday decision
assert k["denni"] == "2026-10-23" and k["patek"] == "", k
k = GB.keys(U(2026, 11, 6, 21, 5))                     # winter time: Friday 16:05 New York is 21:05 UTC
assert k["patek"] == "2026-11-06" and k["denni"] == "2026-11-05", k
k = GB.keys(U(2026, 11, 6, 20, 5))                     # ... and 20:05 UTC is only 15:05 New York
assert k["patek"] == "", k
k = GB.keys(U(2026, 10, 24, 22, 30))                   # Saturday 22:30 UTC = Sunday 00:30 Prague
assert k["uceni"] == "2026-10-25", k

# 2. mode: only "ostry" writes; anything unknown is the shadow mode
assert GB.mode() in GB.MODES
orig = GB.MODE_FILE
try:
    tmp = Path(tempfile.mkdtemp()) / "github.json"
    GB.MODE_FILE = tmp
    assert GB.mode() == "stin"                         # missing file
    tmp.write_text('{"rezim": "zapis vsechno"}')
    assert GB.mode() == "stin"
    tmp.write_text('{"rezim": "ostry"}')
    assert GB.mode() == "ostry"
finally:
    GB.MODE_FILE = orig

# 3. the next update deadline: the next 17:00 New York close on a weekday after the build
assert WS.next_close(U(2026, 10, 22, 21, 10)).astimezone(timezone.utc) == U(2026, 10, 23, 21, 0)
assert WS.next_close(U(2026, 10, 23, 21, 10)).astimezone(timezone.utc) == U(2026, 10, 26, 21, 0)   # Friday -> Monday
assert WS.next_close(U(2026, 11, 2, 12, 0)).astimezone(timezone.utc) == U(2026, 11, 2, 22, 0)      # winter time

# 4. the public state: no journal, decisions per pair, provoz
state = {"aktualizovano": "2026-10-22T21:10+00:00", "pary": [{"par": "EUR/USD", "cena": 1.1}, {"par": "USD/JPY"}],
         "denik_uzivatele": {"otevrene": [{"id": "x"}]}, "signaly": []}
cb = {"EUR/USD": [["2026-10-28", "Fed"], ["2026-10-29", "ECB"]]}
pub = WS.public_state(state, U(2026, 10, 22, 21, 10), "https://run", "https://runs", cb)
assert "denik_uzivatele" not in pub and "denik_uzivatele" in state, "denik se nesmi zverejnit (a vstup se nemeni)"
assert pub["pary"][0]["rozhodnuti_cb"] == cb["EUR/USD"] and pub["pary"][1]["rozhodnuti_cb"] == []
assert pub["provoz"]["dalsi_aktualizace_do"] == "2026-10-24T03:00+00:00", pub["provoz"]
assert pub["provoz"]["beh_url"] == "https://run" and pub["provoz"]["behy_url"] == "https://runs"

# 5. the central bank decisions come from the tracked calendar (learning/udalosti_historie.json), same as live
from datetime import date  # noqa: E402
import signals_live as SL  # noqa: E402
got = WS.cb_by_pair(["EUR/USD"], date(2026, 10, 22))
assert got["EUR/USD"] == [[d.isoformat(), b] for d, b in SL.cb_decisions("EUR/USD", date(2026, 10, 21), WS.CB_DAYS)]

# 6. the whole site: index.html is a full document with the page script, stav.json without the journal
out = Path(tempfile.mkdtemp()) / "site"
src = Path(tempfile.mkdtemp()) / "stav.json"
src.write_text(json.dumps(state))
WS.build(src, out, None, None, now=U(2026, 10, 22, 21, 10))
html = (out / "index.html").read_text(encoding="utf-8")
assert html.startswith("<!doctype html>") and '<meta charset="utf-8">' in html and "noindex" in html
assert html.index("</style>") < html.index("</head>") < html.index('id="status"') < html.index("</body>")
assert "function bootWeb" in html and "fetch(\"stav.json" in html
pub_file = json.loads((out / "stav.json").read_text(encoding="utf-8"))
assert "denik_uzivatele" not in pub_file and (out / ".nojekyll").exists()

# 7. the smoke test of the rendered page
assert WS.check_dom('<div id="status">Aktualizováno 22. 10.</div><div class="row small" id="zaloha">') == []
assert len(WS.check_dom('<div id="status">Data modelu se nepodařilo načíst.</div><div id="zaloha" hidden="">')) == 3

print("J1 GitHub provoz a verejna stranka: OK")
