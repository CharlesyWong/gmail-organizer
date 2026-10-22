# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-22

### Added

- Environment settings loaded from `.env`, with validation for paths, query,
  and positive limits.
- Desktop OAuth authorization, token refresh, and saved-scope validation.
- Gmail API client: paginated message IDs, metadata-only message reads, label
  listing/creation, and label application.
- Retry helper with exponential backoff, jitter, `Retry-After` support, and
  selective handling of 429, rate-limited 403, 5xx, and network timeouts.
- `auth` and `list` CLI commands.
- Offline `FakeGmailClient` plus tests for settings, auth errors, retry
  behavior, metadata parsing, pagination, and CLI exits. 89 tests total.
- UTF-8 safe CLI output for Windows consoles.

### Fixed

- Token scope validation now reads the scopes stored in the token file instead
  of overwriting them with the requested scopes.
- Non-ASCII subjects no longer crash the Windows console output.

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
