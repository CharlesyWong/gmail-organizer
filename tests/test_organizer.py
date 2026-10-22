from __future__ import annotations

from datetime import datetime, timezone

from gmail_organizer.classification import RuleBasedClassifier
from gmail_organizer.config import RulesConfig
from gmail_organizer.exceptions import GmailAPIError
from gmail_organizer.label_manager import LabelManager
from gmail_organizer.organizer import Organizer
from gmail_organizer.state import RunState, StateStore

RECRUITING_RULE = {
    "name": "recruiting",
    "category": "Recruiting",
    "when": {"from_domains": ["linkedin.com"]},
}


def make_pipeline(
    gmail,
    tmp_path,
    *,
    rules=None,
    label_unmatched: bool = False,
    bootstrap_limit: int = 100,
    incremental_limit: int = 200,
):
    config = RulesConfig.model_validate(
        {
            "label_prefix": "Auto",
            "label_unmatched": label_unmatched,
            "rules": rules or [RECRUITING_RULE],
        }
    )
    store = StateStore(tmp_path / "state.json")
    organizer = Organizer(
        gmail=gmail,
        classifier=RuleBasedClassifier(config),
        labels=LabelManager(gmail, config.label_prefix),
        state=store,
        base_query="in:inbox -in:chats",
        bootstrap_limit=bootstrap_limit,
        incremental_limit=incremental_limit,
        label_unmatched=config.label_unmatched,
        clock=lambda: datetime(2026, 10, 22, tzinfo=timezone.utc),
    )
    return organizer, store


def test_bootstrap_dry_run_makes_no_changes(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(message_id="m1", internal_date_ms=1_729_600_000_000),
            make_message(
                message_id="m2",
                sender_email="news@example.org",
                sender_name="News",
                subject="Hello",
                internal_date_ms=1_729_600_001_000,
            ),
        ]
    )
    organizer, store = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=True)

    assert summary.mode == "bootstrap"
    assert summary.dry_run is True
    assert summary.fetched == 2
    assert summary.classified == 1
    assert summary.unmatched == 1
    assert summary.eligible == 1
    assert summary.labels_applied == 0
    assert summary.labels_created == 0
    assert summary.state_updated is False
    assert summary.by_category == {"Recruiting": 1}
    assert gmail.created_labels == []
    assert gmail.add_label_calls == []
    assert store.load() is None
    assert gmail.iter_calls == [("in:inbox -in:chats", 100)]


def test_apply_creates_and_applies_label(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(message_id="m1", internal_date_ms=1_729_600_000_000),
            make_message(
                message_id="m2",
                sender_email="news@example.org",
                sender_name="News",
                subject="Hello",
                internal_date_ms=1_729_600_001_000,
            ),
        ]
    )
    organizer, store = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.labels_applied == 1
    assert summary.labels_created == 1
    assert summary.state_updated is True
    assert summary.failed == 0
    assert gmail.created_labels == ["Auto/Recruiting"]

    label_id = gmail.labels["Auto/Recruiting"]
    assert ("m1", label_id) in gmail.add_label_calls
    assert label_id in gmail.messages["m1"].label_ids

    state = store.load()
    assert state is not None
    assert state.last_internal_date_ms == 1_729_600_001_000
    assert state.last_summary is not None
    assert state.last_summary.labels_applied == 1


