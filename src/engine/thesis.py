"""Persistent thesis state per pair (modules 138, 139, 140, 141).

A thesis is born when a prediction is locked. Later runs APPEND state
transitions; the locked prediction itself never changes (module 138).

States:
    NEW          just locked
    WAITING      WAIT decision, entry not reached yet
    ACTIVE       entry reached (triggered)
    WEAKENED     the new analysis no longer supports the direction, or an
                 opposite setup appeared - but nothing invalidated the thesis
    CONFIRMED    TP1 reached
    INVALIDATED  SL reached / invalidation condition met / hard regime break
    EXPIRED      horizon over

No-instant-flip (module 139): while a thesis is open (NEW / WAITING /
ACTIVE / WEAKENED) an opposite trade on the same pair is refused unless
(a) the thesis was invalidated first, or (b) a hard regime break
invalidates it AND the opposite setup fully qualifies on its own
(confidence A/B, all NOW gates passed). Otherwise the answer is KEEP /
WEAKEN / WAIT, never a reversal.

Hysteresis (module 140): a same-direction candidate while a thesis is open
does not create a new prediction ("teze trva"); ranking changes (Top-1 to
Top-3 or out of Top-3) never erase a thesis.

The book works on a storage backend: SQLite for the live run
(SqliteThesisStore), memory for the backtest (MemoryThesisStore). The
rules are the same code (module 74).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.database import get_connection
from src.engine.decision import Candidate

OPEN_STATES = ("NEW", "WAITING", "ACTIVE", "WEAKENED")
CLOSED_STATES = ("CONFIRMED", "INVALIDATED", "EXPIRED")
STATES = OPEN_STATES + CLOSED_STATES
UTC = timezone.utc


@dataclass
class Thesis:
    symbol: str
    prediction_id: str
    direction: str
    decision: str
    entry: float
    stop: float
    tp1: float
    t0: int
    expires_at: int
    state: str = "NEW"
    triggered_at: int | None = None
    last_change: int = 0
    last_reason: str = ""
    history: list = field(default_factory=list)       # (t, state, reason)

    @property
    def open(self) -> bool:
        return self.state in OPEN_STATES


class MemoryThesisStore:
    def __init__(self):
        self.theses: dict[str, Thesis] = {}
        self.archive: list[Thesis] = []

    def get(self, symbol: str) -> Thesis | None:
        return self.theses.get(symbol)

    def put(self, thesis: Thesis) -> None:
        old = self.theses.get(thesis.symbol)

        if old is not None and old.prediction_id != thesis.prediction_id:
            self.archive.append(old)

        self.theses[thesis.symbol] = thesis

    def transition(self, thesis: Thesis, state: str, t: int, reason: str) -> None:
        thesis.state, thesis.last_change, thesis.last_reason = state, t, reason
        thesis.history.append((t, state, reason))


class SqliteThesisStore:
    """thesis_state = latest state per pair; thesis_transitions = append-only."""

    def __init__(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS thesis_state (
                    symbol TEXT PRIMARY KEY,
                    prediction_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    t0 INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    triggered_at INTEGER,
                    last_change INTEGER NOT NULL,
                    last_reason TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS thesis_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    prediction_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    changed_at INTEGER NOT NULL,
                    reason TEXT,
                    run_id TEXT
                )
                """
            )
            for action in ("UPDATE", "DELETE"):
                connection.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS thesis_transitions_no_{action.lower()}
                    BEFORE {action} ON thesis_transitions
                    BEGIN SELECT RAISE(ABORT, 'thesis transitions are append-only'); END
                    """
                )
            connection.commit()
        self.run_id: str | None = None

    def get(self, symbol: str) -> Thesis | None:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM thesis_state WHERE symbol = ?", (symbol,)).fetchone()

        if row is None:
            return None

        return Thesis(row["symbol"], row["prediction_id"], row["direction"], row["decision"], row["entry"],
                      row["stop"], row["tp1"], row["t0"], row["expires_at"], row["state"],
                      row["triggered_at"], row["last_change"], row["last_reason"] or "")

    def put(self, thesis: Thesis) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO thesis_state (symbol, prediction_id, direction, decision, entry, stop, tp1, t0,
                                          expires_at, state, triggered_at, last_change, last_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol) DO UPDATE SET
                    prediction_id = excluded.prediction_id, direction = excluded.direction,
                    decision = excluded.decision, entry = excluded.entry, stop = excluded.stop,
                    tp1 = excluded.tp1, t0 = excluded.t0, expires_at = excluded.expires_at,
                    state = excluded.state, triggered_at = excluded.triggered_at,
                    last_change = excluded.last_change, last_reason = excluded.last_reason
                """,
                (thesis.symbol, thesis.prediction_id, thesis.direction, thesis.decision, thesis.entry,
                 thesis.stop, thesis.tp1, thesis.t0, thesis.expires_at, thesis.state, thesis.triggered_at,
                 thesis.last_change, thesis.last_reason),
            )
            connection.execute(
                "INSERT INTO thesis_transitions (symbol, prediction_id, state, changed_at, reason, run_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (thesis.symbol, thesis.prediction_id, thesis.state, thesis.last_change, thesis.last_reason,
                 self.run_id),
            )
            connection.commit()

    def transition(self, thesis: Thesis, state: str, t: int, reason: str) -> None:
        thesis.state, thesis.last_change, thesis.last_reason = state, t, reason
        thesis.history.append((t, state, reason))
        self.put(thesis)

    def all_open(self) -> list[Thesis]:
        with get_connection() as connection:
            symbols = [r["symbol"] for r in connection.execute(
                "SELECT symbol FROM thesis_state WHERE state IN (?, ?, ?, ?)", OPEN_STATES)]

        return [self.get(s) for s in symbols]


