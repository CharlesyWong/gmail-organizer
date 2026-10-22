# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-10-22

### Added

- `scripts/run_organizer.bat`: Windows wrapper with virtualenv resolution,
  `python` fallback, `--apply` default, argument passthrough, task log, and
  exit-code propagation.
- `scripts/register_task.ps1`: daily scheduled task with `IgnoreNew`,
  `StartWhenAvailable`, a 30-minute limit, interactive-user principal, and a
  `-DryRun` inspection mode.
- README scheduling guide covering OAuth production publishing, registration,
  manual verification, logs, and removal.
- Windows CI smoke checks for the wrapper and registration script.

### Changed

- The dry-run summary header uses ASCII punctuation so `logs/task.log` reads
  correctly in the default Windows console encoding.

### Verified

- Wrapper `--help` and a real `--dry-run --limit 3` both exit 0.
- Registration `-DryRun` prints the expected `cmd.exe` action, working
  directory, daily trigger, settings, and run-as identity.

## [1.0.0] - 2026-10-22

First stable release.

### Added

- Public-facing README with CI badge, Mermaid architecture diagram, demo
  transcript, safety model, design tradeoffs, and quality metrics.
- `SECURITY.md` describing the local-only scope, secret handling, and private
  vulnerability reporting.
- `docs/demo.md` with sanitized, real-account run transcripts.
- Repository description, topics, and public release metadata.

### Notes

- No functional changes since v0.4.0. This release is the documented public
  v1.0.0 of the same verified pipeline.
- Quality: 149 offline tests, 94% coverage, 85% CI gate, Ubuntu + Windows.

## [0.4.0] - 2026-10-22

### Added

- Rotating file logging to `logs/organizer.log` (5 MB, three backups) plus
  console logging, configured through `logging_setup.py`.
- `--verbose` for `run` and `list`; DEBUG logs include sender and subject,
  while INFO logs contain only counts, label names, and state changes.
- Per-message failure logs with message ID and traceback but no subject.
- Unexpected CLI failures are logged and exit with code 4.
- Test coverage measurement with `pytest-cov` and an 85% CI gate.
- Hardening tests for token refresh, state write failures, retry caps,
  connection errors, error-list caps, label-creation failures, dry-run state
  preservation, and argparse validation. **149 tests, 94% coverage.**

### Changed

- CLI commands now configure logging after loading settings.
- `list --verbose` adds safe DEBUG diagnostics for each listed message.

## [0.3.0] - 2026-10-22

### Added

- `RunSummary` and `RunState` models with per-category counts.
- Atomic `StateStore` for the incremental watermark, with corruption recovery
  via `--reset-state`.
- Bootstrap, incremental, and full run modes. Incremental scans include a
  one-hour overlap and never move the watermark backwards.
- `LabelManager` with case-insensitive reuse, one-time creation, and recovery
  from a concurrent duplicate-label 409.
- `Organizer` pipeline with dry-run, idempotent skipping, per-message failure
  isolation, and state advancement only after a fully successful apply.
- `run` CLI command with `--apply`, `--full`, `--limit`, `--query`, and
  `--reset-state`; summary output and exit code 1 for partial failures.
- Tests for state persistence, label collisions, dry-run, idempotency,
  watermark behavior, mode selection, and CLI exits. 126 tests total.

### Changed

- Recruiting rule now targets dedicated job sources: Jobstreet and
  eFinancialCareers domains plus LinkedIn job-alert sender addresses. The broad
  `linkedin.com` domain match was removed because it also matched connection
  suggestions.

### Verified

- First real apply labeled 10 reviewed messages and created one `Auto/Recruiting`
  label. A full re-scan found all 10 already labeled and applied zero duplicates.

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
