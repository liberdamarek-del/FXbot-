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
assert k == {"denni": "2026-10-22", "patek": "", "uceni": "2026-10-22", "hodina": "2026-10-22T21"}, k
k = GB.keys(U(2026, 10, 22, 20, 59))                   # Thursday 16:59 New York: the last close is Wednesday's
assert k["denni"] == "2026-10-21" and k["patek"] == "", k
k = GB.keys(U(2026, 10, 23, 20, 5))                    # Friday 16:05 New York: the Friday decision is due
assert k == {"denni": "2026-10-22", "patek": "2026-10-23", "uceni": "2026-10-23", "hodina": "2026-10-23T20"}, k
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
# hourly refresh (R-051, "ostry"): cron "12 * * * 1-5" UTC, three hours of tolerance
assert WS.next_hourly(U(2026, 10, 22, 21, 10)) == U(2026, 10, 22, 21, 12)
assert WS.next_hourly(U(2026, 10, 22, 21, 12)) == U(2026, 10, 22, 22, 12)                          # strictly after
assert WS.next_hourly(U(2026, 10, 23, 23, 30)) == U(2026, 10, 26, 0, 12)                           # Friday night -> Monday
assert WS.next_hourly(U(2026, 10, 25, 23, 59)) == U(2026, 10, 26, 0, 12)                           # Sunday
assert WS.deadline(U(2026, 10, 22, 21, 10), "ostry") == U(2026, 10, 23, 0, 12)
assert WS.deadline(U(2026, 10, 22, 21, 10), "stin") == U(2026, 10, 24, 3, 0)

# 4. the public state: no journal, decisions per pair, provoz
state = {"aktualizovano": "2026-10-22T21:10+00:00", "pary": [{"par": "EUR/USD", "cena": 1.1}, {"par": "USD/JPY"}],
         "denik_uzivatele": {"otevrene": [{"id": "x"}]}, "signaly": []}
cb = {"EUR/USD": [["2026-10-28", "Fed"], ["2026-10-29", "ECB"]]}
pub = WS.public_state(state, U(2026, 10, 22, 21, 10), "https://run", "https://runs", cb)
assert "denik_uzivatele" not in pub and "denik_uzivatele" in state, "denik se nesmi zverejnit (a vstup se nemeni)"
assert pub["pary"][0]["rozhodnuti_cb"] == cb["EUR/USD"] and pub["pary"][1]["rozhodnuti_cb"] == []
assert pub["provoz"]["dalsi_aktualizace_do"] == "2026-10-24T03:00+00:00", pub["provoz"]
assert pub["provoz"]["beh_url"] == "https://run" and pub["provoz"]["behy_url"] == "https://runs"
assert pub["provoz"]["rezim"] == "stin" and "23:00" in pub["provoz"]["popis"]
pub_o = WS.public_state(state, U(2026, 10, 22, 21, 10), None, None, cb, "ostry")
assert pub_o["provoz"]["dalsi_aktualizace_do"] == "2026-10-23T00:12+00:00" and "každou hodinu" in pub_o["provoz"]["popis"]

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
assert WS.check_dom('<div id="status">Aktualizováno</div><div id="zaloha"><script>x = "Data se načítají"; y = '
                    '"nepodařilo načíst"</script>') == [], "texty ve skriptu stranky se nepocitaji"
assert len(WS.check_dom('<div id="status">Data modelu se nepodařilo načíst.</div><div id="zaloha" hidden="">')) == 3

