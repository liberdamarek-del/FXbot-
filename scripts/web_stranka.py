"""Static copy of the dashboard for GitHub Pages (R-050, user's decision 2026-10-22: the bot runs on GitHub Actions
and the page opens in any browser without Claude).

    python scripts/web_stranka.py [--stav data/live/stav.json] [--ven _site] [--beh-url URL] [--behy-url URL]
    python scripts/web_stranka.py kontrola DOM.html     # smoke test of the page rendered by a headless browser

Writes <ven>/index.html (web/prehled.html in a full HTML document) and <ven>/stav.json next to it. The page finds no
claude.ai runtime there, loads stav.json itself and keeps the user's journal in the browser.

stav.json is public (the repository and the Pages site are public), so the user's journal summary
(`denik_uzivatele`) is removed. Added fields:
  pary[].rozhodnuti_cb  next scheduled central bank decisions of the pair's currencies, [[YYYY-MM-DD, "Fed"], ...]
                        (signals_live.cb_decisions) - the page warns about the user's own open trades with the same
                        rule as aktualizace.journal_summary;
  provoz                where and when it ran, and by when the next update is due (the page warns after that).
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

NEW_YORK = ZoneInfo("America/New_York")
PRAGUE = ZoneInfo("Europe/Prague")
PRIVATE_KEYS = ("denik_uzivatele",)          # personal data never published
GRACE = timedelta(hours=6)                   # GitHub can start scheduled runs late (docs: delays under high load)
CB_DAYS = 21


def next_close(now: datetime) -> datetime:
    """The next daily FX close (17:00 New York, Monday to Friday) strictly after `now`."""
    t = now.astimezone(NEW_YORK)
    d = t.date()
    while True:
        close = datetime.combine(d, time(17, 0), NEW_YORK)
        if d.weekday() < 5 and close > t:
            return close
        d += timedelta(days=1)


def cb_by_pair(pairs: list[str], today: date) -> dict:
    import signals_live as SL
    return {p: [[d.isoformat(), label] for d, label in SL.cb_decisions(p, today - timedelta(days=1), CB_DAYS)]
            for p in pairs}


def public_state(state: dict, now: datetime, beh_url: str | None, behy_url: str | None, cb: dict) -> dict:
    out = {k: v for k, v in state.items() if k not in PRIVATE_KEYS}
    out["pary"] = [dict(p, rozhodnuti_cb=cb.get(p.get("par"), [])) for p in state.get("pary", [])]
    out["provoz"] = {
        "zdroj": "GitHub Actions",
        "popis": "Obnova ve všední dny po 23:00 našeho času, v pátek i po 22:05 (GitHub)",
        "sestaveno": now.astimezone(timezone.utc).isoformat(timespec="minutes"),
        "dalsi_aktualizace_do": (next_close(now) + GRACE).astimezone(timezone.utc).isoformat(timespec="minutes"),
        "beh_url": beh_url,
        "behy_url": behy_url,
    }
    return out


def html_document(page: str) -> str:
    """web/prehled.html is an artifact body (title, links, style, markup, script); Pages needs a whole document."""
    cut = page.find("</style>")
    head, body = (page[:cut + len("</style>")], page[cut + len("</style>"):]) if cut >= 0 else ("", page)
    return ("<!doctype html>\n<html lang=\"cs\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"{head}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")


def build(stav: Path, ven: Path, beh_url: str | None, behy_url: str | None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    state = json.loads(stav.read_text(encoding="utf-8"))
    pairs = [p["par"] for p in state.get("pary", []) if "par" in p]
    pub = public_state(state, now, beh_url, behy_url, cb_by_pair(pairs, now.astimezone(PRAGUE).date()))
    if ven.exists():
        shutil.rmtree(ven)
    ven.mkdir(parents=True)
    (ven / "index.html").write_text(html_document((ROOT / "web" / "prehled.html").read_text(encoding="utf-8")),
                                    encoding="utf-8")
    (ven / "stav.json").write_text(json.dumps(pub, ensure_ascii=False, default=str), encoding="utf-8")
    (ven / ".nojekyll").write_text("")
    return pub


def check_dom(dom: str) -> list[str]:
    """What must be on the page once its script has loaded stav.json and rendered (headless browser dump)."""
    problems = []
    if "Aktualizováno" not in dom:
        problems.append("stav modelu se nevykreslil (chybí 'Aktualizováno')")
    if "nepodařilo načíst" in dom:
        problems.append("stránka hlásí, že data nešla načíst")
    if "Data se načítají" in dom:
        problems.append("některá část zůstala ve stavu 'Data se načítají'")
    if 'id="zaloha" hidden' in dom:
        problems.append("deník v prohlížeči se nezapnul (lišta zálohy je skrytá)")
    return problems


def browser_check(site: Path, dump: Path | None = None) -> list[str]:
    """Open the built site in a real (headless) Chromium: the state must render, the script must not throw, and a
    journal entry written through the form must show up and survive a reload (the browser journal works)."""
    import functools
    import http.server
    import threading
    from playwright.sync_api import sync_playwright
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    problems: list[str] = []
    rendered = "document.getElementById('status').innerText.includes('Aktualizováno')"
    has_trade = "document.getElementById('open-trades').innerText.includes('Otevřené obchody')"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(locale="cs-CZ", timezone_id="Europe/Prague")
            page.on("pageerror", lambda e: problems.append(f"chyba skriptu: {e}"))
            page.on("console", lambda m: problems.append(f"konzole: {m.text}")
                    if m.type == "error" and "favicon" not in m.text and "fonts.g" not in m.text else None)
            page.goto(url, wait_until="networkidle")
            try:
                page.wait_for_function(rendered, timeout=20000)
            except Exception:
                problems.append("stav se do 20 s nevykreslil")
            html = page.content()
            if dump:
                dump.write_text(html, encoding="utf-8")                  # for the run report (provoz-zprava)
            problems += check_dom(html)
            page.fill("#f-vstup", "1.1")
            page.click("#f-ulozit")
            try:
                page.wait_for_function(has_trade, timeout=5000)
                page.reload(wait_until="networkidle")
                page.wait_for_function(rendered + " && " + has_trade, timeout=20000)
            except Exception:
                problems.append("zápis do deníku v prohlížeči nefunguje (obchod se neobjevil nebo nepřežil obnovení stránky)")
            browser.close()
    finally:
        srv.shutdown()
    return problems


def main(argv: list[str]) -> int:
    if argv[:1] == ["kontrola-prohlizec"]:
        dump = Path(argv[argv.index("--dom") + 1]) if "--dom" in argv else None
        problems = browser_check(Path(argv[1]), dump)
        for p in problems:
            print(f"CHYBA stranky: {p}")
        print("stranka OK (prohlizec)" if not problems else "stranka NENI v poradku")
        return 1 if problems else 0
    if argv[:1] == ["kontrola"]:
        problems = check_dom(Path(argv[1]).read_text(encoding="utf-8", errors="replace"))
        for p in problems:
            print(f"CHYBA stranky: {p}")
        print("stranka OK" if not problems else "stranka NENI v poradku")
        return 1 if problems else 0
    opt = lambda name, default=None: argv[argv.index(name) + 1] if name in argv else default  # noqa: E731
    stav = Path(opt("--stav", str(ROOT / "data" / "live" / "stav.json")))
    ven = Path(opt("--ven", str(ROOT / "_site")))
    pub = build(stav, ven, opt("--beh-url"), opt("--behy-url"))
    print(f"stranka: {ven}/index.html + stav.json ({len(pub.get('pary', []))} paru, signalu {len(pub.get('signaly') or [])}, "
          f"dalsi aktualizace do {pub['provoz']['dalsi_aktualizace_do']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
