"""Official run state machine and execution trace (modules 102, 103, 105).

States: PLANNED -> RUNNING -> ANALYSIS_COMPLETE -> PERSISTENCE_PENDING ->
COMMITTED / COMMITTED_CONDITIONAL, or FAILED / REPRODUCIBILITY_INCOMPLETE.

Only a COMMITTED (or COMMITTED_CONDITIONAL) run is an official anchor: the
"previous official T0" is always the T0 of the newest committed run, so a
crashed or uncommitted run can never move the historical anchor.

Every state change is appended to run_state_history; the trace holds one
row per module 0..145 per run (PASS / CONDITIONAL / BLOCKED / N/A with a
reason) - no module is silently skipped.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from src.database import get_connection

UTC = timezone.utc
RUN_STATES = (
    "PLANNED", "RUNNING", "ANALYSIS_COMPLETE", "PERSISTENCE_PENDING",
    "COMMITTED", "COMMITTED_CONDITIONAL", "FAILED", "REPRODUCIBILITY_INCOMPLETE",
)
COMMITTED = ("COMMITTED", "COMMITTED_CONDITIONAL")
TRACE_STATUSES = ("PASS", "CONDITIONAL", "BLOCKED", "N/A")

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        model_version TEXT NOT NULL,
        implementation TEXT NOT NULL,
        manifest_fingerprint TEXT NOT NULL,
        params_fingerprint TEXT NOT NULL,
        t0 TEXT NOT NULL,
        state TEXT NOT NULL,
        previous_run_id TEXT,
        previous_t0 TEXT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        certificate TEXT,
        artifact_dir TEXT,
        summary TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_state_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        state TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_trace (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        module_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        reason TEXT NOT NULL,
        evidence_ref TEXT,
        recorded_at TEXT NOT NULL,
        UNIQUE (run_id, module_id)
    )
    """,
)


def initialize_runs() -> None:
    with get_connection() as connection:
        for statement in _SCHEMA:
            connection.execute(statement)

        for table in ("run_state_history", "run_trace"):
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}
                    BEFORE {action} ON {table}
                    BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END
                    """
                )

        connection.commit()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RunRecord:
    run_id: str
    t0: datetime
    state: str
    previous_run_id: str | None
    previous_t0: datetime | None


def last_committed() -> dict | None:
    initialize_runs()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM runs WHERE state IN (?, ?) ORDER BY t0 DESC LIMIT 1", COMMITTED
        ).fetchone()

    return dict(row) if row else None


def create_run(t0: datetime, manifest_fp: str, params_fp: str, model_version: str, implementation: str) -> RunRecord:
    initialize_runs()
    previous = last_committed()
    run_id = f"RUN-{t0.astimezone(UTC):%Y%m%dT%H%M%SZ}"
    previous_t0 = datetime.fromisoformat(previous["t0"]) if previous else None

    with get_connection() as connection:
        exists = connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone()

        if exists:
            run_id += f"-{int(t0.timestamp() * 1000) % 1000:03d}"

        connection.execute(
            "INSERT INTO runs (run_id, model_version, implementation, manifest_fingerprint, params_fingerprint, "
            "t0, state, previous_run_id, previous_t0, started_at) VALUES (?, ?, ?, ?, ?, ?, 'PLANNED', ?, ?, ?)",
            (run_id, model_version, implementation, manifest_fp, params_fp, t0.astimezone(UTC).isoformat(),
             previous["run_id"] if previous else None, previous["t0"] if previous else None, now_iso()),
        )
        connection.execute(
            "INSERT INTO run_state_history (run_id, state, changed_at, reason) VALUES (?, 'PLANNED', ?, 'created')",
            (run_id, now_iso()),
        )
        connection.commit()

    return RunRecord(run_id, t0, "PLANNED", previous["run_id"] if previous else None, previous_t0)


def set_state(run_id: str, state: str, reason: str = "", **fields) -> None:
    if state not in RUN_STATES:
        raise ValueError(f"unknown run state {state}")

    columns = {k: v for k, v in fields.items() if k in ("finished_at", "certificate", "artifact_dir", "summary")}

    with get_connection() as connection:
        sets = ", ".join(["state = ?"] + [f"{k} = ?" for k in columns])
        connection.execute(f"UPDATE runs SET {sets} WHERE run_id = ?",
                           (state, *[json.dumps(v) if isinstance(v, (dict, list)) else v for v in columns.values()], run_id))
        connection.execute("INSERT INTO run_state_history (run_id, state, changed_at, reason) VALUES (?, ?, ?, ?)",
                           (run_id, state, now_iso(), reason))
        connection.commit()


class Trace:
    """Collects the module statuses of one run; written once at the end."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.rows: dict[int, tuple[str, str, str | None]] = {}

    def set(self, module_id: int, status: str, reason: str, evidence_ref: str | None = None) -> None:
        if status not in TRACE_STATUSES:
            raise ValueError(f"trace status must be one of {TRACE_STATUSES}")

        self.rows[module_id] = (status, reason, evidence_ref)

    def many(self, module_ids, status: str, reason: str, evidence_ref: str | None = None) -> None:
        for module_id in module_ids:
            self.set(module_id, status, reason, evidence_ref)

    def fill_from_manifest(self, modules) -> None:
        """Modules the run did not set explicitly get their static status
        (NOT_AVAILABLE -> N/A with reason, PARTIAL -> CONDITIONAL, ...)."""
        for module in modules:
            if module.id in self.rows:
                continue

            if module.status == "NOT_AVAILABLE":
                self.set(module.id, "N/A", f"{module.note} (2026-09-30 capability check)")
            elif module.status == "SUPERSEDED":
                self.set(module.id, "N/A", module.note)
            elif module.status == "PARTIAL":
                self.set(module.id, "CONDITIONAL", module.note)
            else:
                self.set(module.id, "PASS", f"enforced by {module.ref}")

    def summary(self) -> dict[str, int]:
        counts = {s: 0 for s in TRACE_STATUSES}

        for status, _, _ in self.rows.values():
            counts[status] += 1

        return counts

    def write(self) -> None:
        with get_connection() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO run_trace (run_id, module_id, status, reason, evidence_ref, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(self.run_id, module_id, status, reason, ref, now_iso())
                 for module_id, (status, reason, ref) in sorted(self.rows.items())],
            )
            connection.commit()
