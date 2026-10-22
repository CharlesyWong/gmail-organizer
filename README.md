# Gmail Organizer

A rule-based Gmail automation that reads message metadata and applies labels so
new mail is easier to triage. Built with the official Gmail API, OAuth2,
pydantic, and pytest.

> **Status:** v0.3.0 — the full rule-based labeling pipeline works end to end,
> with dry-run by default, incremental runs, and idempotent label application.
> See [CHANGELOG.md](CHANGELOG.md).

## What works today

- `auth` — desktop OAuth consent, token refresh, and scope validation.
- `list` — read sender, subject, date, and ID for recent messages.
- `run` — classify messages and add `Auto/<Category>` labels. Dry-run by default.
- `check-config` — validate the YAML rule file with field-level errors.

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

Adjust `GMAIL_QUERY`, limits, or paths if needed.

### 4. Authorize

```powershell
.\.venv\Scripts\python.exe -m gmail_organizer auth
```

Google will show **“Google hasn’t verified this app”** for a personal OAuth app.
Click **Advanced → Go to … (unsafe)**; this is expected for an unverified app
that you own. Approve the Gmail modify scope.

**Token lifetime:** while the OAuth app is in **Testing**, refresh tokens expire
after 7 days. Before using Windows Task Scheduler, publish the app to
**In production** (unverified is fine for personal use) and re-run `auth` once.
If Google disables the Publish button for your project, re-run `auth` weekly.

## Running it

```powershell
# Preview what would change (default; no Gmail writes)
.\.venv\Scripts\python.exe -m gmail_organizer run

# Apply labels to a bounded scan
.\.venv\Scripts\python.exe -m gmail_organizer run --apply --limit 20

# Deliberate backfill beyond the saved watermark
.\.venv\Scripts\python.exe -m gmail_organizer run --full --limit 100

# Forget the watermark and start over with a bootstrap scan
.\.venv\Scripts\python.exe -m gmail_organizer run --reset-state
```

### Run modes

- **Bootstrap** — used when no state file exists. Scans the base query and
  processes the newest `GMAIL_BOOTSTRAP_LIMIT` messages (default 100).
- **Incremental** — used after a successful apply. Scans the base query plus
  `after:<watermark - 1h>` with a one-hour overlap, capped by
  `GMAIL_INCREMENTAL_LIMIT` (default 200).
- **Full** — ignores the watermark and rescans the base query. Use it for older
  mail or after changing rules.
- On bootstrap, `--limit` sets the backfill depth. Mail older than that is not
  revisited unless you later run with `--full`.

### What a run does

1. Fetch metadata only: From, Subject, Date, labels, internal date.
2. Apply rules in order; the first match wins.
3. Reuse an existing `Auto/<Category>` label, or create it once.
4. Skip messages that already have the target label.
5. Add the label with `messages.modify` — labels are never removed, and mail is
   never archived, trashed, or marked read.
6. On a successful non-dry-run, atomically advance the local watermark in
   `data/state.json` (gitignored). Dry runs and partial failures do not advance
   it.

Sample output:

```text
DRY RUN — no Gmail changes were made.
would apply: 10
mode: bootstrap
fetched: 20 | classified: 10 | unmatched: 10
categories: Recruiting=10
already labeled: 0 | eligible: 10
labels applied: 0 | labels created: 0
failed: 0
state: unchanged
duration: 9.94s
```

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
Rule changes only affect messages processed in later runs. Use `--full` to
reclassify older mail; old labels are not removed automatically.

## Safety

- No message bodies are downloaded; only From/Subject/Date metadata.
- Dry-run is the default. `--apply` is required to write to Gmail.
- The only Gmail mutation is adding a label. Nothing is deleted or archived.
- Credentials and tokens stay in `.secrets/` (gitignored); run state is in
  `data/state.json` (gitignored).
- Per-message failures are isolated and counted; the run continues and does not
  advance the watermark.
- Exit codes: `0` success, `1` partial failures, `2` config/state error,
  `3` auth problem, `4` fatal Gmail API error.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m gmail_organizer --help
```

All 126 tests run offline with a fake Gmail client; no credentials or network
access are required for the test suite.

## Roadmap

- [x] v0.1.0 — config + rule classifier
- [x] v0.2.0 — OAuth + Gmail client
- [x] v0.3.0 — organizer pipeline, labels, watermark
- [ ] v0.4.0 — test hardening, logging, exit codes
- [ ] v1.0.0 — documented public release
- [ ] v1.1.0 — Windows Task Scheduler
- [ ] v1.2.0 — FastAPI endpoint

## License

MIT — see [LICENSE](LICENSE).
