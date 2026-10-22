from __future__ import annotations

import json

import pytest
from google.auth.exceptions import RefreshError

from gmail_organizer.exceptions import AuthError
from gmail_organizer.gmail.auth import SCOPES, authorize, load_credentials


class _FakeCredentials:
    def __init__(
        self,
        *,
        valid: bool,
        expired: bool,
        refresh_token: str | None,
        refresh_error: Exception | None = None,
    ) -> None:
        self.scopes = list(SCOPES)
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refresh_error = refresh_error
        self.refreshed = False

    def refresh(self, request) -> None:
        if self.refresh_error is not None:
            raise self.refresh_error
        self.refreshed = True
        self.valid = True

    def to_json(self) -> str:
        return '{"token": "new-token"}'


def stub_credentials(monkeypatch, credentials: _FakeCredentials) -> None:
    class _CredentialsStub:
        @staticmethod
        def from_authorized_user_file(path):
            return credentials

    monkeypatch.setattr(
        "gmail_organizer.gmail.auth.Credentials",
        _CredentialsStub,
    )


def make_token_file(tmp_path):
    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    return token_path


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


def test_expired_token_is_refreshed(tmp_path, monkeypatch) -> None:
    token_path = make_token_file(tmp_path)
    credentials = _FakeCredentials(
        valid=False,
        expired=True,
        refresh_token="refresh-token",
    )
    stub_credentials(monkeypatch, credentials)

    loaded = load_credentials(token_path)

    assert loaded is credentials
    assert credentials.refreshed is True
    assert token_path.read_text(encoding="utf-8") == '{"token": "new-token"}'


def test_refresh_failure_raises_auth_error(tmp_path, monkeypatch) -> None:
    token_path = make_token_file(tmp_path)
    credentials = _FakeCredentials(
        valid=False,
        expired=True,
        refresh_token="refresh-token",
        refresh_error=RefreshError("revoked"),
    )
    stub_credentials(monkeypatch, credentials)

    with pytest.raises(AuthError, match="expired or was revoked"):
        load_credentials(token_path)


def test_invalid_token_without_refresh_raises_auth_error(
    tmp_path, monkeypatch
) -> None:
    token_path = make_token_file(tmp_path)
    credentials = _FakeCredentials(
        valid=False,
        expired=False,
        refresh_token=None,
    )
    stub_credentials(monkeypatch, credentials)

    with pytest.raises(AuthError, match="not usable"):
        load_credentials(token_path)
