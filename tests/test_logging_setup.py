from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

import pytest

from gmail_organizer.logging_setup import (
    configure_logging,
    reset_logging,
)


@pytest.fixture(autouse=True)
def clean_logger():
    reset_logging()
    yield
    reset_logging()


def test_creates_console_and_file_handlers(tmp_path) -> None:
    logger = configure_logging(level="INFO", log_dir=tmp_path)

    assert len(logger.handlers) == 2
    assert any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    assert logger.propagate is False
    assert logger.level == logging.INFO


def test_writes_to_rotating_file(tmp_path) -> None:
    logger = configure_logging(level="INFO", log_dir=tmp_path)

    logger.info("hello from test")
    for handler in logger.handlers:
        handler.flush()

    text = (tmp_path / "organizer.log").read_text(encoding="utf-8")
    assert "hello from test" in text


def test_reconfigure_does_not_duplicate_handlers(tmp_path) -> None:
    configure_logging(level="INFO", log_dir=tmp_path)
    logger = configure_logging(level="DEBUG", log_dir=tmp_path)

    assert len(logger.handlers) == 2
    assert logger.level == logging.DEBUG


def test_verbose_forces_debug(tmp_path) -> None:
    logger = configure_logging(level="WARNING", log_dir=tmp_path, verbose=True)

    assert logger.level == logging.DEBUG
    assert all(handler.level == logging.DEBUG for handler in logger.handlers)


def test_invalid_level_falls_back_to_info(tmp_path) -> None:
    logger = configure_logging(level="NOT-A-LEVEL", log_dir=tmp_path)

    assert logger.level == logging.INFO


def test_unwritable_log_dir_falls_back_to_console(tmp_path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")

    logger = configure_logging(level="INFO", log_dir=blocked)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
