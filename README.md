# Gmail Organizer

A rule-based Gmail automation that reads message metadata and applies labels so
new mail is easier to triage. Built with the official Gmail API, OAuth2,
pydantic, and pytest.

> **Status:** v0.2.0 — OAuth and read-only Gmail metadata access work end to end.
> The labeling pipeline and watermark arrive in v0.3.0.
> See [CHANGELOG.md](CHANGELOG.md).

## What works today

- `auth` — desktop OAuth consent, token refresh, and scope validation.
- `list` — fetch sender, subject, date, and ID for recent messages. Read-only.
- `check-config` — validate the YAML rule file with field-level errors.

No current command modifies your mailbox. Label creation and application are
implemented in the Gmail client but are not exposed by the CLI until v0.3.0.

## Setup

### 1. Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 2. Create Google OAuth credentials

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project
   and enable the **Gmail API**.
2. Open **Google Auth platform → Branding**, set an app name/support email, and
   choose the **External** audience for a personal `@gmail.com` account. Add your
   account under **Audience → Test users**. A Workspace account may use
   **Internal** if the admin allows it.
3. Go to **Credentials → Create credentials → OAuth client ID → Desktop app**.
4. Download the JSON and save it as `.secrets/credentials.json`. That folder is
   gitignored.

### 3. Configure

```powershell
Copy-Item .env.example .env
```

Adjust `GMAIL_QUERY`, limits, or paths if needed. Defaults are suitable for a
personal inbox.

### 4. Authorize and test

```powershell
.\.venv\Scripts\python.exe -m gmail_organizer auth
.\.venv\Scripts\python.exe -m gmail_organizer list --limit 5
```

Google will show **“Google hasn’t verified this app”** for a personal OAuth app.
Click **Advanced → Go to … (unsafe)**; this is expected for an unverified app
that you own. Approve the Gmail modify scope.

The `gmail.modify` scope is the narrowest scope that supports both reading
metadata and applying labels. The current CLI only reads.

**Token lifetime:** while the OAuth app is in **Testing**, refresh tokens expire
after 7 days. Before using Windows Task Scheduler, publish the app to
**In production** (unverified is fine for personal use) and re-run `auth` once.
If Google disables the Publish button for your project, re-run `auth` weekly.

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
- The program requests `gmail.modify`; the current CLI is read-only.
- If the token is missing, invalid, or missing a scope, commands exit with
  code 3 and tell you to re-run `auth`.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m gmail_organizer --help
```

All 89 tests run offline with a fake Gmail client; no credentials or network
access are required for the test suite.

## Roadmap

- [x] v0.1.0 — config + rule classifier
- [x] v0.2.0 — OAuth + Gmail client
- [ ] v0.3.0 — organizer pipeline, labels, watermark
- [ ] v0.4.0 — test hardening, logging, exit codes
- [ ] v1.0.0 — documented public release
- [ ] v1.1.0 — Windows Task Scheduler
- [ ] v1.2.0 — FastAPI endpoint

## License

MIT — see [LICENSE](LICENSE).