def test_second_run_is_incremental_and_idempotent(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    organizer, store = make_pipeline(gmail, tmp_path)
    organizer.run(dry_run=False)

    summary = organizer.run(dry_run=True)

    state = store.load()
    assert state is not None
    expected_start = max(0, state.last_internal_date_ms // 1000 - 3600)

    assert summary.mode == "incremental"
    assert gmail.iter_calls[-1] == (
        f"in:inbox -in:chats after:{expected_start}",
        200,
    )
    assert summary.already_labeled == 1
    assert summary.eligible == 0
    assert summary.labels_applied == 0


def test_already_labeled_message_is_skipped(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [make_message(message_id="m1", label_ids=("L1",))]
    )
    gmail.labels = {"Auto/Recruiting": "L1"}
    organizer, _ = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.already_labeled == 1
    assert summary.eligible == 0
    assert summary.labels_applied == 0
    assert summary.labels_created == 0
    assert summary.state_updated is True
    assert gmail.add_label_calls == []


def test_unmatched_is_not_labeled_by_default(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(
                message_id="m1",
                sender_email="news@example.org",
                sender_name="News",
                subject="Hello",
            )
        ]
    )
    organizer, _ = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.unmatched == 1
    assert summary.classified == 0
    assert summary.by_category == {}
    assert summary.labels_applied == 0
    assert gmail.created_labels == []
    assert summary.state_updated is True


def test_unmatched_is_labeled_when_configured(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(
                message_id="m1",
                sender_email="news@example.org",
                sender_name="News",
                subject="Hello",
            )
        ]
    )
    organizer, _ = make_pipeline(gmail, tmp_path, label_unmatched=True)

    summary = organizer.run(dry_run=False)

    assert summary.unmatched == 1
    assert summary.classified == 0
    assert summary.by_category == {"Uncategorized": 1}
    assert summary.labels_applied == 1
    assert gmail.created_labels == ["Auto/Uncategorized"]


def test_per_message_failure_is_isolated_and_state_not_advanced(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(message_id="m1"),
            make_message(message_id="m2"),
        ]
    )
    gmail.fail_on_get["m2"] = GmailAPIError("boom")
    organizer, store = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.fetched == 1
    assert summary.failed == 1
    assert summary.labels_applied == 1
    assert summary.state_updated is False
    assert summary.errors == ["m2: GmailAPIError"]
    assert store.load() is None


def test_add_label_failure_is_isolated(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    gmail.fail_on_add["m1"] = GmailAPIError("boom")
    organizer, store = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.failed == 1
    assert summary.labels_applied == 0
    assert summary.state_updated is False
    assert store.load() is None


def test_watermark_never_moves_backwards(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    organizer, store = make_pipeline(gmail, tmp_path)
    store.save(
        RunState(
            last_internal_date_ms=2_000_000_000_000,
            last_run_utc=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )
    )

    summary = organizer.run(dry_run=False)

    assert summary.state_updated is True
    state = store.load()
    assert state is not None
    assert state.last_internal_date_ms == 2_000_000_000_000


def test_reset_state_starts_from_bootstrap(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    organizer, store = make_pipeline(gmail, tmp_path)
    store.save(
        RunState(
            last_internal_date_ms=2_000_000_000_000,
            last_run_utc=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )
    )

    summary = organizer.run(dry_run=False, reset_state=True)

    assert summary.mode == "bootstrap"
    assert gmail.iter_calls[-1] == ("in:inbox -in:chats", 100)
    state = store.load()
    assert state is not None
    assert state.last_internal_date_ms == 1_729_600_000_000


def test_full_mode_ignores_watermark(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    organizer, store = make_pipeline(gmail, tmp_path)
    store.save(
        RunState(
            last_internal_date_ms=2_000_000_000_000,
            last_run_utc=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )
    )

    summary = organizer.run(dry_run=False, full=True)

    assert summary.mode == "full"
    assert gmail.iter_calls[-1] == ("in:inbox -in:chats", 200)
    state = store.load()
    assert state is not None
    assert state.last_internal_date_ms == 2_000_000_000_000


def test_limit_and_query_override(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail(
        [
            make_message(message_id="m1"),
            make_message(message_id="m2"),
        ]
    )
    organizer, _ = make_pipeline(gmail, tmp_path)

    summary = organizer.run(
        dry_run=True,
        limit=1,
        query="in:inbox newer_than:1d",
    )

    assert summary.fetched == 1
    assert gmail.iter_calls[-1] == ("in:inbox newer_than:1d", 1)


def test_existing_label_is_reused_case_insensitively(
    make_message, make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([make_message(message_id="m1")])
    gmail.labels = {"auto/recruiting": "L1"}
    organizer, _ = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.labels_created == 0
    assert gmail.add_label_calls == [("m1", "L1")]


def test_no_messages_does_not_create_state(
    make_fake_gmail, tmp_path
) -> None:
    gmail = make_fake_gmail([])
    organizer, store = make_pipeline(gmail, tmp_path)

    summary = organizer.run(dry_run=False)

    assert summary.fetched == 0
    assert summary.state_updated is False
    assert store.load() is None
