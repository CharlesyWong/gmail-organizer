"""Command-line entry point for gmail-organizer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_rules
from .exceptions import ConfigError

DEFAULT_CONFIG_PATH = Path("config/rules.yaml")


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-config":
        return _check_config(args.config)

    parser.print_help()
    return 0


def _check_config(path: Path) -> int:
    try:
        config = load_rules(path)
    except ConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        return 2

    categories = sorted({rule.category for rule in config.rules})
    rule_names = ", ".join(rule.name for rule in config.rules)

    print(f"OK: {path}")
    print(f"  prefix: {config.label_prefix}")
    print(f"  rules: {len(config.rules)} ({rule_names})")
    print(f"  categories: {', '.join(categories)}")
    print(f"  label unmatched: {config.label_unmatched}")
    return 0
