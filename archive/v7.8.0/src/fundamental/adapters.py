"""Download + parse the public fundamental sources (RAW -> NORMALIZED).

Each `update_*` function:
1. downloads one payload (or a few),
2. stores the exact bytes with SHA-256 (module 124) and logs the attempt,
3. parses it into (observation date, value) rows,
4. writes them point-in-time (src/fundamental/store.py).

A source that fails is reported as FAILED with its reason; nothing is
estimated in its place (modules 5, 111). Values that are missing in the
source ('.', '-', empty) are skipped, not zero-filled.
"""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from src.fundamental.catalog import COT_CONTRACTS, COT_LAG_HOURS, SERIES, SeriesSpec
from src.fundamental.store import (
    available_at_for,
    get_fund_connection,
    initialize_fundamentals,
    log_fetch,
    store_payload,
    upsert_series,
)
from src.sources.http import FetchError, fetch

PARSER_VERSION = "fund-1"
UTC = timezone.utc


@dataclass
class SourceResult:
    source: str
    ok: bool = True
    detail: str = ""
    series: dict = field(default_factory=dict)     # series_id -> (inserted, revised, last_date)


def _number(text) -> float | None:
    if text is None:
        return None

    text = str(text).strip().replace("%", "")

    if text in ("", ".", "-", "NA", "N/A", "NaN"):
        return None

    try:
        return float(text)
    except ValueError:
        return None


def _archive(source_id: str, endpoint: str, status: int, content: bytes, kind: str = "SERIES") -> int:
    stored = store_payload(
        source_id=source_id, kind=kind, endpoint=endpoint, instrument=None, side=None,
        period_start=None, period_end=None, http_status=status, content=content,
        parser_version=PARSER_VERSION,
    )
    log_fetch(source_id, endpoint, "OK", None, status, f"{len(content)} B sha256={stored.sha256[:12]}")
    return stored.payload_id


def _get(source_id: str, url: str, params: dict | None = None, kind: str = "SERIES") -> tuple[bytes, int]:
    try:
        status, content, final_url = fetch(url, params=params)
    except FetchError as exc:
        log_fetch(source_id, url, "FAILED", None, None, str(exc))
        raise

    endpoint = final_url if len(final_url) < 480 else url
    return content, _archive(source_id, endpoint, status, content, kind)


def _write(result: SourceResult, spec: SeriesSpec, rows: list[tuple[date, float]], payload_id: int) -> None:
    rows = sorted(rows)
    outcome = upsert_series(spec.series_id, rows, spec.lag_hours, spec.source, payload_id)
    result.series[spec.series_id] = (
        outcome.inserted,
        outcome.revised,
        rows[-1][0].isoformat() if rows else None,
    )


# ----------------------------------------------------------------------
# parsers (pure functions, tested with frozen samples)
# ----------------------------------------------------------------------

def parse_fred_csv(content: bytes) -> list[tuple[date, float]]:
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    header = next(reader, None)

    if not header or len(header) < 2 or "date" not in header[0].lower():
        raise ValueError(f"unexpected FRED header: {header}")

    rows = []

    for record in reader:
        if len(record) < 2:
            continue

        value = _number(record[1])

        if value is not None:
            rows.append((date.fromisoformat(record[0]), value))

    return rows


def parse_ecb_csv(content: bytes) -> list[tuple[date, float]]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = []

    for record in reader:
        value = _number(record.get("OBS_VALUE"))

        if value is not None and record.get("TIME_PERIOD"):
            rows.append((date.fromisoformat(record["TIME_PERIOD"][:10]), value))

    return rows


def parse_mof_csv(content: bytes) -> dict[str, list[tuple[date, float]]]:
    text = content.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    reader = csv.reader(lines[header_index:])
    header = next(reader)
    out: dict[str, list] = {name: [] for name in header[1:]}

    for record in reader:
        if not record or "/" not in record[0]:
            continue

        try:
            y, m, d = (int(x) for x in record[0].split("/"))
            obs = date(y, m, d)
        except ValueError:
            continue

        for name, raw in zip(header[1:], record[1:]):
            value = _number(raw)

            if value is not None:
                out[name].append((obs, value))

    return out


def parse_boe_csv(content: bytes) -> dict[str, list[tuple[date, float]]]:
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    header = next(reader)

    if header[0].upper() != "DATE":
        raise ValueError(f"unexpected BoE header: {header[:3]}")

    out: dict[str, list] = {code: [] for code in header[1:]}

    for record in reader:
        if not record:
            continue

        obs = datetime.strptime(record[0].strip(), "%d %b %Y").date()

        for code, raw in zip(header[1:], record[1:]):
            value = _number(raw)

            if value is not None:
                out[code].append((obs, value))

    return out


