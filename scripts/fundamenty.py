"""History of scheduled fundamental events and macro data for the tests.

    python scripts/fundamenty.py download     # -> learning/udalosti_historie.json, data/research/fundamenty/*.json
    python scripts/fundamenty.py status

Events (dates of scheduled announcements, all known in advance - the
schedules are published a year ahead, so a filter on them uses no hindsight;
unscheduled meetings are left out):
    FED      FOMC decisions (federalreserve.gov calendars, 2012-)
    ECB      Governing Council monetary policy decisions (ecb.europa.eu, 2012-)
    BOJ      Monetary Policy Meeting decisions (boj.or.jp statements, 2012-)
    BOE      MPC decisions (bankofengland.co.uk minutes / summaries, 2012-)
    US_NFP   US Employment Situation release dates (ALFRED release 50)
    US_CPI   US CPI release dates (ALFRED release 10)
Macro (OECD SDMX, monthly, point in time with a publication lag set in the
loader): CPI inflation y/y and the unemployment rate per currency area.
Sources that failed are reported, never filled in.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.sources.http import fetch  # noqa: E402

EVENTS = PROJECT_ROOT / "learning" / "udalosti_historie.json"
MACRO = PROJECT_ROOT / "data" / "research" / "fundamenty"
FIRST, LAST = 2012, 2027
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
MON = {m[:3]: k + 1 for k, m in enumerate(MONTHS)}
CB_OF = {"USD": "FED", "EUR": "ECB", "JPY": "BOJ", "GBP": "BOE"}
CB_OF_ALL = {**CB_OF, "CHF": "SNB", "AUD": "RBA"}          # wider set (R-023 experiment)


def _get(url: str) -> str:
    _, content, _ = fetch(url, retries=2)
    return content.decode("utf-8", "ignore")


def _try(url: str) -> str | None:
    try:
        return _get(url)
    except Exception:
        return None


# ----------------------------------------------------------------------
# central banks
# ----------------------------------------------------------------------

def _range_end(year: int, month_text: str, days_text: str) -> date | None:
    """'January 27-28' / 'April 30-May 1' / ('Apr/May', '30-1') -> the decision (last) day."""
    months = [MON[m[:3].lower()] for m in re.findall(r"[A-Za-z]+", month_text) if m[:3].lower() in MON]
    days = [int(d) for d in re.findall(r"\d+", days_text)]
    if not months or not days:
        return None
    return date(year, months[-1], days[-1])


def fed() -> list[str]:
    out = set()
    for year in range(FIRST, 2021):
        page = _get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
        for head in re.findall(r"<h5[^>]*>(.*?)</h5>", page):
            m = re.match(r"\s*([A-Za-z/]+(?:\s*\d+)?(?:-[A-Za-z]*\s*\d+)?)\s+Meeting\s*-\s*(\d{4})", head)
            if not m or "unscheduled" in head.lower():
                continue
            text = m.group(1)
            d = _range_end(int(m.group(2)), " ".join(re.findall(r"[A-Za-z]+", text)), " ".join(re.findall(r"\d+", text)))
            if d:
                out.add(d.isoformat())
    page = _get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    for part in re.split(r"(?=\b\d{4} FOMC Meetings)", page)[1:]:
        year = int(part[:4])
        for month, days in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>(.*?)</strong>.*?'
                                      r'fomc-meeting__date[^>]*>(.*?)</div>', part, re.S):
            if "unscheduled" in days.lower() or "notation" in days.lower():
                continue
            d = _range_end(year, month, days)
            if d:
                out.add(d.isoformat())
    return sorted(out)


def ecb() -> list[str]:
    out = set()
    for year in range(FIRST, LAST + 1):
        page = _try(f"https://www.ecb.europa.eu/press/govcdec/mopo/{year}/html/index_include.en.html")
        if not page:
            continue
        for iso, title in re.findall(r'<dt isoDate="(\d{4}-\d{2}-\d{2})">.*?<div class="title"><a[^>]*>(.*?)</a>',
                                     page, re.S):
            if "monetary policy decision" in title.lower():
                out.add(iso)
    return sorted(out)


def ecb_future() -> list[str]:
    """Scheduled decisions from the Governing Council meeting calendar (day 2 = decision day)."""
    page = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", _get("https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html")))
    out = set()
    for d, m, y, text in re.findall(r"(\d{2})/(\d{2})/(\d{4})[ |]+([^|]{0,120})", page):
        t = text.lower()
        if "monetary policy meeting" in t and "non-monetary" not in t and "day 1" not in t:
            out.add(f"{y}-{m}-{d}")
    return sorted(out)


def boj_future() -> list[str]:
    """Scheduled Monetary Policy Meetings on the schedule page (decision = last
    day). The year of each row is the one whose calendar matches the weekday
    printed next to the day (the page shows this and next year)."""
    page = _get("https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm")
    names = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    this = date.today().year
    out = set()
    for row in re.findall(r"<tr.*?</tr>", page, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        if not cells:
            continue
        first = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cells[0]))
        m = re.match(r"\s*([A-Z][a-z]+)\.?\s+\d", first)
        last = re.findall(r"(\d{1,2})\s*\(([A-Za-z]+)\.?\)", first)
        if not m or not last or m.group(1)[:3].lower() not in MON:
            continue
        day, weekday = int(last[-1][0]), last[-1][1][:3].lower()
        for year in (this, this + 1):
            try:
                d = date(year, MON[m.group(1)[:3].lower()], day)
            except ValueError:
                continue
            if names[d.weekday()] == weekday:
                out.add(d.isoformat())
    return sorted(out)


def boj() -> list[str]:
    out = set()
    for year in range(FIRST, LAST + 1):
        page = _try(f"https://www.boj.or.jp/en/mopo/mpmdeci/state_{year}/index.htm")
        if not page:
            continue
        for ymd in re.findall(r"k(\d{6})a\.(?:pdf|htm)", page):
            out.add(f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:]}")
    return sorted(out)


def boe() -> list[str]:
    urls = []
    for year in range(FIRST, LAST):
        for month in MONTHS:
            urls.append(f"https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/{year}/{month}-{year}")
            urls.append(f"https://www.bankofengland.co.uk/minutes/{year}/monetary-policy-committee-{month}-{year}")
    with ThreadPoolExecutor(8) as pool:
        pages = list(pool.map(_try, urls))
    out = set()
    for url, page in zip(urls, pages):
        if not page:
            continue
        year = int(re.search(r"/(\d{4})/", url).group(1))
        title = " ".join(re.findall(r"<title>(.*?)</title>", page, re.S))
        held = re.search(r"(?:held on|ending) ([\d\s,and]+)\s+([A-Za-z]+)(?:\s+(\d{4}))?", title)
        if held:                                          # minutes: decision = last meeting day
            d = _range_end(int(held.group(3) or year), held.group(2), held.group(1))
            if d:
                out.add(d.isoformat())
            continue
        # summaries (2015-): the publication date of the decision is in the page metadata
        meta = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', page) or \
            re.search(r'published-date[^>]*>\s*(?:Published on\s*)?(\d{1,2}\s+[A-Za-z]+\s+\d{4})', page)
        if meta:
            text = meta.group(1)
            if re.match(r"\d{4}-", text):
                out.add(text)
            else:
                dd, mm, yy = text.split()
                out.add(date(int(yy), MON[mm[:3].lower()], int(dd)).isoformat())
    return sorted(out)


def snb() -> list[str]:
    """Scheduled quarterly SNB assessments (March, June, September, December) from the decisions page."""
    page = _get("https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions")
    out = set()
    for d, m, y in re.findall(r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|"
                              r"November|December) (20\d\d)", page):
        mm = MON[m[:3].lower()]
        if int(y) >= FIRST and mm in (3, 6, 9, 12):
            out.add(date(int(y), mm, int(d)).isoformat())
    return sorted(out)


def rba() -> list[str]:
    """RBA monetary policy decisions (media releases "...: Monetary Policy Decision")."""
    out = set()
    for year in range(FIRST, LAST):
        page = _try(f"https://www.rba.gov.au/media-releases/{year}/")
        if not page:
            continue
        for item in re.findall(r'<(?:article|li) class="item[^"]*".*?</(?:article|li)>', page, re.S):
            if "Monetary Policy Decision" in item:
                m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', item)
                if m:
                    out.add(m.group(1))
    return sorted(out)


def alfred(rid: int) -> list[str]:
    page = _get(f"https://alfred.stlouisfed.org/release/downloaddates?rid={rid}&ff=txt")
    return sorted({d for d in re.findall(r"^(\d{4}-\d{2}-\d{2})\s*$", page, re.M) if d >= f"{FIRST}"})


# ----------------------------------------------------------------------
# macro (OECD SDMX)
# ----------------------------------------------------------------------

AREAS = {"USD": "USA", "EUR": "EA20", "JPY": "JPN", "GBP": "GBR", "CHF": "CHE", "AUD": "AUS", "CAD": "CAN",
         "NZD": "NZL"}


def oecd_csv(flow: str, key: str) -> list[dict]:
    page = _get(f"https://sdmx.oecd.org/public/rest/data/{flow}/{key}?startPeriod={FIRST - 2}-01&format=csvfilewithlabels")
    lines = page.strip().splitlines()
    head = [h.strip('"') for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        cells = [c.strip('"') for c in re.findall(r'("[^"]*"|[^,]*)(?:,|$)', line)]
        rows.append(dict(zip(head, cells)))
    return rows


def macro() -> dict:
    out = {"cpi": {}, "unemployment": {}, "errors": []}
    for ccy, area in AREAS.items():
        for name, flow, key in (
                ("cpi", "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0", f"{area}.M.N.CPI.PA._T.N.GY"),
                ("cpi", "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0", f"{area}.Q.N.CPI.PA._T.N.GY"),
                ("unemployment", "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,1.0", f"{area}..._Z.Y._T.Y_GE15..M")):
            if ccy in out[name]:
                continue
            try:
                rows = oecd_csv(flow, key)
            except Exception as exc:
                out["errors"].append(f"{name} {ccy} {key}: {str(exc)[:80]}")
                continue
            series = {}
            for r in rows:
                period, value = r.get("TIME_PERIOD", ""), r.get("OBS_VALUE", "")
                if not value:
                    continue
                if "-Q" in period:                     # quarter -> its last month
                    y, q = period.split("-Q")
                    period = f"{y}-{int(q) * 3:02d}"
                series[period] = float(value)
            if series:
                out[name][ccy] = dict(sorted(series.items()))
    return out


BIS_AREAS = {"USD": "US", "EUR": "XM", "JPY": "JP", "GBP": "GB", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}
BIS_QUARTERLY = {"AUD", "NZD"}             # monthly rows repeat the quarterly figure (known ~4 weeks after the quarter)


def bis_cpi() -> dict:
    """Consumer price inflation y/y in % (BIS long CPI series, monthly; AUD and NZD quarterly figures
    repeated per month) for the 8 currencies, {currency: {"YYYY-MM": value}}."""
    out = {}
    for ccy, area in BIS_AREAS.items():
        page = _get(f"https://stats.bis.org/api/v1/data/WS_LONG_CPI/M.{area}.771?format=csv&startPeriod={FIRST - 2}-01")
        lines = page.strip().splitlines()
        head = lines[0].split(",")
        k_t, k_v = head.index("TIME_PERIOD"), head.index("OBS_VALUE")
        out[ccy] = {c[k_t]: float(c[k_v]) for c in (line.split(",") for line in lines[1:]) if c[k_v]}
    return out


def download() -> int:
    events, errors = {}, []
    for name, job in (("FED", fed), ("ECB", lambda: sorted(set(ecb()) | set(ecb_future()))),
                      ("BOJ", lambda: sorted(set(boj()) | set(boj_future()))), ("BOE", boe), ("SNB", snb), ("RBA", rba),
                      ("US_NFP", lambda: alfred(50)), ("US_CPI", lambda: alfred(10))):
        try:
            events[name] = job()
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:100]}")
            events[name] = []
        per_year = {}
        for d in events[name]:
            per_year[d[:4]] = per_year.get(d[:4], 0) + 1
        print(f"{name}: {len(events[name])} dates, per year {per_year}", flush=True)
    EVENTS.write_text(json.dumps({"stazeno": date.today().isoformat(), "chyby": errors, **events}, indent=1))
    MACRO.mkdir(parents=True, exist_ok=True)
    m = macro()
    try:
        m["cpi_bis"] = bis_cpi()
    except Exception as exc:
        m["errors"].append(f"cpi_bis: {type(exc).__name__}: {str(exc)[:80]}")
    (MACRO / "macro.json").write_text(json.dumps(m, indent=1))
    for name in ("cpi", "unemployment", "cpi_bis"):
        print(name, {c: (min(v), max(v), len(v)) for c, v in m.get(name, {}).items()})
    print("errors:", errors + m["errors"])
    return 0


def load_events() -> dict:
    return json.loads(EVENTS.read_text()) if EVENTS.exists() else {}


def main(argv: list[str]) -> int:
    if argv and argv[0] == "download":
        return download()
    ev = load_events()
    print({k: len(v) for k, v in ev.items() if isinstance(v, list)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
