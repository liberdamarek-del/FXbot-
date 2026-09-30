from pathlib import Path
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# The test runner sets FXBOT_IGNORE_DOTENV so that tests never read the
# user's personal settings (API key, instrument list, ...).
if not os.getenv("FXBOT_IGNORE_DOTENV"):
    load_dotenv(PROJECT_ROOT / ".env")

APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")

DATA_DIR.mkdir(parents=True, exist_ok=True)
