"""Isolated test runner for FXBOT.

Every run:
  1. creates a NEW temporary data directory (DATA_DIR), never the production
     one,
  2. seeds it from the frozen fixture in tests/fixtures,
  3. compiles all sources (syntax check),
  4. runs the test scripts in canonical order against that temporary
     database (some tests build on records of earlier tests, e.g. M3.11
     reads the run stored by M3.10),
  5. deletes the temporary directory (use --keep to inspect it).

Because the database is created fresh for each run, tests can be repeated
any number of times without UNIQUE-key or ordering side effects, and no
test record (TEST/*, M3.*, M4.*) is ever written to the production database.

Usage:
    python scripts/run_tests.py            # everything
    python scripts/run_tests.py m48 a2     # only tests whose name contains
                                           # one of the given fragments
    python scripts/run_tests.py --keep
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DATA_DIR = (PROJECT_ROOT / "data").resolve()

# seconds one test may take (slow phones need room); override with
# FXBOT_TEST_TIMEOUT
TEST_TIMEOUT = int(os.getenv("FXBOT_TEST_TIMEOUT", "900"))

# Canonical order. Block A tests come first (they are self-contained).
TESTS = [
    "test_a1_market_session.py",
    "test_a2_schema_migration.py",
    "test_a3_paper_ambiguous.py",
    "test_b1_rate_limiter.py",
    "test_b2_twelve_client.py",
    "test_b3_data_state.py",
    "test_b4_data_update.py",
    "test_b5_prediction_ledger.py",
    "test_b6_scripts.py",
    "test_b7_update_service.py",
    "test_b8_resample.py",
    "test_b9_history_settle.py",
    "test_b10_batch_storage.py",
    "test_b11_offsession.py",
    "test_c1_indicators.py",
    "test_c2_analysis.py",
    "test_d1_resolver.py",
    "test_e1_path_archive.py",
    "test_e2_fundamentals.py",
    "test_e3_engine.py",
    "test_e4_v78_pretests.py",
    "test_e5_run.py",
    "test_e6_stats_registry.py",
    "test_e7_upgrade.py",
    "test_m39.py",
    "test_m310.py",
    "test_m311.py",
    "test_m312.py",
    "test_m313.py",
    "test_m314.py",
    "test_m315.py",
    "test_m41.py",
    "test_m42.py",
    "test_m43.py",
    "test_m44.py",
    "test_m45.py",
    "test_m46.py",
    "test_m47.py",
    "test_m48.py",
    "test_m49.py",
    "test_m410.py",
    "test_m411.py",
    "test_m412.py",
    "test_m413.py",
    "test_m414.py",
    "scripts/test_m415_real_data.py",
    "scripts/test_m51.py",
    "scripts/verify_all.py",
]


def syntax_check() -> bool:
    ok = True
    files = sorted(
        list((PROJECT_ROOT / "src").rglob("*.py"))
        + list((PROJECT_ROOT / "scripts").glob("*.py"))
        + [PROJECT_ROOT / "fxbot.py"]
        + list(PROJECT_ROOT.glob("test_*.py"))
        + list((PROJECT_ROOT / "tests").glob("*.py"))
    )

    for path in files:
        try:
            # compile() only checks syntax; it writes no .pyc files.
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            ok = False
            print(f"[FAIL] SYNTAX {path.relative_to(PROJECT_ROOT)}: {exc}")

    print(f"[{'PASS' if ok else 'FAIL'}] SYNTAX ({len(files)} files)")
    return ok


def main(argv: list[str]) -> int:
    keep = "--keep" in argv
    filters = [a for a in argv if not a.startswith("--")]

    tests = [
        t for t in TESTS
        if not filters or any(f in t for f in filters)
    ]

    if not tests:
        print("No test matches the given filter.")
        return 2

    temp_dir = Path(tempfile.mkdtemp(prefix="fxbot_test_")).resolve()

    if temp_dir == PRODUCTION_DATA_DIR or PRODUCTION_DATA_DIR in temp_dir.parents:
        print("REFUSING to run: test directory overlaps production data.")
        return 2

    env = dict(os.environ)

    # Tests must behave the same on every device: drop personal settings
    # from the shell and never read the project's .env (it may contain a
    # real API key). Tests that need a value set it themselves.
    for name in list(env):
        if name.startswith((
            "COLLECTOR_", "HISTORY_", "UPDATE_", "UPDATER_", "BAR_SETTLE",
            "DATA_STATE_", "API_BUDGET", "TWELVE_DATA_", "DERIVED_",
        )):
            del env[name]

    env["FXBOT_IGNORE_DOTENV"] = "1"
    env["TWELVE_DATA_API_KEY"] = "demo"
    env["DATA_DIR"] = str(temp_dir)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print("=" * 70)
    print("FXBOT ISOLATED TEST RUN")
    print("=" * 70)
    print(f"TEST DATA DIR: {temp_dir}")
    print(f"PRODUCTION DATA DIR (untouched): {PRODUCTION_DATA_DIR}")

    failures = 0

    try:
        if not syntax_check():
            failures += 1

        seed = subprocess.run(
            [
                sys.executable,
                "-c",
                "from tests.seed import seed_database; "
                "print('SEEDED BARS:', seed_database())",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        print(seed.stdout.strip() or seed.stderr.strip())

        if seed.returncode != 0:
            print("[FAIL] SEED")
            return 1

        started_all = time.monotonic()

        for test in tests:
            started = time.monotonic()

            try:
                result = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / test)],
                    cwd=PROJECT_ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=TEST_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                failures += 1
                print(f"[FAIL] {test} (timeout after {TEST_TIMEOUT} s)")
                continue

            elapsed = time.monotonic() - started

            if result.returncode == 0:
                print(f"[PASS] {test} ({elapsed:.0f} s)")
            else:
                failures += 1
                print(f"[FAIL] {test} (rc={result.returncode}, {elapsed:.0f} s)")
                tail = (result.stdout + result.stderr).strip().splitlines()
                for line in tail[-8:]:
                    print(f"       {line}")

        print(f"TOTAL TIME: {time.monotonic() - started_all:.0f} s")

    finally:
        if keep:
            print(f"KEPT: {temp_dir}")
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)

    print("=" * 70)
    print(f"TESTS: {len(tests)} | FAILURES: {failures}")
    print("RESULT:", "PASS" if failures == 0 else "FAIL")
    print("=" * 70)

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
