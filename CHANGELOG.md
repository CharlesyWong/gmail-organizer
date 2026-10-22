# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-22

### Added

- `EmailMessage` and `ClassificationResult` data types.
- pydantic-validated YAML rules: unique rule names, required predicates, domain
  validation, and label path checks.
- Rule-based classifier with first-match precedence, exact/subdomain domain
  matching, and `all`/`any` condition modes.
- `check-config` CLI command. Invalid configuration exits with code 2 and a
  field-level error message.
- 53 offline tests covering config validation, classifier behavior, and CLI
  handling.

### Changed

- GitHub Actions bumped to `actions/checkout@v7` and
  `actions/setup-python@v7`.

## [0.0.0] - 2026-10-22

### Added

- Initial project scaffold: src-layout package, CLI entry point, YAML rule file,
  offline test setup, and GitHub Actions CI.
