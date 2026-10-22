"""Create and reuse Gmail labels without clobbering the user's labels."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import GmailAPIError
from .gmail.base import GmailClient


@dataclass(frozen=True, slots=True)
class Label:
    id: str
    name: str


class LabelManager:
    """Resolve category labels case-insensitively and create them on demand."""

    def __init__(self, gmail: GmailClient, label_prefix: str) -> None:
        self._gmail = gmail
        self._prefix = label_prefix
        self._labels: dict[str, Label] = {}

    def full_name(self, category: str) -> str:
        return f"{self._prefix}/{category}"

    def refresh(self) -> None:
        labels = self._gmail.list_labels()
        self._labels = {
            name.casefold(): Label(id=label_id, name=name)
            for name, label_id in labels.items()
        }

    def find(self, category: str) -> Label | None:
        return self._labels.get(self.full_name(category).casefold())

    def ensure(self, category: str) -> tuple[Label, bool]:
        """Return (label, created). Reuse an existing label where possible."""
        existing = self.find(category)
        if existing is not None:
            return existing, False

        name = self.full_name(category)
        try:
            label_id = self._gmail.create_label(name)
        except GmailAPIError as exc:
            if exc.status_code != 409:
                raise
            # Another process created the label between our refresh and create.
            self.refresh()
            existing = self.find(category)
            if existing is None:
                raise
            return existing, False

        label = Label(id=label_id, name=name)
        self._labels[name.casefold()] = label
        return label, True
