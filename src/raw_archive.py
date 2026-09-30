"""Raw payload archive shared by all stores (specification modules 120, 124).

The exact bytes of every source response are kept together with their
SHA-256, endpoint, retrieval time and parser version, so that a run can be
replayed from the same inputs. `fetch_log` records every acquisition
attempt, successful or not.

The functions take an open sqlite3 connection, so the same layout is used
in the market path archive and in the fundamentals database.
"""

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

RAW_PAYLOADS_DDL = """
    CREATE TABLE IF NOT EXISTS raw_payloads (
        payload_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        instrument TEXT,
        side TEXT,
        period_start INTEGER,
        period_end INTEGER,
        retrieved_at TEXT NOT NULL,
        http_status INTEGER,
        sha256 TEXT NOT NULL,
        size INTEGER NOT NULL,
        parser_version TEXT NOT NULL,
        content BLOB NOT NULL,
        UNIQUE (source_id, endpoint, sha256)
    )
"""

FETCH_LOG_DDL = """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempted_at TEXT NOT NULL,
        source_id TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        instrument TEXT,
        result TEXT NOT NULL,
        http_status INTEGER,
        detail TEXT
    )
"""


@dataclass(frozen=True)
class StoredPayload:
    payload_id: int
    sha256: str
    new: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_payload(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    kind: str,
    endpoint: str,
    instrument: str | None,
    side: str | None,
    period_start: int | None,
    period_end: int | None,
    http_status: int | None,
    content: bytes,
    parser_version: str,
    retrieved_at: str | None = None,
) -> StoredPayload:
    """Store the exact payload (idempotent: same endpoint + same bytes = same row)."""
    digest = sha256_hex(content)
    row = connection.execute(
        "SELECT payload_id FROM raw_payloads "
        "WHERE source_id = ? AND endpoint = ? AND sha256 = ?",
        (source_id, endpoint, digest),
    ).fetchone()

    if row is not None:
        return StoredPayload(int(row[0]), digest, False)

    cursor = connection.execute(
        """
        INSERT INTO raw_payloads (
            source_id, kind, endpoint, instrument, side, period_start,
            period_end, retrieved_at, http_status, sha256, size,
            parser_version, content
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id, kind, endpoint, instrument, side, period_start,
            period_end, retrieved_at or now_iso(), http_status, digest,
            len(content), parser_version, sqlite3.Binary(content),
        ),
    )
    connection.commit()
    return StoredPayload(int(cursor.lastrowid), digest, True)


def load_payload(connection: sqlite3.Connection, payload_id: int) -> tuple[bytes, str]:
    """Return (content, sha256) and verify the hash (module 124 replay)."""
    row = connection.execute(
        "SELECT content, sha256 FROM raw_payloads WHERE payload_id = ?",
        (payload_id,),
    ).fetchone()

    if row is None:
        raise KeyError(f"payload {payload_id} not found")

    content = bytes(row[0])

    if sha256_hex(content) != row[1]:
        raise RuntimeError(
            f"payload {payload_id} hash mismatch - REPRODUCIBILITY INCOMPLETE"
        )

    return content, row[1]


def log_fetch(
    connection: sqlite3.Connection,
    source_id: str,
    endpoint: str,
    result: str,
    instrument: str | None = None,
    http_status: int | None = None,
    detail: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO fetch_log (
            attempted_at, source_id, endpoint, instrument, result,
            http_status, detail
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (now_iso(), source_id, endpoint, instrument, result, http_status,
         (detail or "")[:500]),
    )
    connection.commit()
