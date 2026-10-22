"""Retry transient Gmail/HTTP failures with bounded exponential backoff."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from googleapiclient.errors import HttpError

T = TypeVar("T")

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
RATE_LIMIT_REASONS = (
    "rateLimitExceeded",
    "userRateLimitExceeded",
    "quotaExceeded",
)


def _status_code(exc: HttpError) -> int | None:
    response = getattr(exc, "resp", None)
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "get"):
        status = response.get("status")
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_rate_limit(exc: HttpError) -> bool:
    content = exc.content
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
    return any(reason in str(content) for reason in RATE_LIMIT_REASONS)


def is_retryable(exc: BaseException) -> bool:
    """Return True only for transient failures that are safe to retry."""
    if isinstance(exc, HttpError):
        status = _status_code(exc)
        if status in RETRYABLE_STATUSES:
            return True
        return status == 403 and _is_rate_limit(exc)
    return isinstance(exc, (TimeoutError, ConnectionError))


def _retry_after_seconds(exc: BaseException) -> float | None:
    if not isinstance(exc, HttpError):
        return None
    response = getattr(exc, "resp", None)
    if response is None or not hasattr(response, "get"):
        return None
    value = response.get("retry-after") or response.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def retry_call(
    action: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    random_func: Callable[[], float] = random.random,
) -> T:
    """Call action, retrying only transient failures.

    max_attempts includes the first call. Delays use exponential backoff with
    up to 25% jitter, capped at max_delay. A Retry-After header wins.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(max_attempts):
        try:
            return action()
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts - 1:
                raise

            retry_after = _retry_after_seconds(exc)
            if retry_after is not None:
                delay = min(max_delay, retry_after)
            else:
                delay = min(max_delay, base_delay * (2**attempt))
                delay += random_func() * delay * 0.25
            sleep(delay)

    raise AssertionError("retry loop exited unexpectedly")
