"""Classifier interface used by the organizer pipeline."""

from __future__ import annotations

from typing import Protocol

from ..models import ClassificationResult, EmailMessage


class Classifier(Protocol):
    """Turn one email's metadata into a category, or None when unmatched."""

    def classify(self, message: EmailMessage) -> ClassificationResult | None: ...
