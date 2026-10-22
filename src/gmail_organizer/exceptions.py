"""Expected application errors."""

from __future__ import annotations


class GmailOrganizerError(Exception):
    """Base class for errors the CLI can present to the user."""


class ConfigError(GmailOrganizerError):
    """The rules file is missing, unreadable, or invalid."""


class AuthError(GmailOrganizerError):
    """Gmail credentials are missing, expired, or insufficient."""


class GmailAPIError(GmailOrganizerError):
    """A Gmail API request failed."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
