from __future__ import annotations

from pathlib import Path

import pytest

from gmail_organizer.exceptions import ConfigError
from gmail_organizer.settings import Settings, load_settings

ENV_KEYS = (
    "GMAIL_CREDENTIALS_PATH",
    "GMAIL_TOKEN_PATH",
    "GMAIL_QUERY",
    "GMAIL_BOOTSTRAP_LIMIT",
    "GMAIL_INCREMENTAL_LIMIT",
    "GMAIL_STATE_PATH",
    "LOG_LEVEL",
    "ORGANIZER_API_KEY",
)


def clear_env(monkeypatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults(monkeypatch) -> None:
    clear_env(monkeypatch)

    settings = Settings.from_env(load_file=False)

    assert settings.credentials_path == Path(".secrets/credentials.json")
    assert settings.token_path == Path(".secrets/token.json")
    assert settings.query == "in:inbox -in:chats"
    assert settings.bootstrap_limit == 100
    assert settings.incremental_limit == 200
    assert settings.state_path == Path("data/state.json")
    assert settings.api_key is None


def test_environment_overrides(monkeypatch, tmp_path) -> None:
    clear_env(monkeypatch)
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(tmp_path / "client.json"))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(tmp_path / "token.json"))
    monkeypatch.setenv("GMAIL_QUERY", "in:inbox newer_than:7d")
    monkeypatch.setenv("GMAIL_BOOTSTRAP_LIMIT", "25")
    monkeypatch.setenv("GMAIL_INCREMENTAL_LIMIT", "50")
    monkeypatch.setenv("GMAIL_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("ORGANIZER_API_KEY", "secret-key")

    settings = load_settings(load_file=False)

    assert settings.credentials_path == tmp_path / "client.json"
    assert settings.token_path == tmp_path / "token.json"
    assert settings.query == "in:inbox newer_than:7d"
    assert settings.bootstrap_limit == 25
    assert settings.incremental_limit == 50
    assert settings.state_path == tmp_path / "state.json"
    assert settings.api_key == "secret-key"


def test_empty_api_key_becomes_none(monkeypatch) -> None:
    clear_env(monkeypatch)
    monkeypatch.setenv("ORGANIZER_API_KEY", "")

    assert Settings.from_env(load_file=False).api_key is None


def test_invalid_limit_raises_config_error(monkeypatch) -> None:
    clear_env(monkeypatch)
    monkeypatch.setenv("GMAIL_BOOTSTRAP_LIMIT", "not-a-number")

    with pytest.raises(ConfigError, match="Invalid environment setting"):
        load_settings(load_file=False)