def parse_boc_json(content: bytes) -> dict[str, list[tuple[date, float]]]:
    data = json.loads(content)
    out: dict[str, list] = {}

    for observation in data.get("observations", []):
        obs = date.fromisoformat(observation["d"])

        for key, cell in observation.items():
            if key == "d" or not isinstance(cell, dict):
                continue

            value = _number(cell.get("v"))

            if value is not None:
                out.setdefault(key, []).append((obs, value))

    return out


def parse_rba_csv(content: bytes) -> dict[str, list[tuple[date, float]]]:
    lines = content.decode("utf-8-sig", errors="replace").splitlines()
    ids_index = next(i for i, line in enumerate(lines) if line.startswith("Series ID"))
    ids = next(csv.reader([lines[ids_index]]))[1:]
    out: dict[str, list] = {code: [] for code in ids}

    for record in csv.reader(lines[ids_index + 1:]):
        if not record or not record[0].strip():
            continue

        try:
            obs = datetime.strptime(record[0].strip(), "%d-%b-%Y").date()
        except ValueError:
            continue

        for code, raw in zip(ids, record[1:]):
            value = _number(raw)

            if value is not None:
                out[code].append((obs, value))

    return out


def parse_bis_csv(content: bytes) -> dict[str, list[tuple[date, float]]]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    out: dict[str, list] = {}

    for record in reader:
        value = _number(record.get("OBS_VALUE"))

        if value is None or not record.get("TIME_PERIOD"):
            continue

        out.setdefault(record["REF_AREA"], []).append((date.fromisoformat(record["TIME_PERIOD"]), value))

    return out


# ----------------------------------------------------------------------
# update functions
# ----------------------------------------------------------------------

def _specs(source: str) -> list[SeriesSpec]:
    return [s for s in SERIES if s.source == source]


def update_fred(start: date) -> SourceResult:
    result = SourceResult("FRED")

    for spec in _specs("FRED"):
        try:
            content, payload_id = _get("FRED", "https://fred.stlouisfed.org/graph/fredgraph.csv",
                                       {"id": spec.code, "cosd": start.isoformat()})
            _write(result, spec, parse_fred_csv(content), payload_id)
        except (FetchError, ValueError) as exc:
            result.ok = False
            result.detail += f"{spec.code}: {exc}; "

    return result


def update_ecb(start: date) -> SourceResult:
    result = SourceResult("ECB")

    for spec in _specs("ECB"):
        try:
            content, payload_id = _get(
                "ECB", f"https://data-api.ecb.europa.eu/service/data/{spec.code}",
                {"startPeriod": start.isoformat(), "format": "csvdata"},
            )
            _write(result, spec, parse_ecb_csv(content), payload_id)
        except (FetchError, ValueError) as exc:
            result.ok = False
            result.detail += f"{spec.code}: {exc}; "

    return result


def update_mof(start: date) -> SourceResult:
    result = SourceResult("MOF")
    combined: dict[str, list] = {}

    urls = [
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",
    ]
    payload_id = None

    for url in urls:
        try:
            content, payload_id = _get("MOF", url)
            for name, rows in parse_mof_csv(content).items():
                combined.setdefault(name, []).extend(r for r in rows if r[0] >= start)
        except (FetchError, ValueError, StopIteration) as exc:
            result.ok = False
            result.detail += f"{url.rsplit('/', 1)[-1]}: {exc}; "

    for spec in _specs("MOF"):
        rows = sorted(set(combined.get(spec.code, [])))

        if rows:
            _write(result, spec, rows, payload_id)

    return result


def update_boe(start: date) -> SourceResult:
    result = SourceResult("BOE")
    specs = _specs("BOE")

    try:
        content, payload_id = _get(
            "BOE", "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp",
            {
                "csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": "now",
                "SeriesCodes": ",".join(s.code for s in specs), "CSVF": "TN",
                "UsingCodes": "Y", "VPD": "Y", "VFD": "N",
            },
        )
        parsed = parse_boe_csv(content)
    except (FetchError, ValueError) as exc:
        return SourceResult("BOE", False, str(exc))

    for spec in specs:
        _write(result, spec, parsed.get(spec.code, []), payload_id)

    return result


def update_boc(start: date) -> SourceResult:
    result = SourceResult("BOC")
    specs = _specs("BOC")

    try:
        content, payload_id = _get(
            "BOC", f"https://www.bankofcanada.ca/valet/observations/{','.join(s.code for s in specs)}/json",
            {"start_date": start.isoformat()},
        )
        parsed = parse_boc_json(content)
    except (FetchError, ValueError) as exc:
        return SourceResult("BOC", False, str(exc))

    for spec in specs:
        _write(result, spec, parsed.get(spec.code, []), payload_id)

    return result


