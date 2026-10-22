"""OAuth2 desktop authorization and credential loading."""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..exceptions import AuthError

SCOPES = ("https://www.googleapis.com/auth/gmail.modify",)


def authorize(credentials_path: Path, token_path: Path) -> Path:
    """Run the desktop OAuth flow and save the token."""
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)

    if not credentials_path.is_file():
        raise AuthError(
            f"OAuth client credentials not found: {credentials_path}. "
            "Download a Desktop app client JSON from Google Cloud and save it there."
        )

    print("Opening your browser for Google authorization...")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), list(SCOPES)
        )
        credentials = flow.run_local_server(port=0, open_browser=True)
    except Exception as exc:
        raise AuthError(f"Google authorization failed: {exc}") from exc

    _save_token(credentials, token_path)
    return token_path


def load_credentials(token_path: Path) -> Credentials:
    """Load and, if necessary, refresh a previously saved token."""
    token_path = Path(token_path)
    if not token_path.is_file():
        raise AuthError(
            f"No saved Gmail token at {token_path}. "
            "Run `python -m gmail_organizer auth` first."
        )

    try:
        # Do not pass SCOPES here: that would overwrite the scopes stored in
        # the token file and hide a missing-scope problem.
        credentials = Credentials.from_authorized_user_file(str(token_path))
    except Exception as exc:
        raise AuthError(
            f"Could not read {token_path}. Delete it and run "
            "`python -m gmail_organizer auth` again."
        ) from exc

    saved_scopes = set(credentials.scopes or ())
    if not set(SCOPES).issubset(saved_scopes):
        raise AuthError(
            "The saved token does not include the Gmail modify scope. "
            f"Delete {token_path} and run `python -m gmail_organizer auth` again."
        )

    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError as exc:
                raise AuthError(
                    "The saved Gmail authorization expired or was revoked. "
                    "Run `python -m gmail_organizer auth` again."
                ) from exc
            _save_token(credentials, token_path)
        else:
            raise AuthError(
                f"The saved Gmail token at {token_path} is not usable. "
                "Run `python -m gmail_organizer auth` again."
            )

    return credentials


def _save_token(credentials: Credentials, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    try:
        os.chmod(token_path, 0o600)
    except OSError:
        # Windows does not implement POSIX permission bits fully; ignore.
        pass
