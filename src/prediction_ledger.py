"""Prediction ledger (foundation).

Implements the ledger rules of the model specification (modules 4, 60, 61,
138):

- a prediction is LOCKED when written: its fields can never be changed or
  deleted (enforced by SQLite triggers, not only by convention),
- later knowledge is appended in separate tables: state transitions
  (`prediction_states`) and outcomes (`prediction_outcomes`),
- a changed thesis is a NEW prediction with a new ID,
- a prediction can only be created from CURRENT input data: an unverified,
  stale or closed-market price never becomes a prediction,
- BUY/SELL levels must be consistent (stop-loss on the losing side, take
  profits on the winning side).

This module stores and protects predictions. It does not create them; the
analytic engine (V7.x adapter) is a later block.
"""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from src.database import get_connection

DECISIONS = (
    "BUY NOW",
    "SELL NOW",
    "WAIT FOR BUY",
    "WAIT FOR SELL",
    "NO TRADE",
)

STATES = (
    "NEW",
    "WAITING",
    "CONFIRMED",
    "TRIGGERED",
    "ACTIVE",
    "WEAKENED",
    "INVALIDATED",
    "EXPIRED",
    "RESOLVED",
    "NOT_ACTIVATED",
)

OUTCOME_STATES = (
    "TP1_BEFORE_SL",
    "SL_BEFORE_TP1",
    "EXPIRED",
    "NOT_ACTIVATED",
    "SEQUENCE_UNKNOWN",
    "PARTIAL",
    "UNRESOLVED",
)

CONFIDENCE = ("A", "B", "C")
DATA_QUALITY = ("A", "B", "C", "D")

_DECIMAL_FIELDS = (
    "reference_price",
    "bid",
    "ask",
    "entry",
    "entry_zone_low",
    "entry_zone_high",
    "trigger_price",
    "stop_loss",
    "tp1",
    "tp2",
    "tp3",
)


