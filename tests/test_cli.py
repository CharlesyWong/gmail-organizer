from __future__ import annotations

import logging

import pytest

from gmail_organizer.cli import main
from gmail_organizer.exceptions import (
    AuthError,
    ConfigError,
    GmailAPIError,
    StateError,
)
from gmail_organizer.models import RunSummary
from gmail_organizer.settings import Settings


def test_check_config_valid(write_rules, valid_rules_yaml, capsys) -> None:
    path = write_rules(valid_rules_yaml)

    assert main(["check-config", "--config", str(path)]) == 0

    output = capsys.readouterr().out
    assert f"OK: {path}" in output
    assert "rules: 1 (recruiting)" in output
    assert "Recruiting" in output


def test_check_config_invalid_returns_2(write_rules, capsys) -> None:
    path = write_rules("rules: []\n")

    assert main(["check-config", "--config", str(path)]) == 2

    error = capsys.readouterr().err
    assert "Configuration error:" in error
    assert str(path) in error


def test_check_config_missing_file_returns_2(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.yaml"

    assert main(["check-config", "--config", str(missing)]) == 2

    assert "not found" in capsys.readouterr().err


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 0

    output = capsys.readouterr().out
    assert "check-config" in output
    assert "Rule-based Gmail organizer" in output


def test_auth_success(monkeypatch, tmp_path, capsys) -> None:
    token_path = tmp_path / "token.json"
    monkeypatch.setattr(
        "gmail_organizer.cli.load_settings",
        lambda: Settings(token_path=token_path),
    )
    monkeypatch.setattr(
        "gmail_organizer.cli.authorize",
        lambda credentials_path, token: token,
    )

    assert main(["auth"]) == 0
    assert "Token saved" in capsys.readouterr().out


def test_auth_error_returns_3(monkeypatch, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())

    def fail(credentials_path, token_path):
        raise AuthError("missing credentials")

    monkeypatch.setattr("gmail_organizer.cli.authorize", fail)

    assert main(["auth"]) == 3
    assert "missing credentials" in capsys.readouterr().err


def test_list_prints_metadata(
    monkeypatch, make_message, make_fake_gmail, capsys
) -> None:
    fake = make_fake_gmail(
        [
            make_message(
                message_id="m1",
                sender_name="LinkedIn",
                sender_email="jobs@linkedin.com",
                subject="Interview invitation",
            ),
            make_message(
                message_id="m2",
                sender_name="News",
                sender_email="news@example.org",
                subject="Weekly digest",
            ),
        ]
    )
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_gmail_client", lambda settings: fake
    )

    assert main(["list", "--limit", "2"]) == 0

    output = capsys.readouterr().out
    assert "m1" in output
    assert "Interview invitation" in output
    assert "2 message(s)" in output


def test_list_handles_unicode_subject(
    monkeypatch, make_message, make_fake_gmail, capsys
) -> None:
    fake = make_fake_gmail(
        [make_message(message_id="u1", subject="Application ✅ received")]
    )
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_gmail_client", lambda settings: fake
    )

    assert main(["list", "--limit", "1"]) == 0
    assert "✅" in capsys.readouterr().out


def test_list_empty_result(monkeypatch, make_fake_gmail, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_gmail_client",
        lambda settings: make_fake_gmail(),
    )

    assert main(["list"]) == 0
    assert "No messages matched" in capsys.readouterr().out


def test_list_auth_error_returns_3(monkeypatch, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())

    def fail(settings):
        raise AuthError("No saved Gmail token")

    monkeypatch.setattr("gmail_organizer.cli.build_gmail_client", fail)

    assert main(["list"]) == 3
    assert "No saved Gmail token" in capsys.readouterr().err


class _FailingClient:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def iter_message_ids(self, query: str, limit: int):
        raise GmailAPIError("request failed", status_code=self.status_code)


def test_list_401_returns_3(monkeypatch, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_gmail_client",
        lambda settings: _FailingClient(401),
    )

    assert main(["list"]) == 3
    assert "authorization failed" in capsys.readouterr().err.lower()


def test_list_api_error_returns_4(monkeypatch, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_gmail_client",
        lambda settings: _FailingClient(500),
    )

    assert main(["list"]) == 4
    assert "Gmail API error" in capsys.readouterr().err


class _FakeOrganizer:
    def __init__(self, summary: RunSummary | None = None, error=None) -> None:
        self.summary = summary
        self.error = error
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.summary


