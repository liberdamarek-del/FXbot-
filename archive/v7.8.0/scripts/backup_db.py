"""Create or list verified backups of the FXBOT database.

    python scripts/backup_db.py                # backup, reason "manual"
    python scripts/backup_db.py before_change  # backup with a reason tag
    python scripts/backup_db.py --list
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import BACKUP_DIR, DB_PATH, backup_database


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--list":
        files = sorted(BACKUP_DIR.glob("*.sqlite3")) if BACKUP_DIR.exists() else []

        if not files:
            print(f"No backups in {BACKUP_DIR}")
            return 0

        for path in files:
            print(f"{path.stat().st_size:>10}  {path.name}")

        return 0

    reason = argv[0] if argv else "manual"

    try:
        target = backup_database(reason=reason)
    except FileNotFoundError:
        print(f"Database not found: {DB_PATH}")
        return 1

    print(f"BACKUP OK (integrity verified): {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
