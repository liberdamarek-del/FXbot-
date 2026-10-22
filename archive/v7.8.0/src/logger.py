import logging
import time
from pathlib import Path

from src.config import DATA_DIR, LOG_LEVEL


LOG_FILE = DATA_DIR / "fxbot.log"


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def get_logger(name: str = "fxbot") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(
        getattr(
            logging,
            LOG_LEVEL.upper(),
            logging.INFO,
        )
    )

    formatter = UTCFormatter(
        "%(asctime)s UTC | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
