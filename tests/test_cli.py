from __future__ import annotations

from gmail_organizer.cli import main


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
