"""Core data types shared by the classifier, pipeline, and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """The message metadata the organizer is allowed to read from Gmail."""

    id: str
    thread_id: str
    sender_email: str
    sender_name: str
    subject: str
    date: datetime | None = None
    internal_date_ms: int | None = None
    label_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def sender_domain(self) -> str:
        """Return the normalized domain part of the sender address."""
        address = self.sender_email.strip().strip("<>")
        if "@" not in address:
            return ""
        return address.rsplit("@", 1)[1].strip().casefold()


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """The outcome of matching one message against the rule set."""

    category: str
    label_name: str
    matched_rule: str
    reason: str
