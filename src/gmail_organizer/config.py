"""Load and validate the YAML rule configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .exceptions import ConfigError

_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)


def _normalize_label_path(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must be a non-empty label path")
    segments = value.split("/")
    if any(not segment.strip() or segment != segment.strip() for segment in segments):
        raise ValueError(
            f"{field_name} must not contain empty segments or spaces around '/'"
        )
    return value


class RuleConditions(BaseModel):
    """Conditions a rule can match. Entries within one list are ORed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    from_domains: list[str] = Field(default_factory=list)
    from_contains: list[str] = Field(default_factory=list)
    subject_contains_any: list[str] = Field(default_factory=list)

    @field_validator("from_domains")
    @classmethod
    def _clean_domains(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in values:
            domain = raw.strip().lstrip("@").casefold()
            if not domain or not _DOMAIN_RE.fullmatch(domain):
                raise ValueError(f"invalid sender domain: {raw!r}")
            cleaned.append(domain)
        return list(dict.fromkeys(cleaned))

    @field_validator("from_contains", "subject_contains_any")
    @classmethod
    def _clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in values:
            keyword = raw.strip()
            if not keyword:
                raise ValueError("condition entries must not be empty")
            cleaned.append(keyword)
        return list(dict.fromkeys(cleaned))


class RuleConfig(BaseModel):
    """One ordered classification rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    category: str
    match: Literal["all", "any"] = "all"
    when: RuleConditions

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("rule name must not be empty")
        return value

    @field_validator("category")
    @classmethod
    def _clean_category(cls, value: str) -> str:
        return _normalize_label_path(value, "category")

    @model_validator(mode="after")
    def _has_predicate(self) -> Self:
        if not (
            self.when.from_domains
            or self.when.from_contains
            or self.when.subject_contains_any
        ):
            raise ValueError("rule must define at least one condition in `when`")
        return self


class RulesConfig(BaseModel):
    """Top-level rules document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label_prefix: str = "Auto"
    label_unmatched: bool = False
    rules: list[RuleConfig] = Field(min_length=1)

    @field_validator("label_prefix")
    @classmethod
    def _clean_prefix(cls, value: str) -> str:
        # A trailing slash is a common convenience in configs like "Auto/".
        return _normalize_label_path(value.strip().rstrip("/"), "label_prefix")

    @model_validator(mode="after")
    def _unique_rule_names(self) -> Self:
        seen: set[str] = set()
        for rule in self.rules:
            key = rule.name.casefold()
            if key in seen:
                raise ValueError(f"duplicate rule name: {rule.name!r}")
            seen.add(key)
        return self

    def label_name(self, category: str) -> str:
        """Return the full Gmail label for a category."""
        return f"{self.label_prefix}/{category}"


def load_rules(path: Path | str) -> RulesConfig:
    """Read and validate a YAML rules file, raising ConfigError on failure."""
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"Rules file not found: {config_path}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read rules file {config_path}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"Rules file is empty: {config_path}")
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Rules file must contain a mapping at the top level: {config_path}"
        )

    try:
        return RulesConfig.model_validate(raw)
    except ValidationError as exc:
        details = _format_validation_error(exc)
        raise ConfigError(f"Invalid rules in {config_path}:\n{details}") from exc


def _format_validation_error(exc: ValidationError) -> str:
    lines: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        lines.append(f"  {location}: {error['msg']}")
    return "\n".join(lines)
