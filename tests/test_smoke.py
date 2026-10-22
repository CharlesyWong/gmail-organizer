from gmail_organizer import __version__
from gmail_organizer.cli import build_parser, main


def test_package_has_version() -> None:
    assert __version__ == "0.3.0"


def test_cli_prints_help(capsys) -> None:
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "Rule-based Gmail organizer" in output


def test_parser_program_name() -> None:
    assert build_parser().prog == "gmail-organizer"
