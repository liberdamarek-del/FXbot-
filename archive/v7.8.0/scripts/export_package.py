"""Build the delivery packages.

    python scripts/export_package.py            # code only -> dist/FXBOT_V78.tar.gz
    python scripts/export_package.py --data     # + dist/FXBOT_V78_DATA.tar.gz (history archive, fundamentals)
    python scripts/export_package.py --data --with-fxcm   # incl. the FXCM 1-minute weeks (+~175 MB)
    python scripts/export_package.py --research # + dist/FXBOT_RESEARCH.tar.gz (41-pair hourly arrays,
                                                #   FRED series, learning state; ~110 MB) for the labs

The code package contains every tracked project file (no data/, no .env,
no caches). The data package contains consistent copies (SQLite backup
API, safe while a download is running) of data/market_path.sqlite3 and
data/fundamentals.sqlite3 - never the prediction ledger (data/fxbot.sqlite3),
which belongs to the installation that created it.

The FXCM 1-minute week files (second path source, only for outcome checks)
are left out by default - they are re-downloaded in a few minutes with
`python fxbot.py history --source fxcm --from 2023-08-01`.
"""

import argparse
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def code_package(target: Path) -> Path:
    files = subprocess.run(["git", "ls-files"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout.split()

    with tarfile.open(target, "w:gz") as archive:
        for name in files:
            archive.add(PROJECT_ROOT / name, arcname=name)

    return target


def data_package(target: Path, with_fxcm: bool = False) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(target, "w:gz") as archive:
            for name in ("market_path.sqlite3", "fundamentals.sqlite3"):
                source = PROJECT_ROOT / "data" / name

                if not source.exists():
                    continue

                copy = Path(tmp) / name
                src, dst = sqlite3.connect(source), sqlite3.connect(copy)
                try:
                    src.backup(dst)
                    assert dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

                    if name == "market_path.sqlite3" and not with_fxcm:
                        dst.execute("DELETE FROM path_days WHERE source_id = 'FXCM_M1'")
                        dst.execute("DELETE FROM raw_payloads WHERE source_id LIKE 'FXCM%'")
                        dst.commit()

                    dst.execute("VACUUM")
                finally:
                    dst.close()
                    src.close()
                archive.add(copy, arcname=f"data/{name}")

            # long daily history 2013-2023 for the self-learning challenger (CH-006)
            history = PROJECT_ROOT / "data" / "research" / "daily_history.pkl"
            if history.exists():
                archive.add(history, arcname="data/research/daily_history.pkl")

    return target


RESEARCH_PATTERNS = ("data/research/fxcm_h1/*.npz", "data/research/fxcm_h1/manifest.tsv",
                     "data/research/histdata_h1/*.npz", "data/research/histdata_h1/manifest.tsv",
                     "data/research/fred/*.csv", "data/research/profit2/champion*.json",
                     "data/research/daily_history.pkl", "data/research/signals.pkl")


def research_package(target: Path) -> Path:
    """Hourly arrays of the 41-pair research universe (the raw week / year
    files stay out: their sha256 are in the manifests and the download
    scripts fetch them again), FRED series and the self-learning state."""
    with tarfile.open(target, "w:gz") as archive:
        for pattern in RESEARCH_PATTERNS:
            for path in sorted(PROJECT_ROOT.glob(pattern)):
                archive.add(path, arcname=str(path.relative_to(PROJECT_ROOT)))
    return target


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build delivery packages")
    parser.add_argument("--data", action="store_true")
    parser.add_argument("--with-fxcm", action="store_true", help="include the FXCM 1-minute week files")
    parser.add_argument("--research", action="store_true", help="research arrays and learning state")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "dist"))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    code = code_package(out / "FXBOT_V78.tar.gz")
    print(f"kod: {code} ({code.stat().st_size / 1e6:.1f} MB)")

    if args.data:
        data = data_package(out / "FXBOT_V78_DATA.tar.gz", args.with_fxcm)
        print(f"data: {data} ({data.stat().st_size / 1e6:.1f} MB)")

    if args.research:
        research = research_package(out / "FXBOT_RESEARCH.tar.gz")
        print(f"vyzkum: {research} ({research.stat().st_size / 1e6:.1f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
