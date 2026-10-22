from __future__ import annotations

import json

import pytest

from gmail_organizer.exceptions import AuthError
from gmail_organizer.gmail.auth import authorize, load_credentials


def test_authorize_requires_client_credentials(tmp_path) -> None:
    with pytest.raises(AuthError, match="not found"):
        authorize(tmp_path / "missing.json", tmp_path / "token.json")


def test_load_credentials_requires_token(tmp_path) -> None:
    with pytest.raises(AuthError, match="No saved Gmail token"):
        load_credentials(tmp_path / "token.json")


def test_load_credentials_rejects_malformed_token(tmp_path) -> None:
    token_path = tmp_path / "token.json"
    token_path.write_text("not valid json", encoding="utf-8")

    with pytest.raises(AuthError, match="Could not read"):
        load_credentials(token_path)


def test_load_credentials_rejects_wrong_scope(tmp_path) -> None:
    token_path = tmp_path / "token.json"
    token_path.write_text(
        json.dumps(
            {
                "token": "access-token",
                "refresh_token": "refresh-token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "client.apps.googleusercontent.com",
                "client_secret": "client-secret",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AuthError, match="does not include"):
        load_credentials(token_path)
