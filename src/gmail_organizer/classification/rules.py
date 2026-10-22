"""Deterministic, configuration-driven classifier."""

from __future__ import annotations

from ..config import RuleConfig, RulesConfig
from ..models import ClassificationResult, EmailMessage


def domain_matches(sender_domain: str, pattern: str) -> bool:
    """Match an exact domain or a subdomain, never a lookalike domain."""
    domain = sender_domain.strip().casefold()
    expected = pattern.strip().lstrip("@").casefold()
    if not domain or not expected:
        return False
    return domain == expected or domain.endswith("." + expected)


class RuleBasedClassifier:
    """Apply ordered rules; the first matching rule wins."""

    def __init__(self, config: RulesConfig) -> None:
        self._config = config

    def classify(self, message: EmailMessage) -> ClassificationResult | None:
        for rule in self._config.rules:
            matched = self._matched_conditions(rule, message)
            if rule.match == "all":
                if len(matched) != self._populated_condition_count(rule):
                    continue
            elif not matched:
                continue

            return ClassificationResult(
                category=rule.category,
                label_name=self._config.label_name(rule.category),
                matched_rule=rule.name,
                reason="; ".join(matched),
            )
        return None

    @staticmethod
    def _populated_condition_count(rule: RuleConfig) -> int:
        return sum(
            bool(values)
            for values in (
                rule.when.from_domains,
                rule.when.from_contains,
                rule.when.subject_contains_any,
            )
        )

    def _matched_conditions(
        self, rule: RuleConfig, message: EmailMessage
    ) -> list[str]:
        matched: list[str] = []

        if rule.when.from_domains:
            for pattern in rule.when.from_domains:
                if domain_matches(message.sender_domain, pattern):
                    matched.append(f"from_domains={pattern}")
                    break

        if rule.when.from_contains:
            haystack = f"{message.sender_name} {message.sender_email}".casefold()
            for keyword in rule.when.from_contains:
                if keyword.casefold() in haystack:
                    matched.append(f"from_contains={keyword}")
                    break

        if rule.when.subject_contains_any:
            subject = message.subject.casefold()
            for keyword in rule.when.subject_contains_any:
                if keyword.casefold() in subject:
                    matched.append(f"subject_contains_any={keyword}")
                    break

        return matched
