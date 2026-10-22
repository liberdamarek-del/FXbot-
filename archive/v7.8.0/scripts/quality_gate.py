import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_check(name: str, command: list[str]) -> bool:
    print("=" * 70)
    print(f"QUALITY CHECK: {name}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0:
        print(f"[PASS] {name}")
        return True

    print(f"[FAIL] {name}")
    return False


def main() -> int:
    checks = []

    python_files = [
        "src/config.py",
        "src/database.py",
        "src/models.py",
        "src/validator.py",
        "src/storage.py",
        "src/logger.py",
        "src/twelve_data.py",
        "src/bar_policy.py",
        "src/market_session.py",
        "src/gap_detector.py",
        "src/backfill.py",
        "src/backfill_missing_gaps.py",
        "src/collector.py",
        "src/collector_service.py",
        "scripts/verify_all.py",
        "scripts/health_check.py",
    ]

    syntax_command = [
        sys.executable,
        "-m",
        "py_compile",
        *python_files,
    ]

    checks.append(
        run_check(
            "PYTHON SYNTAX",
            syntax_command,
        )
    )

    checks.append(
        run_check(
            "REGRESSION TESTS",
            [
                sys.executable,
                "scripts/verify_all.py",
            ],
        )
    )

    checks.append(
        run_check(
            "SYSTEM HEALTH",
            [
                sys.executable,
                "scripts/health_check.py",
            ],
        )
    )

    print()
    print("=" * 70)
    print("QUALITY GATE SUMMARY")
    print("=" * 70)

    passed = sum(checks)
    failed = len(checks) - passed

    print(f"CHECKS:  {len(checks)}")
    print(f"PASS:    {passed}")
    print(f"FAIL:    {failed}")

    if failed == 0:
        print("RESULT:  PASS")
        return 0

    print("RESULT:  BLOCKED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
