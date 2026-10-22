from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from gmail_organizer.models import EmailMessage

VALID_RULES_YAML = """\
label_prefix: "Auto"
label_unmatched: false
rules:
  - name: recruiting
    category: Recruiting
    match: any
    when:
      from_domains: [linkedin.com, greenhouse.io]
      from_contains: [talent, recruiter]
      subject_contains_any: [job application, interview]
"""


@pytest.fixture
def valid_rules_yaml() -> str:
    return VALID_RULES_YAML


@pytest.fixture
def make_message():
    def _make(
        *,
        message_id: str = "msg-1",
        sender_email: str = "alerts@linkedin.com",
        sender_name: str = "LinkedIn",
        subject: str = "You have a new job alert",
        label_ids: tuple[str, ...] = (),
    ) -> EmailMessage:
        return EmailMessage(
            id=message_id,
            thread_id="thread-1",
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            date=datetime(2026, 10, 22, tzinfo=timezone.utc),
            label_ids=label_ids,
        )

    return _make


@pytest.fixture
def write_rules(tmp_path: Path):
    def _write(text: str, filename: str = "rules.yaml") -> Path:
        path = tmp_path / filename
        path.write_text(text, encoding="utf-8")
        return path

    return _write
