from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import Settings


_FRAUD_LOGGING_CONFIGURED = False


class UTCFormatter(logging.Formatter):
    converter = __import__("time").gmtime


def configure_logging(settings: Settings) -> None:
    global _FRAUD_LOGGING_CONFIGURED

    if _FRAUD_LOGGING_CONFIGURED:
        return

    log_dir = Path(settings.log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / settings.log_file_name

    formatter = UTCFormatter(
        fmt=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    root_logger.setLevel(
        getattr(
            logging,
            settings.log_level.upper(),
            logging.INFO,
        )
    )

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _FRAUD_LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)