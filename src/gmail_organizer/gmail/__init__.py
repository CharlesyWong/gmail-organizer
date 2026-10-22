"""Gmail API adapter and authentication helpers."""

from .auth import authorize, load_credentials
from .base import GmailClient
from .google import GoogleGmailClient, build_gmail_client, parse_message

__all__ = [
    "GmailClient",
    "GoogleGmailClient",
    "authorize",
    "build_gmail_client",
    "load_credentials",
    "parse_message",
]