def update_rba(start: date) -> SourceResult:
    result = SourceResult("RBA")

    try:
        content, payload_id = _get("RBA", "https://www.rba.gov.au/statistics/tables/csv/f2-data.csv")
        parsed = parse_rba_csv(content)
    except (FetchError, ValueError, StopIteration) as exc:
        return SourceResult("RBA", False, str(exc))

    for spec in _specs("RBA"):
        _write(result, spec, [r for r in parsed.get(spec.code, []) if r[0] >= start], payload_id)

    return result


def update_bis(start: date) -> SourceResult:
    result = SourceResult("BIS")
    specs = _specs("BIS")

    try:
        content, payload_id = _get(
            "BIS", f"https://stats.bis.org/api/v1/data/WS_CBPOL/D.{'+'.join(s.code for s in specs)}",
            {"startPeriod": start.isoformat(), "format": "csv"},
        )
        parsed = parse_bis_csv(content)
    except (FetchError, ValueError) as exc:
        return SourceResult("BIS", False, str(exc))

    for spec in specs:
        _write(result, spec, parsed.get(spec.code, []), payload_id)

    return result


COT_FIELDS = (
    "report_date_as_yyyy_mm_dd", "cftc_contract_market_code", "open_interest_all",
    "dealer_positions_long_all", "dealer_positions_short_all",
    "asset_mgr_positions_long", "asset_mgr_positions_short",
    "lev_money_positions_long", "lev_money_positions_short",
)


def update_cot(start: date) -> SourceResult:
    """CFTC Traders in Financial Futures -> net positioning series (module 25).

    COT.<CCY>.LEV_NET_PCT  leveraged funds net long in % of open interest
    COT.<CCY>.AM_NET_PCT   asset managers net long in % of open interest
    Positive = long the currency against USD. Weekly, slow (module 25).
    """
    result = SourceResult("CFTC")
    by_code = {code: ccy for ccy, code in COT_CONTRACTS.items()}
    codes = ",".join(f"'{c}'" for c in COT_CONTRACTS.values())

    try:
        content, payload_id = _get(
            "CFTC", "https://publicreporting.cftc.gov/resource/gpe5-46if.json",
            {
                "$select": ",".join(COT_FIELDS),
                "$where": f"cftc_contract_market_code in({codes}) AND "
                          f"report_date_as_yyyy_mm_dd >= '{start.isoformat()}'",
                "$order": "report_date_as_yyyy_mm_dd",
                "$limit": "50000",
            },
        )
        records = json.loads(content)
    except (FetchError, ValueError) as exc:
        return SourceResult("CFTC", False, str(exc))

    series: dict[str, list] = {}
    raw_rows = []

    for record in records:
        currency = by_code.get(record.get("cftc_contract_market_code"))
        oi = _number(record.get("open_interest_all"))

        if currency is None or not oi:
            continue

        report = date.fromisoformat(record["report_date_as_yyyy_mm_dd"][:10])
        values = {k: _number(record.get(k)) or 0.0 for k in COT_FIELDS[3:]}
        lev = values["lev_money_positions_long"] - values["lev_money_positions_short"]
        am = values["asset_mgr_positions_long"] - values["asset_mgr_positions_short"]
        series.setdefault(f"COT.{currency}.LEV_NET_PCT", []).append((report, 100.0 * lev / oi))
        series.setdefault(f"COT.{currency}.AM_NET_PCT", []).append((report, 100.0 * am / oi))
        raw_rows.append((currency, report.isoformat(), record["cftc_contract_market_code"], oi,
                         values["dealer_positions_long_all"], values["dealer_positions_short_all"],
                         values["asset_mgr_positions_long"], values["asset_mgr_positions_short"],
                         values["lev_money_positions_long"], values["lev_money_positions_short"],
                         available_at_for(report, COT_LAG_HOURS), payload_id))

    initialize_fundamentals()

    with get_fund_connection() as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO cot_reports (currency, report_date, contract_code, open_interest, "
            "dealer_long, dealer_short, asset_mgr_long, asset_mgr_short, lev_money_long, lev_money_short, "
            "available_at, payload_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            raw_rows,
        )
        connection.commit()

    for series_id, rows in series.items():
        outcome = upsert_series(series_id, sorted(rows), COT_LAG_HOURS, "CFTC", payload_id)
        result.series[series_id] = (outcome.inserted, outcome.revised, max(rows)[0].isoformat())

    return result


UPDATERS = (
    update_bis,
    update_fred,
    update_ecb,
    update_mof,
    update_boe,
    update_boc,
    update_rba,
    update_cot,
)


def update_all(start: date | None = None) -> list[SourceResult]:
    start = start or (datetime.now(UTC).date() - timedelta(days=60))
    results = []

    for updater in UPDATERS:
        try:
            results.append(updater(start))
        except Exception as exc:          # one source never stops the others
            results.append(SourceResult(updater.__name__.replace("update_", "").upper(), False,
                                        f"{type(exc).__name__}: {exc}"))

    return results
