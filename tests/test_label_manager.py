from __future__ import annotations

import pytest
from fake_gmail import FakeGmailClient

from gmail_organizer.exceptions import GmailAPIError
from gmail_organizer.label_manager import LabelManager


def test_full_name() -> None:
    manager = LabelManager(FakeGmailClient(), "Auto")

    assert manager.full_name("Finance/Receipts") == "Auto/Finance/Receipts"


def test_refresh_is_case_insensitive(make_fake_gmail) -> None:
    gmail = make_fake_gmail()
    gmail.labels = {"auto/recruiting": "L1"}
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    label = manager.find("Recruiting")

    assert label is not None
    assert label.id == "L1"
    assert label.name == "auto/recruiting"


def test_ensure_reuses_existing_label(make_fake_gmail) -> None:
    gmail = make_fake_gmail()
    gmail.labels = {"Auto/Recruiting": "L1"}
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    label, created = manager.ensure("Recruiting")

    assert (label.id, created) == ("L1", False)
    assert gmail.created_labels == []


def test_ensure_creates_only_once(make_fake_gmail) -> None:
    gmail = make_fake_gmail()
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    first, created = manager.ensure("Recruiting")
    second, created_again = manager.ensure("Recruiting")

    assert created is True
    assert created_again is False
    assert first.id == second.id == "Label_1"
    assert gmail.created_labels == ["Auto/Recruiting"]


def test_409_refresh_recovers(make_fake_gmail) -> None:
    gmail = make_fake_gmail()

    def collide(name: str) -> str:
        gmail.labels[name] = "L9"
        raise GmailAPIError("conflict", status_code=409)

    gmail.create_label = collide  # type: ignore[method-assign]
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    label, created = manager.ensure("Recruiting")

    assert (label.id, created) == ("L9", False)


def test_409_without_matching_label_reraises(make_fake_gmail) -> None:
    gmail = make_fake_gmail()

    def collide(name: str) -> str:
        raise GmailAPIError("conflict", status_code=409)

    gmail.create_label = collide  # type: ignore[method-assign]
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    with pytest.raises(GmailAPIError):
        manager.ensure("Recruiting")


def test_non_409_create_error_propagates(make_fake_gmail) -> None:
    gmail = make_fake_gmail()

    def fail(name: str) -> str:
        raise GmailAPIError("server error", status_code=500)

    gmail.create_label = fail  # type: ignore[method-assign]
    manager = LabelManager(gmail, "Auto")
    manager.refresh()

    with pytest.raises(GmailAPIError):
        manager.ensure("Recruiting")
