"""Console and rotating-file logging for the package."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "gmail_organizer"
_HANDLER_MARK = "_gmail_organizer_handler"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _resolve_level(name: str) -> int:
    level = getattr(logging, name.upper(), None)
    return level if isinstance(level, int) else logging.INFO


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            logger.removeHandler(handler)
            handler.close()


def configure_logging(
    *,
    level: str = "INFO",
    log_dir: Path | str = "logs",
    verbose: bool = False,
) -> logging.Logger:
    """Configure the package logger. Safe to call more than once."""
    logger = logging.getLogger(LOGGER_NAME)
    _clear_handlers(logger)
    logger.propagate = False

    resolved_level = logging.DEBUG if verbose else _resolve_level(level)
    logger.setLevel(resolved_level)
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(resolved_level)
    console.setFormatter(formatter)
    setattr(console, _HANDLER_MARK, True)
    logger.addHandler(console)

    try:
        log_path = Path(log_dir) / "organizer.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not open log file in %s: %s", log_dir, exc)
    else:
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        setattr(file_handler, _HANDLER_MARK, True)
        logger.addHandler(file_handler)

    return logger


def reset_logging() -> None:
    """Remove handlers created by configure_logging (used by tests)."""
    logger = logging.getLogger(LOGGER_NAME)
    _clear_handlers(logger)
    logger.propagate = True
    logger.setLevel(logging.NOTSET)