def make_summary(**overrides) -> RunSummary:
    values = {
        "mode": "bootstrap",
        "dry_run": True,
        "fetched": 2,
        "classified": 1,
        "unmatched": 1,
        "eligible": 1,
    }
    values.update(overrides)
    return RunSummary(**values)


def patch_run(monkeypatch, organizer) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_rules", lambda path: object())
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())
    monkeypatch.setattr(
        "gmail_organizer.cli.build_organizer",
        lambda config, settings: organizer,
    )


def test_run_defaults_to_dry_run(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(make_summary())
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 0
    assert fake.calls[0]["dry_run"] is True

    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "would apply: 1" in output


def test_run_apply(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(
        make_summary(
            dry_run=False,
            labels_applied=1,
            labels_created=1,
            state_updated=True,
        )
    )
    patch_run(monkeypatch, fake)

    assert main(["run", "--apply"]) == 0
    assert fake.calls[0]["dry_run"] is False

    output = capsys.readouterr().out
    assert "APPLY RUN" in output
    assert "labels applied: 1" in output


def test_run_forwards_options(monkeypatch) -> None:
    fake = _FakeOrganizer(make_summary())
    patch_run(monkeypatch, fake)

    assert main(
        [
            "run",
            "--limit",
            "5",
            "--query",
            "in:inbox",
            "--full",
            "--reset-state",
        ]
    ) == 0
    assert fake.calls[0] == {
        "dry_run": True,
        "limit": 5,
        "query": "in:inbox",
        "full": True,
        "reset_state": True,
    }


def test_run_partial_failure_exits_1(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(
        make_summary(failed=1, errors=["m1: GmailAPIError"])
    )
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 1
    assert "m1: GmailAPIError" in capsys.readouterr().err


def test_run_config_error_exits_2(monkeypatch, capsys) -> None:
    def fail_load(path):
        raise ConfigError("bad rules")

    monkeypatch.setattr("gmail_organizer.cli.load_rules", fail_load)
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())

    assert main(["run"]) == 2
    assert "Configuration error" in capsys.readouterr().err


def test_run_state_error_exits_2(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(error=StateError("corrupt state"))
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 2
    assert "State error" in capsys.readouterr().err


def test_run_auth_error_exits_3(monkeypatch, capsys) -> None:
    monkeypatch.setattr("gmail_organizer.cli.load_rules", lambda path: object())
    monkeypatch.setattr("gmail_organizer.cli.load_settings", lambda: Settings())

    def fail_build(config, settings):
        raise AuthError("No saved Gmail token")

    monkeypatch.setattr("gmail_organizer.cli.build_organizer", fail_build)

    assert main(["run"]) == 3
    assert "No saved Gmail token" in capsys.readouterr().err


def test_run_gmail_401_exits_3(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(error=GmailAPIError("expired", status_code=401))
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 3
    assert "authorization failed" in capsys.readouterr().err.lower()


def test_run_gmail_500_exits_4(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(error=GmailAPIError("server", status_code=500))
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 4
    assert "Gmail API error" in capsys.readouterr().err


def test_run_unexpected_error_exits_4(monkeypatch, capsys) -> None:
    fake = _FakeOrganizer(error=RuntimeError("boom"))
    patch_run(monkeypatch, fake)

    assert main(["run"]) == 4
    assert "Unexpected error" in capsys.readouterr().err


def test_run_rejects_apply_and_dry_run() -> None:
    with pytest.raises(SystemExit) as info:
        main(["run", "--apply", "--dry-run"])

    assert info.value.code == 2


def test_run_rejects_zero_limit() -> None:
    with pytest.raises(SystemExit) as info:
        main(["run", "--limit", "0"])

    assert info.value.code == 2


def test_list_rejects_zero_limit() -> None:
    with pytest.raises(SystemExit) as info:
        main(["list", "--limit", "0"])

    assert info.value.code == 2


def test_run_verbose_configures_debug(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_configure(**kwargs):
        calls.append(kwargs)
        return logging.getLogger("gmail_organizer")

    monkeypatch.setattr(
        "gmail_organizer.cli.configure_logging",
        fake_configure,
    )
    fake = _FakeOrganizer(make_summary())
    patch_run(monkeypatch, fake)

    assert main(["run", "--verbose"]) == 0
    assert calls == [{"level": "INFO", "verbose": True}]
