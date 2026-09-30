"""Run package, staged commit and read-back verification (modules 99, 104,
112, 124).

Artifacts of a run are written to data/runs/<run_id>/ as JSON (English,
internal audit) plus the Czech report. The commit manifest lists every
artifact with its SHA-256 and the row counts / newest timestamps of every
persistent store. Read-back re-opens every artifact and every database
with NEW connections and checks hashes, counts, run id and the links of the
newly locked predictions. Only after a successful read-back may the run
state become COMMITTED (the run state is the last commit marker).
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.config import DATA_DIR
from src.database import DB_PATH
from src.fundamental.store import FUND_DB
from src.path_archive import PATH_DB

UTC = timezone.utc
RUNS_DIR = DATA_DIR / "runs"


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def write_artifact(run_dir: Path, name: str, content) -> str:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / name

    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = json.dumps(content, indent=1, ensure_ascii=False, sort_keys=True, default=_json_default).encode("utf-8")

    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def store_counts() -> dict:
    """Row counts and newest timestamps of every persistent store."""
    counts = {}

    def count(db: Path, queries: dict) -> dict:
        if not db.exists():
            return {"missing": True}

        out = {}
        connection = sqlite3.connect(db)

        try:
            for key, query in queries.items():
                try:
                    out[key] = connection.execute(query).fetchone()[0]
                except sqlite3.OperationalError:
                    out[key] = None
        finally:
            connection.close()

        return out

    counts["ledger"] = count(DB_PATH, {
        "predictions": "SELECT COUNT(*) FROM predictions",
        "prediction_states": "SELECT COUNT(*) FROM prediction_states",
        "prediction_outcomes": "SELECT COUNT(*) FROM prediction_outcomes",
        "latest_t0": "SELECT MAX(t0) FROM predictions",
        "raw_bars": "SELECT COUNT(*) FROM raw_bars",
        "latest_raw_bar": "SELECT MAX(bar_time) FROM raw_bars WHERE source = 'TwelveData'",
        "runs": "SELECT COUNT(*) FROM runs",
        "thesis_transitions": "SELECT COUNT(*) FROM thesis_transitions",
    })
    counts["market_path"] = count(PATH_DB, {
        "payloads": "SELECT COUNT(*) FROM raw_payloads",
        "days_complete": "SELECT COUNT(*) FROM path_days WHERE state = 'COMPLETE'",
        "months_complete": "SELECT COUNT(*) FROM path_months WHERE state = 'COMPLETE'",
        "bars": "SELECT COUNT(*) FROM market_path",
        "latest_day": "SELECT MAX(day) FROM path_days WHERE state = 'COMPLETE'",
    })
    counts["fundamentals"] = count(FUND_DB, {
        "observations": "SELECT COUNT(*) FROM series_obs",
        "revisions": "SELECT COUNT(*) FROM series_revisions",
        "calendar_events": "SELECT COUNT(*) FROM calendar_events",
        "latest_available": "SELECT MAX(available_at) FROM series_obs",
    })
    return counts


def commit_manifest(run_id: str, t0: datetime, artifacts: dict[str, str], new_prediction_ids: list[str],
                    extra: dict) -> dict:
    return {
        "run_id": run_id,
        "t0": t0.isoformat(),
        "committed_at": datetime.now(UTC).isoformat(),
        "artifacts": artifacts,
        "stores": store_counts(),
        "new_prediction_ids": new_prediction_ids,
        **extra,
    }


def read_back(run_dir: Path, manifest: dict) -> dict:
    """Re-open everything and verify (module 104)."""
    problems = []

    for name, digest in manifest["artifacts"].items():
        path = run_dir / name

        if not path.exists():
            problems.append(f"artifact missing: {name}")
            continue

        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"artifact hash mismatch: {name}")

    now_counts = store_counts()

    for store, values in manifest["stores"].items():
        for key, value in values.items():
            current = now_counts.get(store, {}).get(key)

            if isinstance(value, int) and (current is None or current < value):
                problems.append(f"{store}.{key}: read back {current}, expected >= {value}")

    if manifest["new_prediction_ids"]:
        connection = sqlite3.connect(DB_PATH)

        try:
            placeholders = ",".join("?" for _ in manifest["new_prediction_ids"])
            found = connection.execute(
                f"SELECT COUNT(*) FROM predictions WHERE prediction_id IN ({placeholders}) AND run_id = ?",
                (*manifest["new_prediction_ids"], manifest["run_id"]),
            ).fetchone()[0]
        finally:
            connection.close()

        if found != len(manifest["new_prediction_ids"]):
            problems.append(f"locked predictions read back {found}/{len(manifest['new_prediction_ids'])}")

    connection = sqlite3.connect(DB_PATH)

    try:
        row = connection.execute("SELECT run_id FROM runs WHERE run_id = ?", (manifest["run_id"],)).fetchone()
    finally:
        connection.close()

    if row is None:
        problems.append("run row missing")

    return {"status": "PASS" if not problems else "FAIL", "problems": problems, "checked_at": datetime.now(UTC).isoformat()}
