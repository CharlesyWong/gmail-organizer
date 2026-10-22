"""The end-to-end fetch, classify, and label pipeline."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from .classification.base import Classifier
from .classification.rules import RuleBasedClassifier
from .config import RulesConfig
from .gmail.base import GmailClient
from .label_manager import LabelManager
from .models import RunSummary
from .settings import Settings
from .state import RunState, StateStore

UNCATEGORIZED = "Uncategorized"
MAX_RECORDED_ERRORS = 20

logger = logging.getLogger(__name__)


class Organizer:
    """Apply ordered rules to messages and add labels when explicitly applied."""

    def __init__(
        self,
        gmail: GmailClient,
        classifier: Classifier,
        labels: LabelManager,
        *,
        state: StateStore,
        base_query: str,
        bootstrap_limit: int = 100,
        incremental_limit: int = 200,
        label_unmatched: bool = False,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._gmail = gmail
        self._classifier = classifier
        self._labels = labels
        self._state = state
        self._base_query = base_query
        self._bootstrap_limit = bootstrap_limit
        self._incremental_limit = incremental_limit
        self._label_unmatched = label_unmatched
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        *,
        dry_run: bool = True,
        limit: int | None = None,
        query: str | None = None,
        full: bool = False,
        reset_state: bool = False,
    ) -> RunSummary:
        started = time.perf_counter()

        if reset_state:
            self._state.reset()

        previous = self._state.load()
        if full:
            mode = "full"
        elif previous is None:
            mode = "bootstrap"
        else:
            mode = "incremental"

        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")
        effective_limit = (
            limit
            if limit is not None
            else (
                self._bootstrap_limit
                if mode == "bootstrap"
                else self._incremental_limit
            )
        )

        search_query = query or self._base_query
        if mode == "incremental" and previous is not None:
            # One hour of overlap absorbs Gmail's date-granularity quirks.
            overlap_start = max(
                0,
                previous.last_internal_date_ms // 1000 - 3600,
            )
            search_query = f"{search_query} after:{overlap_start}".strip()

        logger.info(
            "Starting run: mode=%s dry_run=%s limit=%d query=%r",
            mode,
            dry_run,
            effective_limit,
            search_query,
        )

        summary = RunSummary(mode=mode, dry_run=dry_run)
        max_internal_date: int | None = None

        # Refresh once so reuse and already-labeled checks are reliable.
        self._labels.refresh()
        logger.debug("Label cache refreshed")

        for message_id in self._gmail.iter_message_ids(
            search_query, effective_limit
        ):
            try:
                message = self._gmail.get_message(message_id)
                summary.fetched += 1
                logger.debug(
                    "Fetched id=%s sender=%s subject=%r internal_date_ms=%s",
                    message.id,
                    message.sender_email,
                    message.subject,
                    message.internal_date_ms,
                )

                if message.internal_date_ms is not None:
                    max_internal_date = (
                        message.internal_date_ms
                        if max_internal_date is None
                        else max(max_internal_date, message.internal_date_ms)
                    )

                result = self._classifier.classify(message)
                if result is None:
                    summary.unmatched += 1
                    logger.debug("Unmatched id=%s", message.id)
                    if not self._label_unmatched:
                        continue
                    category = UNCATEGORIZED
                else:
                    summary.classified += 1
                    category = result.category
                    logger.debug(
                        "Matched id=%s rule=%s category=%s",
                        message.id,
                        result.matched_rule,
                        category,
                    )

                summary.by_category[category] = (
                    summary.by_category.get(category, 0) + 1
                )

                existing = self._labels.find(category)
                if existing is not None and existing.id in message.label_ids:
                    summary.already_labeled += 1
                    logger.debug(
                        "Already labeled id=%s category=%s",
                        message.id,
                        category,
                    )
                    continue

                summary.eligible += 1
                if dry_run:
                    logger.debug(
                        "Would label id=%s category=%s",
                        message.id,
                        category,
                    )
                    continue

                label, created = self._labels.ensure(category)
                if created:
                    summary.labels_created += 1
                    logger.info("Created label %s", label.name)
                self._gmail.add_label(message.id, label.id)
                summary.labels_applied += 1
                logger.debug(
                    "Applied label %s to id=%s",
                    label.name,
                    message.id,
                )
            except Exception as exc:
                # One bad message must not abort the run.
                summary.failed += 1
                logger.exception("Failed processing message %s", message_id)
                if len(summary.errors) < MAX_RECORDED_ERRORS:
                    summary.errors.append(
                        f"{message_id}: {type(exc).__name__}"
                    )

        summary.duration_seconds = round(time.perf_counter() - started, 2)

        if (
            not dry_run
            and summary.failed == 0
            and max_internal_date is not None
        ):
            previous_watermark = (
                previous.last_internal_date_ms if previous else 0
            )
            watermark = max(previous_watermark, max_internal_date)
            if watermark > 0:
                summary.state_updated = True
                self._state.save(
                    RunState(
                        last_internal_date_ms=watermark,
                        last_run_utc=self._clock(),
                        last_summary=summary,
                    )
                )
                logger.info("Advanced watermark to %d", watermark)

        logger.debug(
            "Run complete: mode=%s dry_run=%s fetched=%d classified=%d "
            "unmatched=%d eligible=%d applied=%d created=%d failed=%d "
            "state_updated=%s",
            summary.mode,
            summary.dry_run,
            summary.fetched,
            summary.classified,
            summary.unmatched,
            summary.eligible,
            summary.labels_applied,
            summary.labels_created,
            summary.failed,
            summary.state_updated,
        )
        return summary


def build_organizer(config: RulesConfig, settings: Settings) -> Organizer:
    """Compose the production pipeline. Tests build Organizer directly."""
    from .gmail.google import build_gmail_client

    gmail = build_gmail_client(settings)
    return Organizer(
        gmail=gmail,
        classifier=RuleBasedClassifier(config),
        labels=LabelManager(gmail, config.label_prefix),
        state=StateStore(settings.state_path),
        base_query=settings.query,
        bootstrap_limit=settings.bootstrap_limit,
        incremental_limit=settings.incremental_limit,
        label_unmatched=config.label_unmatched,
    )
