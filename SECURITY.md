# Security Policy

## Scope

Gmail Organizer is a **local, single-user** tool. It is not a hosted service
and must not be exposed directly to the internet.

The application requests the `https://www.googleapis.com/auth/gmail.modify`
OAuth scope: the narrowest practical scope for reading message metadata and
applying labels. It never fetches message bodies, sends mail, archives mail, or
deletes mail.

## Secrets

Never commit any of the following:

- `.env`
- `.secrets/` (contains `credentials.json` and `token.json`)
- `credentials.json`
- `token.json`
- `data/state.json`
- `logs/`

They are listed in `.gitignore`. Tokens are written locally, best-effort
permission-restricted, and are never logged.

Use your own Google Cloud OAuth client. Do not share client secrets or reuse a
client created by someone else.

## Reporting a vulnerability

Please **do not open a public issue containing exploit details**.

Use GitHub's private security advisory flow on this repository
(**Security → Advisories → Report a vulnerability**) and include:

- a description of the issue;
- steps to reproduce;
- the affected version or commit;
- whether credentials or mailbox data could be exposed.

If the advisory flow is unavailable, contact the repository owner through their
GitHub profile without posting sensitive details publicly.

## Supported versions

Security fixes target the latest release on `main`. Older tags are provided for
reference only.

## Local API (future)

The planned FastAPI endpoint must remain bound to `127.0.0.1`, require an API
key, default to dry-run, and never expose tokens. Publishing the OAuth app is a
separate concern from exposing the local API.
