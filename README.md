# Gmail Organizer

A rule-based Gmail automation that reads message metadata and applies labels so
new mail is easier to triage. Built with the official Gmail API, OAuth2,
pydantic, and pytest.

> **Status:** v0.1.0 — the rule engine and config validation are complete and
> fully tested offline. Gmail integration lands in v0.2.0 and v0.3.0.
> See [CHANGELOG.md](CHANGELOG.md).

## How it will work

- First run: classify and label the latest 100 inbox messages.
- Later runs: process only mail newer than the stored watermark.
- Rules live in a readable YAML file; the first matching rule wins.
- Dry-run by default. `--apply` is required to change anything in Gmail.
- Labels are prefixed `Auto/` and are only ever added — never removed,
  archived, or deleted.

## Configuration

Rules live in [`config/rules.yaml`](config/rules.yaml). Validate after editing:

```powershell
.\.venv\Scripts\python.exe -m gmail_organizer check-config
```

The validator enforces:

- `label_prefix` is non-empty; a trailing `/` is normalized away.
- Every rule has a unique `name` and at least one condition.
- `category` may be nested (`Finance/Receipts`) and may repeat across rules.
- `match` is `all` (default) or `any`.
- Conditions:
  - `from_domains` — exact domain or subdomain. `linkedin.com` matches
    `mail.linkedin.com` but never `notlinkedin.com`.
  - `from_contains` — case-insensitive substring of the sender name or address.
  - `subject_contains_any` — case-insensitive substring of the subject.
- Entries within a list are ORed; populated conditions are combined by `match`.
- Rules are evaluated top to bottom, and the first match wins.

Labels are named `<label_prefix>/<category>`, for example `Auto/Recruiting`.

## Safety

- No message bodies are downloaded; only From/Subject/Date metadata.
- Credentials and tokens stay in `.secrets/` (gitignored).
- The program requests the narrowest practical Gmail scope: `gmail.modify`.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m gmail_organizer --help
.\.venv\Scripts\python.exe -m gmail_organizer check-config
```

## Roadmap

- [x] v0.1.0 — config + rule classifier
- [ ] v0.2.0 — OAuth + Gmail client
- [ ] v0.3.0 — organizer pipeline, labels, watermark
- [ ] v0.4.0 — test hardening, logging, exit codes
- [ ] v1.0.0 — documented public release
- [ ] v1.1.0 — Windows Task Scheduler
- [ ] v1.2.0 — FastAPI endpoint

## License

MIT — see [LICENSE](LICENSE).
