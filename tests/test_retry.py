from __future__ import annotations

import httplib2
import pytest
from googleapiclient.errors import HttpError

from gmail_organizer.gmail.retry import is_retryable, retry_call


def http_error(status: int, reason: str = "", retry_after: str | None = None) -> HttpError:
    headers = {"status": status, "reason": "test"}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    content = f'{{"error": {{"errors": [{{"reason": "{reason}"}}]}}}}'.encode()
    return HttpError(httplib2.Response(headers), content)


def test_retries_429_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    def action() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise http_error(429, "rateLimitExceeded")
        return "ok"

    result = retry_call(
        action,
        max_attempts=4,
        base_delay=0.5,
        sleep=sleeps.append,
        random_func=lambda: 0.0,
    )

    assert result == "ok"
    assert calls == 3
    assert sleeps == [0.5, 1.0]


def test_retries_rate_limit_403() -> None:
    calls = 0

    def action() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise http_error(403, "userRateLimitExceeded")
        return "ok"

    result = retry_call(
        action,
        max_attempts=2,
        sleep=lambda _: None,
        random_func=lambda: 0.0,
    )

    assert result == "ok"
    assert calls == 2


def test_does_not_retry_permission_403() -> None:
    calls = 0

    def action() -> None:
        nonlocal calls
        calls += 1
        raise http_error(403, "permissionDenied")

    with pytest.raises(HttpError):
        retry_call(
            action,
            max_attempts=3,
            sleep=lambda _: None,
            random_func=lambda: 0.0,
        )

    assert calls == 1


def test_does_not_retry_400() -> None:
    error = http_error(400, "invalidArgument")
    assert is_retryable(error) is False

    with pytest.raises(HttpError):
        retry_call(
            lambda: (_ for _ in ()).throw(error),
            max_attempts=3,
            sleep=lambda _: None,
            random_func=lambda: 0.0,
        )


def test_gives_up_after_max_attempts() -> None:
    calls = 0
    sleeps: list[float] = []

    def action() -> None:
        nonlocal calls
        calls += 1
        raise http_error(503, "backendError")

    with pytest.raises(HttpError):
        retry_call(
            action,
            max_attempts=3,
            base_delay=0.5,
            sleep=sleeps.append,
            random_func=lambda: 0.0,
        )

    assert calls == 3
    assert sleeps == [0.5, 1.0]


def test_honors_retry_after() -> None:
    calls = 0
    sleeps: list[float] = []

    def action() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise http_error(429, "rateLimitExceeded", retry_after="7")
        return "ok"

    result = retry_call(
        action,
        max_attempts=2,
        sleep=sleeps.append,
        random_func=lambda: 0.0,
    )

    assert result == "ok"
    assert sleeps == [7.0]


def test_retries_timeout() -> None:
    calls = 0

    def action() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("timed out")
        return "ok"

    result = retry_call(
        action,
        max_attempts=2,
        sleep=lambda _: None,
        random_func=lambda: 0.0,
    )

    assert result == "ok"
    assert calls == 2


def test_invalid_max_attempts() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        retry_call(lambda: None, max_attempts=0)
