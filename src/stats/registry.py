"""Model registry, change log and promotion gate (modules 78-80, 95-98,
126, 127, 144).

- Every parameter set that ever produced predictions or backtests is a
  registry entry identified by its fingerprint.
- Status: CHAMPION (the active production set), CHALLENGER (tested, not
  promoted), CANDIDATE (proposed, not tested), REJECTED, RETIRED.
- The FIRST champion is the default parameter set with the explicit note
  that it has NO statistical evidence yet (the Word's V7.5.1 champion
  exists only as a document, not as code).
- A change is recorded BEFORE it is implemented (pre-change gate): old
  rule, proposed rule, root cause, affected modules, tests, failure modes,
  rollback target, proof class A/B/C and a decision SAFE TO TEST / HOLD /
  REJECT. History is append-only.
- Promotion (module 78, 127, 144) needs out-of-sample evidence: enough
  trades, better OOS expectancy with a 95 % interval above zero, no worse
  drawdown, no collapse in any regime, and it never happens automatically
  from one good run (no daily churn).
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from src.database import get_connection
from src.engine.params import ModelParams

UTC = timezone.utc
STATUSES = ("CHAMPION", "CHALLENGER", "CANDIDATE", "REJECTED", "RETIRED")
PROOF_CLASSES = {
    "A": "documented repair of a logical/data defect",
    "B": "structural improvement of observability/integrity",
    "C": "expected predictive improvement without sufficient OOS evidence",
}
MIN_OOS_TRADES = 100


def initialize_registry() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS model_registry (
                fingerprint TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                params TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                evidence TEXT,
                note TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS model_registry_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                reason TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS change_log (
                change_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                record TEXT NOT NULL
            )
            """
        )
        for table in ("model_registry_history", "change_log"):
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} "
                    f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
                )
        connection.commit()


def _history(connection, fingerprint: str, status: str, reason: str) -> None:
    connection.execute(
        "INSERT INTO model_registry_history (fingerprint, status, changed_at, reason) VALUES (?, ?, ?, ?)",
        (fingerprint, status, datetime.now(UTC).isoformat(), reason),
    )


def register(params: ModelParams, label: str, status: str, note: str = "", evidence: dict | None = None) -> str:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")

    initialize_registry()

    with get_connection() as connection:
        existing = connection.execute("SELECT status FROM model_registry WHERE fingerprint = ?",
                                      (params.fingerprint,)).fetchone()

        if existing is None:
            connection.execute(
                "INSERT INTO model_registry (fingerprint, label, params, status, created_at, evidence, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (params.fingerprint, label, json.dumps(params.to_dict(), sort_keys=True), status,
                 datetime.now(UTC).isoformat(), json.dumps(evidence or {}, default=str), note),
            )
            _history(connection, params.fingerprint, status, note or "registered")

        connection.commit()

    return params.fingerprint


def ensure_baseline(params: ModelParams) -> str:
    """The first champion: the default set, explicitly without evidence."""
    initialize_registry()

    with get_connection() as connection:
        champion = connection.execute("SELECT fingerprint FROM model_registry WHERE status = 'CHAMPION'").fetchone()

    if champion:
        return champion["fingerprint"]

    return register(params, "baseline-default", "CHAMPION",
                    "vychozi parametry; ZADNY statisticky dukaz (OOS) zatim neexistuje")


def champion() -> dict | None:
    initialize_registry()

    with get_connection() as connection:
        row = connection.execute("SELECT * FROM model_registry WHERE status = 'CHAMPION'").fetchone()

    return dict(row) if row else None


def entries() -> list[dict]:
    initialize_registry()

    with get_connection() as connection:
        return [dict(r) for r in connection.execute("SELECT * FROM model_registry ORDER BY created_at")]