# 8. notifications (R-051): model trades opened / closed against the last commit, new diagnostics errors
t_open = {"id": "2026-10-23_EURUSD", "par": "EUR/USD", "smer": "KOUPIT", "vstup": 1.16, "tp": 1.17, "sl": 1.14, "stav": "otevreny"}
t_old = {"id": "2026-10-02_EURJPY", "par": "EUR/JPY", "smer": "KOUPIT", "stav": "otevreny", "prubezne_proc_marze": -29.7}
t_closed = dict(t_old, stav="uzavreny", duvod_vystupu="TP", vysledek_proc_marze=12.25)
assert GB.model_changes([t_old], [t_old]) == []                                    # a running value alone is no news
assert GB.model_changes([t_old], [dict(t_old, prubezne_proc_marze=-20.0)]) == []
ch = GB.model_changes([t_old], [t_closed, t_open])
assert ch[0] == "Model zavřel EUR/JPY KOUPIT na cíli (TP): +12.2 % marže." and ch[1].startswith("Model otevřel EUR/USD KOUPIT"), ch
assert "před rozhodnutím" in GB.model_changes([t_old], [dict(t_closed, duvod_vystupu="pred rozhodnutim CB")])[0]
assert "NEOVĚŘENO" in GB.model_changes([t_old], [dict(t_closed, vysledek_proc_marze=None)])[0]
assert GB.model_changes(None, [t_old])[0].startswith("Model otevřel")              # no previous commit
beat = {"denni": {"cas": "2026-10-22T21:10+00:00", "diagnostika": {"chyby": ["ceny: stara data"]}},
        "hodina": {"cas": "2026-10-22T22:12+00:00", "diagnostika": {"chyby": []}}}
assert GB.new_errors(["ceny: stara data"], beat) == ["ceny: stara data"]           # the LAST run had no error
beat["hodina"]["diagnostika"]["chyby"] = ["ceny: stara data"]
assert GB.new_errors(["ceny: stara data"], beat) == [] and GB.new_errors(["x"], None) == ["x"]

# send or not: the daily / Friday / learning runs always, an hourly run only with news
tmp = Path(tempfile.mkdtemp())
orig = (GB.STAV, GB.FORWARD, GB.committed)
try:
    GB.STAV, GB.FORWARD = tmp / "stav.json", tmp / "forward.json"
    GB.STAV.write_text(json.dumps({"signaly": [], "model": {"obchody": [t_old], "uzavrenych": 1, "ziskovych": 1},
                                   "diagnostika": {"souhrn": {"OK": 30, "CHYBA": 0}, "problemy": []}}))
    GB.FORWARD.write_text(json.dumps([t_old]))
    GB.committed = lambda rel: [t_old] if rel.endswith("forward_trades.json") else beat
    assert GB.summary("hodina")["poslat"] is False
    assert GB.summary("denni")["poslat"] is True and GB.summary("uceni")["priority"] == 2
    f = GB.summary("patek")
    assert f["poslat"] and f["title"] == "FXBOT pátek: žádný signál" and f["priority"] == 4
    GB.FORWARD.write_text(json.dumps([t_closed]))
    h = GB.summary("hodina")
    assert h["poslat"] and h["title"] == "FXBOT: změna u obchodů modelu" and h["lines"][0].startswith("Model zavřel"), h
    GB.FORWARD.write_text(json.dumps([t_old]))
    GB.STAV.write_text(json.dumps({"signaly": [], "model": {}, "diagnostika": {"souhrn": {"CHYBA": 1},
                                                                                "problemy": ["sazby: chybi"]}}))
    h = GB.summary("hodina")
    assert h["poslat"] and h["title"] == "FXBOT: nová chyba" and h["priority"] == 4, h
    beat["hodina"]["diagnostika"]["chyby"] = ["sazby: chybi"]
    assert GB.summary("hodina")["poslat"] is False                                 # the same error again: quiet
    GB.STAV.unlink()
    assert GB.summary("hodina")["poslat"] is False and GB.summary("denni")["poslat"] is True
finally:
    GB.STAV, GB.FORWARD, GB.committed = orig
# no topic: nothing is sent, the run never fails because of a notification
os.environ.pop("FXBOT_NTFY_TEMA", None)
assert GB.post({"title": "x", "lines": []}) == 0 and GB.notify_failure("hodina") == 0 and GB.notify_failure("patek") == 0

print("J1 GitHub provoz a verejna stranka: OK")
