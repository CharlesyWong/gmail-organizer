"""Gmail adapter interface used by the organizer pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from ..models import EmailMessage


class GmailClient(Protocol):
    """The only Gmail surface the rest of the application depends on."""

    def iter_message_ids(self, query: str, limit: int) -> Iterator[str]: ...

    def get_message(self, message_id: str) -> EmailMessage: ...

    def list_labels(self) -> dict[str, str]: ...

    def create_label(self, name: str) -> str: ...

    def add_label(self, message_id: str, label_id: str) -> None: ...
