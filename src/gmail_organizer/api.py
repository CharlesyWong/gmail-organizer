"""Local, API-key protected FastAPI wrapper around the organizer pipeline."""

from __future__ import annotations

import logging
import os
import secrets
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .config import load_rules
from .exceptions import AuthError, GmailAPIError, StateError
from .logging_setup import configure_logging
from .models import RunSummary
from .organizer import build_organizer
from .settings import load_settings

API_HOST = "127.0.0.1"
API_PORT = 8000
DEFAULT_CONFIG_PATH = Path("config/rules.yaml")

Runner = Callable[..., RunSummary]

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class RunRequest(BaseModel):
    dry_run: bool = True
    limit: int | None = Field(default=None, gt=0)


def create_app(*, api_key: str, runner: Runner) -> FastAPI:
    """Build the app with injected dependencies for tests and embedding."""
    if not api_key:
        raise ValueError("api_key must not be empty")

    app = FastAPI(title="Gmail Organizer", version=__version__)
    app.state.api_key = api_key
    app.state.runner = runner
    app.state.run_lock = threading.Lock()

    def require_api_key(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> None:
        if x_api_key is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
        supplied = x_api_key.encode("utf-8", errors="replace")
        expected = app.state.api_key.encode("utf-8")
        if not secrets.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.post("/run", response_model=RunSummary)
    def run(
        body: RunRequest | None = None,
        _: None = Depends(require_api_key),
    ) -> RunSummary:
        request = body or RunRequest()
        lock: threading.Lock = app.state.run_lock
        if not lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409,
                detail="A run is already in progress",
            )
        try:
            try:
                return app.state.runner(
                    dry_run=request.dry_run,
                    limit=request.limit,
                )
            except AuthError as exc:
                logger.warning("API run authorization failure: %s", exc)
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Gmail authorization failed. "
                        "Re-run the auth command on the host."
                    ),
                ) from exc
            except GmailAPIError as exc:
                logger.error("API run Gmail failure: %s", exc)
                raise HTTPException(
                    status_code=502,
                    detail=f"Gmail API request failed (HTTP {exc.status_code}).",
                ) from exc
            except StateError as exc:
                logger.error("API run state failure: %s", exc)
                raise HTTPException(
                    status_code=500,
                    detail="Run state error. Check the server logs.",
                ) from exc
            except Exception as exc:
                logger.exception("Unexpected API run failure")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected run failure. Check the server logs.",
                ) from exc
        finally:
            lock.release()

    return app


def create_app_from_env() -> FastAPI:
    """Production factory: settings, rules, token, and logging from the host."""
    settings = load_settings()
    if not settings.api_key:
        raise RuntimeError(
            "ORGANIZER_API_KEY is not set. Generate one and add it to .env "
            "or the environment."
        )

    config_path = Path(
        os.getenv("ORGANIZER_CONFIG", str(DEFAULT_CONFIG_PATH))
    )
    config = load_rules(config_path)
    configure_logging(level=settings.log_level)

    def runner(*, dry_run: bool, limit: int | None) -> RunSummary:
        organizer = build_organizer(config, settings)
        return organizer.run(dry_run=dry_run, limit=limit)

    return create_app(api_key=settings.api_key, runner=runner)


def main() -> None:
    import uvicorn

    uvicorn.run(
        create_app_from_env(),
        host=API_HOST,
        port=API_PORT,
    )


if __name__ == "__main__":
    main()