class PredictionRejected(ValueError):
    """The prediction violates a ledger rule and was NOT stored."""


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id TEXT NOT NULL UNIQUE,
        run_id TEXT,
        model_version TEXT NOT NULL,
        t0 TEXT NOT NULL,
        locked_at TEXT NOT NULL,
        instrument TEXT NOT NULL,
        decision TEXT NOT NULL,
        direction TEXT NOT NULL,
        reference_price TEXT NOT NULL,
        price_source TEXT NOT NULL,
        price_timestamp TEXT NOT NULL,
        data_state TEXT NOT NULL,
        data_quality TEXT NOT NULL,
        bid TEXT,
        ask TEXT,
        forecast_mode TEXT,
        setup_type TEXT,
        entry TEXT,
        entry_zone_low TEXT,
        entry_zone_high TEXT,
        trigger_price TEXT,
        stop_loss TEXT,
        tp1 TEXT,
        tp2 TEXT,
        tp3 TEXT,
        primary_horizon TEXT,
        expected_move TEXT,
        catalyst TEXT,
        thesis TEXT,
        counterforce TEXT,
        invalidation TEXT,
        regime TEXT,
        confidence TEXT,
        event_cluster TEXT,
        reasons TEXT,
        inputs TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_predictions_lookup
    ON predictions(instrument, t0)
    """,
    """
    CREATE TABLE IF NOT EXISTS prediction_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id TEXT NOT NULL,
        state TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        reason TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_prediction_states_lookup
    ON prediction_states(prediction_id, id)
    """,
    """
    CREATE TABLE IF NOT EXISTS prediction_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        outcome_state TEXT NOT NULL,
        path_coverage TEXT,
        r_multiple TEXT,
        mfe TEXT,
        mae TEXT,
        error_family TEXT,
        root_cause TEXT,
        notes TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_prediction_outcomes_lookup
    ON prediction_outcomes(prediction_id, id)
    """,
)


def _immutability_triggers() -> list[str]:
    statements = []

    for table, message in (
        ("predictions", "prediction ledger is immutable"),
        ("prediction_states", "prediction state history is append-only"),
        ("prediction_outcomes", "prediction outcome history is append-only"),
    ):
        for action in ("UPDATE", "DELETE"):
            statements.append(
                f"""
                CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}
                BEFORE {action} ON {table}
                BEGIN
                    SELECT RAISE(ABORT, '{message}');
                END
                """
            )

    return statements


def initialize_ledger() -> None:
    with get_connection() as connection:
        for statement in _SCHEMA:
            connection.execute(statement)

        for statement in _immutability_triggers():
            connection.execute(statement)

        connection.commit()


# ----------------------------------------------------------------------
# validation
# ----------------------------------------------------------------------

def _decimal(name: str, value) -> Decimal | None:
    if value is None:
        return None

    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise PredictionRejected(f"{name} is not a number: {value!r}") from None

    if not number.is_finite() or number <= 0:
        raise PredictionRejected(f"{name} must be a positive number")

    return number


def _iso(name: str, value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PredictionRejected(f"{name} must be a timezone-aware datetime")

    return value.astimezone(timezone.utc).isoformat()


def _direction(decision: str) -> str:
    if decision in ("BUY NOW", "WAIT FOR BUY"):
        return "BUY"

    if decision in ("SELL NOW", "WAIT FOR SELL"):
        return "SELL"

    return "NONE"


def _validate_levels(direction: str, numbers: dict[str, Decimal | None]) -> None:
    reference = (
        numbers["entry"]
        or numbers["trigger_price"]
        or numbers["reference_price"]
    )

    stop = numbers["stop_loss"]
    targets = [numbers[k] for k in ("tp1", "tp2", "tp3") if numbers[k]]

    if stop is None or numbers["tp1"] is None:
        raise PredictionRejected("stop_loss and tp1 are required for a trade")

    if direction == "BUY":
        if not stop < reference:
            raise PredictionRejected("BUY stop_loss must be below entry")

        if any(target <= reference for target in targets):
            raise PredictionRejected("BUY take profits must be above entry")

        if targets != sorted(targets):
            raise PredictionRejected("BUY take profits must be ascending")

    else:
        if not stop > reference:
            raise PredictionRejected("SELL stop_loss must be above entry")

        if any(target >= reference for target in targets):
            raise PredictionRejected("SELL take profits must be below entry")

        if targets != sorted(targets, reverse=True):
            raise PredictionRejected("SELL take profits must be descending")

    low, high = numbers["entry_zone_low"], numbers["entry_zone_high"]

    if (low is None) != (high is None):
        raise PredictionRejected("entry zone needs both low and high")

    if low is not None and low > high:
        raise PredictionRejected("entry_zone_low must not exceed entry_zone_high")


def lock_prediction(
    *,
    model_version: str,
    t0: datetime,
    instrument: str,
    decision: str,
    reference_price,
    price_source: str,
    price_timestamp: datetime,
    data_state: str,
    data_quality: str,
    run_id: str | None = None,
    bid=None,
    ask=None,
    forecast_mode: str | None = None,
    setup_type: str | None = None,
    entry=None,
    entry_zone_low=None,
    entry_zone_high=None,
    trigger_price=None,
    stop_loss=None,
    tp1=None,
    tp2=None,
    tp3=None,
    primary_horizon: str | None = None,
    expected_move: str | None = None,
    catalyst: str | None = None,
    thesis: str | None = None,
    counterforce: str | None = None,
    invalidation: str | None = None,
    regime: str | None = None,
    confidence: str | None = None,
    event_cluster: str | None = None,
    reasons: list | None = None,
    inputs: dict | None = None,
    now: datetime | None = None,
) -> str:
    """Validate and permanently store a prediction. Returns its ID.

    Raises PredictionRejected (nothing stored) when a rule is violated.
    """
    if not model_version or not model_version.strip():
        raise PredictionRejected("model_version is required")

    if not instrument or not instrument.strip():
        raise PredictionRejected("instrument is required")

    if decision not in DECISIONS:
        raise PredictionRejected(f"decision must be one of {DECISIONS}")

    if data_quality not in DATA_QUALITY:
        raise PredictionRejected(f"data_quality must be one of {DATA_QUALITY}")

    if confidence is not None and confidence not in CONFIDENCE:
        raise PredictionRejected(f"confidence must be one of {CONFIDENCE}")

    if not price_source or not price_source.strip():
        raise PredictionRejected("price_source is required")

    # A prediction may only rest on verified, current input data.
    if data_state != "CURRENT":
        raise PredictionRejected(
            f"input data state is {data_state}; only CURRENT data can "
            f"produce a prediction"
        )

    t0_text = _iso("t0", t0)
    price_time_text = _iso("price_timestamp", price_timestamp)

    if now is None:
        now = datetime.now(timezone.utc)

    if t0 > now:
        raise PredictionRejected("t0 lies in the future")

    if price_timestamp > t0:
        raise PredictionRejected(
            "price_timestamp is after t0 (post-T0 information)"
        )

    values = {
        "reference_price": reference_price,
        "bid": bid,
        "ask": ask,
        "entry": entry,
        "entry_zone_low": entry_zone_low,
        "entry_zone_high": entry_zone_high,
        "trigger_price": trigger_price,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
    }
    numbers = {name: _decimal(name, value) for name, value in values.items()}

    if numbers["reference_price"] is None:
        raise PredictionRejected("reference_price is required")

    if numbers["bid"] is not None and numbers["ask"] is not None:
        if numbers["bid"] > numbers["ask"]:
            raise PredictionRejected("bid must not exceed ask")

    direction = _direction(decision)

    if direction != "NONE":
        for name, text in (
            ("thesis", thesis),
            ("counterforce", counterforce),
            ("invalidation", invalidation),
        ):
            if not text or not text.strip():
                raise PredictionRejected(f"{name} is required for a trade")

        _validate_levels(direction, numbers)

    def text(value):
        return None if value is None else str(value)

    initialize_ledger()

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        try:
            next_id = connection.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM predictions"
            ).fetchone()[0]

            prediction_id = (
                f"P-{t0.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{next_id:05d}"
            )

            connection.execute(
                """
                INSERT INTO predictions (
                    prediction_id, run_id, model_version, t0, locked_at,
                    instrument, decision, direction, reference_price,
                    price_source, price_timestamp, data_state, data_quality,
                    bid, ask, forecast_mode, setup_type, entry,
                    entry_zone_low, entry_zone_high, trigger_price,
                    stop_loss, tp1, tp2, tp3, primary_horizon,
                    expected_move, catalyst, thesis, counterforce,
                    invalidation, regime, confidence, event_cluster,
                    reasons, inputs
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction_id,
                    run_id,
                    model_version,
                    t0_text,
                    now.astimezone(timezone.utc).isoformat(),
                    instrument,
                    decision,
                    direction,
                    str(numbers["reference_price"]),
                    price_source,
                    price_time_text,
                    data_state,
                    data_quality,
                    text(numbers["bid"]),
                    text(numbers["ask"]),
                    forecast_mode,
                    setup_type,
                    text(numbers["entry"]),
                    text(numbers["entry_zone_low"]),
                    text(numbers["entry_zone_high"]),
                    text(numbers["trigger_price"]),
                    text(numbers["stop_loss"]),
                    text(numbers["tp1"]),
                    text(numbers["tp2"]),
                    text(numbers["tp3"]),
                    primary_horizon,
                    expected_move,
                    catalyst,
                    thesis,
                    counterforce,
                    invalidation,
                    regime,
                    confidence,
                    event_cluster,
                    json.dumps(reasons, ensure_ascii=False) if reasons is not None else None,
                    json.dumps(inputs, ensure_ascii=False, sort_keys=True) if inputs is not None else None,
                ),
            )

            connection.execute(
                """
                INSERT INTO prediction_states (prediction_id, state, changed_at, reason)
                VALUES (?, 'NEW', ?, 'locked')
                """,
                (prediction_id, now.astimezone(timezone.utc).isoformat()),
            )

            connection.execute("COMMIT")

        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    return prediction_id


