"""In-memory GmailClient for offline tests. Query filtering is not simulated."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import replace

from gmail_organizer.models import EmailMessage


class FakeGmailClient:
    def __init__(
        self,
        messages: Iterable[EmailMessage] = (),
        labels: dict[str, str] | None = None,
    ) -> None:
        self.messages: dict[str, EmailMessage] = {
            message.id: message for message in messages
        }
        self.labels: dict[str, str] = dict(labels or {})
        self.created_labels: list[str] = []
        self.add_label_calls: list[tuple[str, str]] = []
        self.get_message_calls: list[str] = []
        self.fail_on_get: dict[str, Exception] = {}
        self.fail_on_add: dict[str, Exception] = {}
        self._next_label_id = 1

    def iter_message_ids(self, query: str, limit: int) -> Iterator[str]:
        for message_id in list(self.messages)[:limit]:
            yield message_id

    def get_message(self, message_id: str) -> EmailMessage:
        self.get_message_calls.append(message_id)
        if message_id in self.fail_on_get:
            raise self.fail_on_get[message_id]
        return self.messages[message_id]

    def list_labels(self) -> dict[str, str]:
        return dict(self.labels)

    def create_label(self, name: str) -> str:
        label_id = f"Label_{self._next_label_id}"
        self._next_label_id += 1
        self.labels[name] = label_id
        self.created_labels.append(name)
        return label_id

    def add_label(self, message_id: str, label_id: str) -> None:
        if message_id in self.fail_on_add:
            raise self.fail_on_add[message_id]
        self.add_label_calls.append((message_id, label_id))
        message = self.messages[message_id]
        if label_id not in message.label_ids:
            self.messages[message_id] = replace(
                message,
                label_ids=message.label_ids + (label_id,),
            )
