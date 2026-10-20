"""FXBOT - jediny prikaz: izolovane testy.

    python fxbot.py test             # vsechny testy v docasne slozce; nikdy nesahaji na data/
    python fxbot.py test h1 f3       # jen testy, v jejichz nazvu je jeden z retezcu

Zivy system (denni aktualizace, uceni, signaly) se spousti skripty ve scripts/ - viz docs/RUTINY.md. Puvodni
prikazy V7.8.0 (run, update, history, backtest, review, journal, ...) jsou v archive/v7.8.0/fxbot.py, vysvetleni a
navod na obnovu v archive/README.md.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


def main(argv: list[str]) -> int:
    if argv[:1] != ["test"]:
        print(__doc__)
        return 2
    import run_tests

    return run_tests.main(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