# ----------------------------------------------------------------------
# append-only follow-up records
# ----------------------------------------------------------------------

def _require_prediction(connection, prediction_id: str) -> None:
    found = connection.execute(
        "SELECT 1 FROM predictions WHERE prediction_id = ?", (prediction_id,)
    ).fetchone()

    if found is None:
        raise PredictionRejected(f"unknown prediction: {prediction_id}")


def add_state(
    prediction_id: str,
    state: str,
    reason: str | None = None,
    changed_at: datetime | None = None,
) -> int:
    if state not in STATES:
        raise PredictionRejected(f"state must be one of {STATES}")

    if changed_at is None:
        changed_at = datetime.now(timezone.utc)

    initialize_ledger()

    with get_connection() as connection:
        _require_prediction(connection, prediction_id)

        cursor = connection.execute(
            """
            INSERT INTO prediction_states (prediction_id, state, changed_at, reason)
            VALUES (?, ?, ?, ?)
            """,
            (prediction_id, state, _iso("changed_at", changed_at), reason),
        )
        connection.commit()
        return int(cursor.lastrowid)


def record_outcome(
    prediction_id: str,
    outcome_state: str,
    path_coverage: str | None = None,
    r_multiple=None,
    mfe=None,
    mae=None,
    error_family: str | None = None,
    root_cause: str | None = None,
    notes: str | None = None,
    recorded_at: datetime | None = None,
) -> int:
    if outcome_state not in OUTCOME_STATES:
        raise PredictionRejected(f"outcome_state must be one of {OUTCOME_STATES}")

    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)

    def number(value):
        if value is None:
            return None
        try:
            return str(Decimal(str(value)))
        except InvalidOperation:
            raise PredictionRejected(f"not a number: {value!r}") from None

    initialize_ledger()

    with get_connection() as connection:
        _require_prediction(connection, prediction_id)

        cursor = connection.execute(
            """
            INSERT INTO prediction_outcomes (
                prediction_id, recorded_at, outcome_state, path_coverage,
                r_multiple, mfe, mae, error_family, root_cause, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prediction_id,
                _iso("recorded_at", recorded_at),
                outcome_state,
                path_coverage,
                number(r_multiple),
                number(mfe),
                number(mae),
                error_family,
                root_cause,
                notes,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


# ----------------------------------------------------------------------
# reading
# ----------------------------------------------------------------------

def get_prediction(prediction_id: str) -> dict | None:
    initialize_ledger()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,)
        ).fetchone()

        if row is None:
            return None

        result = dict(row)
        result["states"] = [
            dict(r)
            for r in connection.execute(
                "SELECT state, changed_at, reason FROM prediction_states "
                "WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            )
        ]
        result["outcomes"] = [
            dict(r)
            for r in connection.execute(
                "SELECT * FROM prediction_outcomes "
                "WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            )
        ]

    result["current_state"] = result["states"][-1]["state"]
    return result


def list_predictions(instrument: str | None = None, limit: int = 50) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be >= 1")

    initialize_ledger()

    query = "SELECT prediction_id FROM predictions"
    params: list = []

    if instrument is not None:
        query += " WHERE instrument = ?"
        params.append(instrument)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as connection:
        ids = [r["prediction_id"] for r in connection.execute(query, params)]

    return [get_prediction(prediction_id) for prediction_id in ids]


def ledger_digest() -> str:
    """SHA-256 over all locked predictions, in ID order (reproducibility)."""
    initialize_ledger()
    hasher = hashlib.sha256()

    with get_connection() as connection:
        for row in connection.execute("SELECT * FROM predictions ORDER BY id"):
            hasher.update(repr(tuple(row)).encode("utf-8"))
            hasher.update(b"\n")

    return hasher.hexdigest()