@dataclass
class FlipCheck:
    allowed: bool
    action: str          # NEW / KEEP / WEAKEN / FLIP_ALLOWED / BLOCKED_FLIP
    reason: str


class ThesisBook:
    def __init__(self, store):
        self.store = store

    def update_from_path(self, symbol: str, t: int, outcome: str | None, triggered_at: int | None,
                         prediction_id: str | None = None) -> Thesis | None:
        """Advance an open thesis from the resolved path (append-only).
        With prediction_id, only the thesis of exactly that prediction moves
        (another prediction on the same pair never closes it)."""
        thesis = self.store.get(symbol)

        if thesis is None or not thesis.open:
            return thesis

        if prediction_id is not None and thesis.prediction_id != prediction_id:
            return thesis

        if triggered_at and thesis.state in ("NEW", "WAITING", "WEAKENED") and thesis.triggered_at is None:
            thesis.triggered_at = triggered_at
            self.store.transition(thesis, "ACTIVE", triggered_at, "vstup aktivovan")

        if outcome == "TP1_BEFORE_SL":
            self.store.transition(thesis, "CONFIRMED", t, "TP1 dosazen")
        elif outcome == "SL_BEFORE_TP1":
            self.store.transition(thesis, "INVALIDATED", t, "SL dosazen")
        elif outcome in ("EXPIRED", "NOT_ACTIVATED"):
            self.store.transition(thesis, "EXPIRED", t, "horizont skoncil")
        elif outcome == "SEQUENCE_UNKNOWN":
            self.store.transition(thesis, "INVALIDATED", t, "SL i TP1 ve stejne svicce - teze uzavrena (poradi neznamo)")
        elif t >= thesis.expires_at:
            self.store.transition(thesis, "EXPIRED", t, "horizont skoncil")

        return thesis

    def check(self, candidate: Candidate, t: int, regime_break: bool) -> FlipCheck:
        """No-instant-flip and hysteresis for a new candidate (modules 139, 140)."""
        thesis = self.store.get(candidate.symbol)

        if thesis is None or not thesis.open:
            return FlipCheck(True, "NEW", "zadna otevrena teze")

        if not candidate.actionable:
            if candidate.thesis_direction != thesis.direction:
                if thesis.state != "WEAKENED":
                    self.store.transition(thesis, "WEAKENED", t, "nova analyza smer nepodporuje: " + candidate.reasons[0][:120])
                return FlipCheck(False, "WEAKEN", f"teze {thesis.direction} ({thesis.prediction_id}) oslabena, ne otocena")

            return FlipCheck(False, "KEEP", f"teze {thesis.direction} trva ({thesis.prediction_id})")

        if candidate.direction == thesis.direction:
            return FlipCheck(False, "KEEP", f"teze {thesis.direction} trva ({thesis.prediction_id}) - bez nove predikce")

        fully_qualified = candidate.is_now and candidate.confidence in ("A", "B")

        if regime_break and fully_qualified:
            self.store.transition(thesis, "INVALIDATED", t, "tvrdy zlom rezimu + plne kvalifikovany opacny setup")
            return FlipCheck(True, "FLIP_ALLOWED", f"predchozi teze {thesis.prediction_id} invalidovana zlomem rezimu")

        if thesis.state != "WEAKENED":
            self.store.transition(thesis, "WEAKENED", t, f"objevil se opacny setup {candidate.direction}")

        return FlipCheck(False, "BLOCKED_FLIP",
                         f"no-instant-flip: otevrena teze {thesis.direction} ({thesis.prediction_id}) nebyla invalidovana")

    def open_thesis(self, candidate: Candidate, prediction_id: str, t: int, horizon_hours: int) -> Thesis:
        thesis = Thesis(
            symbol=candidate.symbol, prediction_id=prediction_id, direction=candidate.direction,
            decision=candidate.decision, entry=candidate.entry, stop=candidate.stop, tp1=candidate.targets[0],
            t0=t, expires_at=t + horizon_hours * 3600,
            state="NEW", last_change=t, last_reason="zamceno",
        )
        thesis.history.append((t, "NEW", "zamceno"))
        self.store.put(thesis)

        if candidate.decision.startswith("WAIT"):
            self.store.transition(thesis, "WAITING", t, "cekani na vstup")

        return thesis
