from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from gmail_organizer.exceptions import StateError
from gmail_organizer.models import RunSummary
from gmail_organizer.state import RunState, StateStore


def make_state(watermark: int = 1_729_600_000_000) -> RunState:
    return RunState(
        last_internal_date_ms=watermark,
        last_run_utc=datetime(2026, 10, 22, tzinfo=timezone.utc),
        last_summary=RunSummary(
            mode="bootstrap",
            dry_run=False,
            fetched=2,
            labels_applied=1,
        ),
    )


def test_missing_state_returns_none(tmp_path) -> None:
    assert StateStore(tmp_path / "state.json").load() is None


def test_save_and_load_roundtrip(tmp_path) -> None:
    store = StateStore(tmp_path / "nested" / "state.json")
    store.save(make_state())

    loaded = store.load()

    assert loaded is not None
    assert loaded.last_internal_date_ms == 1_729_600_000_000
    assert loaded.last_summary is not None
    assert loaded.last_summary.fetched == 2


def test_save_leaves_no_temp_file(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.save(make_state())

    assert (tmp_path / "state.json").is_file()
    assert not (tmp_path / "state.json.tmp").exists()


def test_corrupt_json_raises_state_error(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(StateError, match="--reset-state"):
        StateStore(path).load()


def test_invalid_schema_raises_state_error(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "last_internal_date_ms": 0,
                "last_run_utc": "2026-10-22T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StateError, match="Could not read run state"):
        StateStore(path).load()


def test_reset_removes_state(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save(make_state())

    store.reset()

    assert not path.exists()


def test_reset_missing_state_is_noop(tmp_path) -> None:
    StateStore(tmp_path / "missing.json").reset()