def set_status(fingerprint: str, status: str, reason: str, evidence: dict | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")

    initialize_registry()

    with get_connection() as connection:
        if status == "CHAMPION":
            for row in connection.execute("SELECT fingerprint FROM model_registry WHERE status = 'CHAMPION'"):
                connection.execute("UPDATE model_registry SET status = 'RETIRED' WHERE fingerprint = ?",
                                   (row["fingerprint"],))
                _history(connection, row["fingerprint"], "RETIRED", f"replaced by {fingerprint}")

        connection.execute("UPDATE model_registry SET status = ?, evidence = COALESCE(?, evidence) WHERE fingerprint = ?",
                           (status, json.dumps(evidence, default=str) if evidence else None, fingerprint))
        _history(connection, fingerprint, status, reason)
        connection.commit()


@dataclass
class ChangeRecord:
    """Module 80/95/126 change record (all fields required before testing)."""
    change_id: str
    symptom: str
    root_cause: str
    old_rule: str
    new_rule: str
    affected_modules: list
    data_dependencies: str
    expected_benefit: str
    failure_modes: str
    negative_interactions: str
    tests: str
    rollback_target: str
    proof_class: str
    decision: str = "HOLD"            # SAFE TO TEST / HOLD / REJECT
    oos_result: str = ""
    robustness_result: str = ""
    benchmark_delta: str = ""
    status: str = "CANDIDATE"


def pre_change_gate(record: ChangeRecord) -> str:
    """SAFE TO TEST only when every field is filled and the proof class is
    known; predictive claims (class C) can be tested, never adopted."""
    required = ("symptom", "root_cause", "old_rule", "new_rule", "expected_benefit", "failure_modes",
                "tests", "rollback_target")

    if record.proof_class not in PROOF_CLASSES:
        return "REJECT"

    if any(not getattr(record, name).strip() for name in required) or not record.affected_modules:
        return "HOLD"

    return "SAFE TO TEST"


def log_change(record: ChangeRecord) -> str:
    initialize_registry()
    record.decision = pre_change_gate(record)

    with get_connection() as connection:
        connection.execute("INSERT INTO change_log (change_id, created_at, record) VALUES (?, ?, ?)",
                           (record.change_id, datetime.now(UTC).isoformat(), json.dumps(asdict(record))))
        connection.commit()

    return record.decision


def change_log() -> list[dict]:
    initialize_registry()

    with get_connection() as connection:
        return [{"change_id": r["change_id"], "created_at": r["created_at"], **json.loads(r["record"])}
                for r in connection.execute("SELECT * FROM change_log ORDER BY created_at")]


def promotion_gate(challenger_oos, champion_oos, difference: dict, regimes_challenger: dict | None = None,
                   regimes_champion: dict | None = None) -> tuple[str, list[str]]:
    """PROMOTE only with sufficient, significant, non-degrading OOS
    evidence; otherwise HOLD (stays CHALLENGER)."""
    reasons = []

    if len(challenger_oos.r_values) < MIN_OOS_TRADES:
        reasons.append(f"malo OOS obchodu ({len(challenger_oos.r_values)} < {MIN_OOS_TRADES})")

    if challenger_oos.effective_n and challenger_oos.effective_n < MIN_OOS_TRADES // 2:
        reasons.append(f"malo nezavislych situaci ({challenger_oos.effective_n})")

    if not difference.get("significant"):
        reasons.append("OOS rozdil expectancy neni statisticky vyznamny (95% IS obsahuje 0)")

    if (challenger_oos.max_drawdown_r or 0) < 1.2 * (champion_oos.max_drawdown_r or 0):
        reasons.append("drawdown challengera je o >20 % horsi")

    if challenger_oos.expectancy is not None and challenger_oos.expectancy <= 0:
        reasons.append("OOS expectancy challengera neni kladna")

    if regimes_challenger and regimes_champion:
        for key, summary in regimes_challenger.items():
            other = regimes_champion.get(key)
            if other and summary.expectancy is not None and other.expectancy is not None \
                    and len(summary.r_values) >= 20 and summary.expectancy < other.expectancy - 0.3:
                reasons.append(f"zhorseni v rezimu {key}")

    return ("PROMOTE" if not reasons else "HOLD"), reasons
