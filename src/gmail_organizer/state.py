"""Incremental watermark persistence."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import StateError
from .models import RunSummary


class RunState(BaseModel):
    """The last successfully processed message and run metadata."""

    model_config = ConfigDict(extra="forbid")

    last_internal_date_ms: int = Field(gt=0)
    last_run_utc: datetime
    last_summary: RunSummary | None = None


class StateStore:
    """Read and atomically write the local state JSON."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> RunState | None:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return RunState.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise StateError(
                f"Could not read run state {self.path}. "
                "Delete it or rerun with --reset-state. "
                f"Details: {exc}"
            ) from exc

    def save(self, state: RunState) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StateError(
                f"Could not create state directory {self.path.parent}: {exc}"
            ) from exc

        temp_path = self.path.with_name(self.path.name + ".tmp")
        try:
            temp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            os.replace(temp_path, self.path)
        except OSError as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise StateError(f"Could not write run state {self.path}: {exc}") from exc

    def reset(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise StateError(
                f"Could not remove run state {self.path}: {exc}"
            ) from exc
