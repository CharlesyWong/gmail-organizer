from __future__ import annotations

import pytest

from gmail_organizer.classification import RuleBasedClassifier, domain_matches
from gmail_organizer.config import RulesConfig


def make_config(rules: list[dict], *, prefix: str = "Auto") -> RulesConfig:
    return RulesConfig.model_validate({"label_prefix": prefix, "rules": rules})


@pytest.mark.parametrize(
    ("domain", "pattern", "expected"),
    [
        ("linkedin.com", "linkedin.com", True),
        ("mail.linkedin.com", "linkedin.com", True),
        ("LINKEDIN.COM", "LinkedIn.com", True),
        ("notlinkedin.com", "linkedin.com", False),
        ("linkedin.com.evil.example", "linkedin.com", False),
        ("", "linkedin.com", False),
    ],
)
def test_domain_matches(domain: str, pattern: str, expected: bool) -> None:
    assert domain_matches(domain, pattern) is expected


def test_first_matching_rule_wins(make_message) -> None:
    config = make_config(
        [
            {
                "name": "first",
                "category": "First",
                "when": {"from_domains": ["linkedin.com"]},
            },
            {
                "name": "second",
                "category": "Second",
                "when": {"subject_contains_any": ["job"]},
            },
        ]
    )

    result = RuleBasedClassifier(config).classify(make_message())

    assert result is not None
    assert result.category == "First"
    assert result.matched_rule == "first"


def test_domain_rule_matches_subdomain(make_message) -> None:
    config = make_config(
        [
            {
                "name": "jobs",
                "category": "Recruiting",
                "when": {"from_domains": ["linkedin.com"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(
            sender_email="jobs-noreply@mail.linkedin.com",
            sender_name="LinkedIn",
        )
    )

    assert result is not None
    assert result.label_name == "Auto/Recruiting"


def test_lookalike_domain_does_not_match(make_message) -> None:
    config = make_config(
        [
            {
                "name": "jobs",
                "category": "Recruiting",
                "when": {"from_domains": ["linkedin.com"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(sender_email="hello@notlinkedin.com", subject="Hello")
    )

    assert result is None


def test_from_contains_matches_display_name(make_message) -> None:
    config = make_config(
        [
            {
                "name": "talent",
                "category": "Recruiting",
                "when": {"from_contains": ["talent"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(
            sender_email="hello@example.org",
            sender_name="Talent Team",
            subject="Hello",
        )
    )

    assert result is not None
    assert result.category == "Recruiting"


def test_from_contains_matches_email(make_message) -> None:
    config = make_config(
        [
            {
                "name": "careers",
                "category": "Recruiting",
                "when": {"from_contains": ["careers"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(sender_email="careers@example.org", subject="Hello")
    )

    assert result is not None
    assert "from_contains=careers" in result.reason


def test_subject_match_is_case_insensitive(make_message) -> None:
    config = make_config(
        [
            {
                "name": "interview",
                "category": "Recruiting",
                "when": {"subject_contains_any": ["interview invitation"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(subject="INTERVIEW INVITATION: Software Engineer")
    )

    assert result is not None
    assert result.matched_rule == "interview"


def test_match_all_requires_every_condition(make_message) -> None:
    config = make_config(
        [
            {
                "name": "precise",
                "category": "Recruiting",
                "match": "all",
                "when": {
                    "from_domains": ["linkedin.com"],
                    "subject_contains_any": ["interview"],
                },
            }
        ]
    )
    classifier = RuleBasedClassifier(config)

    assert classifier.classify(make_message(subject="Weekly digest")) is None
    assert classifier.classify(make_message(subject="Interview invitation")) is not None


def test_match_any_needs_only_one_condition(make_message) -> None:
    config = make_config(
        [
            {
                "name": "broad",
                "category": "Recruiting",
                "match": "any",
                "when": {
                    "from_domains": ["other.example"],
                    "subject_contains_any": ["interview"],
                },
            }
        ]
    )
    classifier = RuleBasedClassifier(config)

    result = classifier.classify(make_message(subject="Interview invitation"))
    assert result is not None
    assert "subject_contains_any=interview" in result.reason
    assert classifier.classify(make_message(subject="Weekly digest")) is None


def test_unmatched_returns_none(make_message) -> None:
    config = make_config(
        [
            {
                "name": "other",
                "category": "Other",
                "when": {"from_domains": ["other.example"]},
            }
        ]
    )

    assert RuleBasedClassifier(config).classify(make_message()) is None


def test_missing_sender_and_subject_does_not_crash(make_message) -> None:
    config = make_config(
        [
            {
                "name": "jobs",
                "category": "Recruiting",
                "when": {"from_domains": ["linkedin.com"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(sender_email="", sender_name="", subject="")
    )

    assert result is None


def test_result_records_rule_and_reason(make_message) -> None:
    config = make_config(
        [
            {
                "name": "jobs",
                "category": "Recruiting",
                "when": {"from_domains": ["linkedin.com"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(make_message())

    assert result is not None
    assert result.matched_rule == "jobs"
    assert "from_domains=linkedin.com" in result.reason


def test_nested_category_label_name(make_message) -> None:
    config = make_config(
        [
            {
                "name": "receipts",
                "category": "Finance/Receipts",
                "when": {"subject_contains_any": ["receipt"]},
            }
        ]
    )

    result = RuleBasedClassifier(config).classify(
        make_message(subject="Your receipt from Example")
    )

    assert result is not None
    assert result.label_name == "Auto/Finance/Receipts"


def test_sender_domain_property(make_message) -> None:
    assert (
        make_message(sender_email="x@Mail.Example.COM").sender_domain
        == "mail.example.com"
    )
    assert make_message(sender_email="not-an-email").sender_domain == ""


def test_second_rule_used_when_first_does_not_match(make_message) -> None:
    config = make_config(
        [
            {
                "name": "other",
                "category": "Other",
                "when": {"from_domains": ["other.example"]},
            },
            {
                "name": "jobs",
                "category": "Recruiting",
                "when": {"from_domains": ["linkedin.com"]},
            },
        ]
    )

    result = RuleBasedClassifier(config).classify(make_message())

    assert result is not None
    assert result.matched_rule == "jobs"
