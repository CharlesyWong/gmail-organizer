from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from gmail_organizer.api import create_app, create_app_from_env
from gmail_organizer.exceptions import AuthError, GmailAPIError, StateError
from gmail_organizer.models import RunSummary

API_KEY = "test-api-key"


class FakeRunner:
    def __init__(
        self,
        summary: RunSummary | None = None,
        error: Exception | None = None,
    ) -> None:
        self.summary = summary or RunSummary(mode="bootstrap", dry_run=True)
        self.error = error
        self.calls: list[dict] = []

    def __call__(self, *, dry_run: bool, limit: int | None) -> RunSummary:
        self.calls.append({"dry_run": dry_run, "limit": limit})
        if self.error is not None:
            raise self.error
        return self.summary


def make_client(runner: FakeRunner) -> tuple[TestClient, object]:
    app = create_app(api_key=API_KEY, runner=runner)
    return TestClient(app), app


def headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def test_health_does_not_require_key() -> None:
    client, _ = make_client(FakeRunner())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"]


def test_run_requires_api_key() -> None:
    client, _ = make_client(FakeRunner())

    assert client.post("/run", json={}).status_code == 401


def test_run_rejects_wrong_api_key() -> None:
    client, _ = make_client(FakeRunner())

    response = client.post(
        "/run",
        json={},
        headers={"X-API-Key": "wrong"},
    )

    assert response.status_code == 401


def test_api_key_header_is_case_insensitive() -> None:
    client, _ = make_client(FakeRunner())

    response = client.post(
        "/run",
        json={},
        headers={"x-api-key": API_KEY},
    )

    assert response.status_code == 200


def test_run_defaults_to_dry_run() -> None:
    runner = FakeRunner()
    client, _ = make_client(runner)

    response = client.post("/run", headers=headers())

    assert response.status_code == 200
    assert response.json()["dry_run"] is True
    assert runner.calls == [{"dry_run": True, "limit": None}]


def test_run_forwards_dry_run_and_limit() -> None:
    runner = FakeRunner()
    client, _ = make_client(runner)

    response = client.post(
        "/run",
        json={"dry_run": False, "limit": 5},
        headers=headers(),
    )

    assert response.status_code == 200
    assert runner.calls == [{"dry_run": False, "limit": 5}]


def test_run_rejects_zero_limit() -> None:
    client, _ = make_client(FakeRunner())

    response = client.post(
        "/run",
        json={"limit": 0},
        headers=headers(),
    )

    assert response.status_code == 422


def test_run_returns_409_when_busy() -> None:
    client, app = make_client(FakeRunner())
    app.state.run_lock.acquire()
    try:
        response = client.post("/run", headers=headers())
    finally:
        app.state.run_lock.release()

    assert response.status_code == 409


def test_auth_error_maps_to_503() -> None:
    client, _ = make_client(FakeRunner(error=AuthError("expired")))

    assert client.post("/run", headers=headers()).status_code == 503


def test_gmail_error_maps_to_502() -> None:
    client, _ = make_client(
        FakeRunner(error=GmailAPIError("boom", status_code=500))
    )

    assert client.post("/run", headers=headers()).status_code == 502


def test_state_error_maps_to_500() -> None:
    client, _ = make_client(FakeRunner(error=StateError("corrupt")))

    assert client.post("/run", headers=headers()).status_code == 500


def test_unexpected_error_maps_to_500() -> None:
    client, _ = make_client(FakeRunner(error=RuntimeError("boom")))

    assert client.post("/run", headers=headers()).status_code == 500


def test_create_app_requires_api_key() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        create_app(api_key="", runner=FakeRunner())


def test_create_app_from_env_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("ORGANIZER_API_KEY", "")

    with pytest.raises(RuntimeError, match="ORGANIZER_API_KEY"):
        create_app_from_env()


def test_create_app_from_env_builds_app(monkeypatch, tmp_path) -> None:
    rules = tmp_path / "rules.yaml"
    rules.write_text(
        """
rules:
  - name: example
    category: Example
    when: {subject_contains_any: [example]}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("ORGANIZER_API_KEY", API_KEY)
    monkeypatch.setattr("gmail_organizer.api.DEFAULT_CONFIG_PATH", rules)
    monkeypatch.setattr(
        "gmail_organizer.api.configure_logging",
        lambda **kwargs: logging.getLogger("gmail_organizer"),
    )

    app = create_app_from_env()

    assert app.state.api_key == API_KEY
    assert app.title == "Gmail Organizer"
