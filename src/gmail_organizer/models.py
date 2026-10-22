"""Core data types shared by the classifier, pipeline, and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class RunSummary(BaseModel):
    """Counts from one organizer run. Safe to log: no senders or subjects."""

    mode: Literal["bootstrap", "incremental", "full"]
    dry_run: bool
    fetched: int = 0
    classified: int = 0
    unmatched: int = 0
    eligible: int = 0
    already_labeled: int = 0
    labels_applied: int = 0
    labels_created: int = 0
    failed: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    state_updated: bool = False
    duration_seconds: float = 0.0
