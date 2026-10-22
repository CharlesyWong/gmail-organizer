"""Runtime settings loaded from .env and environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import ConfigError

DEFAULT_QUERY = "in:inbox -in:chats"


class Settings(BaseModel):
    """Application settings, with defaults suitable for local development."""

    model_config = ConfigDict(frozen=True)

    credentials_path: Path = Path(".secrets/credentials.json")
    token_path: Path = Path(".secrets/token.json")
    query: str = DEFAULT_QUERY
    bootstrap_limit: int = Field(default=100, gt=0)
    incremental_limit: int = Field(default=200, gt=0)
    state_path: Path = Path("data/state.json")
    log_level: str = "INFO"
    api_key: str | None = None

    @classmethod
    def from_env(cls, *, load_file: bool = True) -> "Settings":
        if load_file:
            load_dotenv()
        return cls(
            credentials_path=Path(
                os.getenv("GMAIL_CREDENTIALS_PATH", ".secrets/credentials.json")
            ),
            token_path=Path(os.getenv("GMAIL_TOKEN_PATH", ".secrets/token.json")),
            query=os.getenv("GMAIL_QUERY", DEFAULT_QUERY),
            bootstrap_limit=os.getenv("GMAIL_BOOTSTRAP_LIMIT", "100"),
            incremental_limit=os.getenv("GMAIL_INCREMENTAL_LIMIT", "200"),
            state_path=Path(os.getenv("GMAIL_STATE_PATH", "data/state.json")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            api_key=os.getenv("ORGANIZER_API_KEY") or None,
        )


def load_settings(*, load_file: bool = True) -> Settings:
    """Load settings, converting pydantic errors into ConfigError."""
    try:
        return Settings.from_env(load_file=load_file)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(f"Invalid environment setting(s): {details}") from exc
