"""Store your Twelve Data API key safely and test it.

    python scripts/set_api_key.py

The key is written to the file `.env` in the project folder (created if
missing, other lines are kept) with owner-only permissions. The key is never
printed in full and never written to logs or the database.

Free personal key: register at https://twelvedata.com/register (no credit
card), the key is shown in the dashboard under "API keys".
"""

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ENV_NAME = "TWELVE_DATA_API_KEY"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{16,64}$")


def validate_key(key: str) -> str:
    key = key.strip().strip("'\"")

    if key.lower() == "demo":
        raise ValueError("'demo' is the shared demo key, not a personal key")

    if not KEY_PATTERN.match(key):
        raise ValueError(
            "the key should be 16-64 letters/digits without spaces "
            "(copy only the key itself)"
        )

    return key


def mask(key: str) -> str:
    return f"{key[:4]}{'*' * max(0, len(key) - 8)}{key[-4:]}"


def write_key(env_path: Path, key: str) -> bool:
    """Set TWELVE_DATA_API_KEY in the env file. Returns True if it replaced
    an existing value. All other lines are preserved unchanged."""
    lines = []

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    replaced = False
    result = []

    for line in lines:
        if re.match(rf"^\s*{ENV_NAME}\s*=", line):
            if not replaced:
                result.append(f"{ENV_NAME}={key}")
                replaced = True
            # drop duplicate definitions
        else:
            result.append(line)

    if not replaced:
        result.append(f"{ENV_NAME}={key}")

    temporary = env_path.with_name(env_path.name + ".tmp")
    temporary.write_text("\n".join(result) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, env_path)

    return replaced


def main(argv: list[str], feed_factory=None, env_path: Path | None = None) -> int:
    env_path = env_path or PROJECT_ROOT / ".env"

    raw = argv[0] if argv else input("Vlozte API klic a stisknete Enter: ")

    try:
        key = validate_key(raw)
    except ValueError as exc:
        print(f"CHYBA: {exc}")
        return 1

    replaced = write_key(env_path, key)
    print(
        ("Klic prepsan" if replaced else "Klic ulozen")
        + f" v {env_path.name}: {mask(key)}"
    )

    # Test the key with ONE request (1 API credit).
    from src.twelve_data import TwelveDataFeed

    feed = feed_factory(key) if feed_factory else TwelveDataFeed(api_key=key, timeout=15)

    try:
        bar = feed.fetch_latest_bar("EUR/USD", "1min")
    except Exception as exc:
        message = str(exc).replace(key, "***")
        print(f"TEST KLICE SELHAL: {message[:200]}")
        print("Klic je ulozen. Zkontrolujte ho v dashboardu a zkuste to znovu.")
        return 1

    print(f"TEST KLICE OK (EUR/USD, svicka {bar.bar_time:%Y-%m-%d %H:%M} UTC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
