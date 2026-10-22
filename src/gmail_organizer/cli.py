"""Command-line entry point for gmail-organizer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_rules
from .exceptions import AuthError, ConfigError, GmailAPIError
from .gmail.auth import authorize
from .gmail.google import build_gmail_client
from .settings import load_settings

DEFAULT_CONFIG_PATH = Path("config/rules.yaml")


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gmail-organizer",
        description="Rule-based Gmail organizer: classify new mail and apply labels.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND")

    subcommands.add_parser(
        "auth",
        help="Authorize Gmail access in the browser and save a token.",
    )

    listing = subcommands.add_parser(
        "list",
        help="List recent messages with sender, subject, and date.",
    )
    listing.add_argument(
        "--limit",
        type=_positive_int,
        default=10,
        help="Maximum number of messages to show (default: 10).",
    )
    listing.add_argument(
        "--query",
        default=None,
        help="Gmail search query (default: GMAIL_QUERY from .env).",
    )

    check = subcommands.add_parser(
        "check-config",
        help="Validate the YAML rule file and print a summary.",
    )
    check.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to the rules file (default: {DEFAULT_CONFIG_PATH})",
    )

    return parser


def _configure_output() -> None:
    """Avoid crashes when Windows consoles use a legacy code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _configure_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "auth":
        return _auth()
    if args.command == "list":
        return _list(args)
    if args.command == "check-config":
        return _check_config(args.config)

    parser.print_help()
    return 0


def _auth() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        return _print_config_error(exc)

    try:
        token_path = authorize(settings.credentials_path, settings.token_path)
    except AuthError as exc:
        print(f"Authorization error:\n{exc}", file=sys.stderr)
        return 3

    print(f"Authorized. Token saved to {token_path}")
    return 0


def _list(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        return _print_config_error(exc)

    query = args.query or settings.query
    try:
        client = build_gmail_client(settings)
        messages = [
            client.get_message(message_id)
            for message_id in client.iter_message_ids(query, args.limit)
        ]
    except AuthError as exc:
        print(f"Authorization error:\n{exc}", file=sys.stderr)
        return 3
    except GmailAPIError as exc:
        if exc.status_code == 401:
            print(
                "Gmail authorization failed. Run "
                "`python -m gmail_organizer auth` again.",
                file=sys.stderr,
            )
            return 3
        print(f"Gmail API error:\n{exc}", file=sys.stderr)
        return 4

    if not messages:
        print(f"No messages matched: {query}")
        return 0

    for message in messages:
        date = message.date.strftime("%Y-%m-%d") if message.date else "unknown-date"
        sender = (
            f"{message.sender_name} <{message.sender_email}>"
            if message.sender_name
            else (message.sender_email or "unknown-sender")
        )
        subject = " ".join(message.subject.split()) or "(no subject)"
        print(f"{date} | {sender} | {subject} | {message.id}")

    print(f"{len(messages)} message(s) from query: {query}")
    return 0


def _check_config(path: Path) -> int:
    try:
        config = load_rules(path)
    except ConfigError as exc:
        return _print_config_error(exc)

    categories = sorted({rule.category for rule in config.rules})
    rule_names = ", ".join(rule.name for rule in config.rules)

    print(f"OK: {path}")
    print(f"  prefix: {config.label_prefix}")
    print(f"  rules: {len(config.rules)} ({rule_names})")
    print(f"  categories: {', '.join(categories)}")
    print(f"  label unmatched: {config.label_unmatched}")
    return 0


def _print_config_error(exc: ConfigError) -> int:
    print(f"Configuration error:\n{exc}", file=sys.stderr)
    return 2
