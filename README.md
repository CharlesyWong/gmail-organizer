# Gmail Organizer

A rule-based Gmail automation that reads message metadata and applies labels so
new mail is easier to triage. Built with the official Gmail API, OAuth2,
pydantic, and pytest.

> **Status:** early scaffold (v0.0.0). The full feature set ships at v1.0.0.
> See [CHANGELOG.md](CHANGELOG.md) for release history.

## Planned behavior

- First run: classify and label the latest 100 inbox messages.
- Later runs: process only mail newer than the stored watermark.
- Rules live in a readable YAML file; the first matching rule wins.
- Dry-run by default. `--apply` is required to change anything in Gmail.
- Labels are prefixed `Auto/` and are only ever added — never removed,
  archived, or deleted.

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
```

## Roadmap

- v0.1.0 — config + rule classifier
- v0.2.0 — OAuth + Gmail client
- v0.3.0 — organizer pipeline, labels, watermark
- v1.0.0 — documented public release
- v1.1.0 — Windows Task Scheduler
- v1.2.0 — FastAPI endpoint

## License

MIT — see [LICENSE](LICENSE).
