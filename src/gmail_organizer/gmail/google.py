"""Google Gmail API adapter."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

import httplib2
from google.auth.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..exceptions import GmailAPIError
from ..models import EmailMessage
from ..settings import Settings
from .auth import load_credentials
from .retry import retry_call

METADATA_HEADERS = ("From", "Subject", "Date")
HTTP_TIMEOUT_SECONDS = 30


def build_gmail_client(settings: Settings) -> "GoogleGmailClient":
    """Build a Gmail client from the saved OAuth token."""
    credentials = load_credentials(settings.token_path)
    return GoogleGmailClient(build_gmail_service(credentials))


def build_gmail_service(credentials: Credentials) -> Any:
    """Create the discovery client with an explicit network timeout."""
    http = AuthorizedHttp(
        credentials,
        http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS),
    )
    return build("gmail", "v1", http=http, cache_discovery=False)


class GoogleGmailClient:
    """A thin, retrying wrapper around the Gmail API discovery client."""

    def __init__(
        self,
        service: Any,
        *,
        max_attempts: int = 4,
        base_delay: float = 0.5,
        max_delay: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
        random_func: Callable[[], float] = random.random,
    ) -> None:
        self._service = service
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._sleep = sleep
        self._random_func = random_func

    def iter_message_ids(self, query: str, limit: int) -> Iterator[str]:
        if limit < 1:
            return

        page_token: str | None = None
        yielded = 0
        while yielded < limit:
            page_size = min(500, limit - yielded)
            params: dict[str, Any] = {
                "userId": "me",
                "q": query,
                "maxResults": page_size,
            }
            if page_token:
                params["pageToken"] = page_token

            response = self._execute(self._service.users().messages().list(**params))
            messages = response.get("messages") or []
            if not messages:
                break

            for item in messages:
                message_id = item.get("id")
                if not message_id:
                    continue
                yield str(message_id)
                yielded += 1
                if yielded >= limit:
                    break

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def get_message(self, message_id: str) -> EmailMessage:
        response = self._execute(
            self._service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=list(METADATA_HEADERS),
            )
        )
        return parse_message(response)

    def list_labels(self) -> dict[str, str]:
        response = self._execute(self._service.users().labels().list(userId="me"))
        labels: dict[str, str] = {}
        for label in response.get("labels") or []:
            name = label.get("name")
            label_id = label.get("id")
            if name and label_id:
                labels[str(name)] = str(label_id)
        return labels

    def create_label(self, name: str) -> str:
        response = self._execute(
            self._service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
        )
        label_id = response.get("id")
        if not label_id:
            raise GmailAPIError("Gmail did not return an id for the new label.")
        return str(label_id)

    def add_label(self, message_id: str, label_id: str) -> None:
        self._execute(
            self._service.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            )
        )

    def _execute(self, request: Any) -> dict[str, Any]:
        try:
            response = retry_call(
                lambda: request.execute(num_retries=0),
                max_attempts=self._max_attempts,
                base_delay=self._base_delay,
                max_delay=self._max_delay,
                sleep=self._sleep,
                random_func=self._random_func,
            )
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            raise GmailAPIError(
                f"Gmail API request failed with HTTP {status}.",
                status_code=status,
            ) from exc
        except (TimeoutError, ConnectionError) as exc:
            raise GmailAPIError("Gmail API request failed: network error.") from exc

        if not isinstance(response, dict):
            raise GmailAPIError("Gmail API returned an unexpected response.")
        return response


def parse_message(response: Mapping[str, Any]) -> EmailMessage:
    """Convert a Gmail messages.get metadata response into EmailMessage."""
    payload = response.get("payload") or {}
    headers: dict[str, str] = {}
    for header in payload.get("headers") or []:
        name = str(header.get("name", "")).casefold()
        if name:
            headers[name] = str(header.get("value", ""))

    sender_name, sender_email = parseaddr(headers.get("from", ""))
    subject = headers.get("subject", "")

    date: datetime | None = None
    raw_date = headers.get("date")
    if raw_date:
        try:
            date = parsedate_to_datetime(raw_date)
        except (TypeError, ValueError, OverflowError):
            date = None

    internal_date_ms: int | None = None
    raw_internal_date = response.get("internalDate")
    if raw_internal_date is not None:
        try:
            internal_date_ms = int(raw_internal_date)
        except (TypeError, ValueError):
            internal_date_ms = None

    label_ids = tuple(str(label_id) for label_id in response.get("labelIds") or ())

    return EmailMessage(
        id=str(response.get("id", "")),
        thread_id=str(response.get("threadId", "")),
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        date=date,
        internal_date_ms=internal_date_ms,
        label_ids=label_ids,
    )
