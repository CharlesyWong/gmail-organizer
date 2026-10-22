from __future__ import annotations

import pytest

from gmail_organizer.config import load_rules
from gmail_organizer.exceptions import ConfigError


def test_loads_valid_rules(write_rules, valid_rules_yaml) -> None:
    config = load_rules(write_rules(valid_rules_yaml))

    assert config.label_prefix == "Auto"
    assert config.label_unmatched is False
    assert [rule.name for rule in config.rules] == ["recruiting"]
    assert config.label_name("Recruiting") == "Auto/Recruiting"


def test_missing_file_raises_config_error(tmp_path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_rules(tmp_path / "missing.yaml")


def test_invalid_yaml_raises_config_error(write_rules) -> None:
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_rules(write_rules("rules: [unclosed"))


def test_empty_file_raises_config_error(write_rules) -> None:
    with pytest.raises(ConfigError, match="empty"):
        load_rules(write_rules(""))


def test_top_level_must_be_mapping(write_rules) -> None:
    with pytest.raises(ConfigError, match="mapping"):
        load_rules(write_rules("- one\n- two\n"))


def test_empty_rule_list_rejected(write_rules) -> None:
    with pytest.raises(ConfigError):
        load_rules(write_rules("rules: []\n"))


def test_duplicate_rule_names_rejected(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: Same
    category: A
    when: {subject_contains_any: [alpha]}
  - name: same
    category: B
    when: {subject_contains_any: [beta]}
"""
    )
    with pytest.raises(ConfigError, match="duplicate rule name"):
        load_rules(path)


def test_duplicate_categories_allowed(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: by-domain
    category: Recruiting
    when: {from_domains: [linkedin.com]}
  - name: by-sender
    category: Recruiting
    when: {from_contains: [recruiter]}
"""
    )
    config = load_rules(path)

    assert [rule.category for rule in config.rules] == ["Recruiting", "Recruiting"]


def test_rule_requires_a_condition(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: empty
    category: A
    when: {}
"""
    )
    with pytest.raises(ConfigError, match="at least one condition"):
        load_rules(path)


def test_unknown_rule_key_rejected(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: typo
    category: A
    typo: true
    when: {subject_contains_any: [alpha]}
"""
    )
    with pytest.raises(ConfigError) as info:
        load_rules(path)

    assert "Extra inputs are not permitted" in str(info.value)


def test_unknown_top_level_key_rejected(write_rules) -> None:
    path = write_rules(
        """
settings: {}
rules:
  - name: valid
    category: A
    when: {subject_contains_any: [alpha]}
"""
    )
    with pytest.raises(ConfigError) as info:
        load_rules(path)

    assert "Extra inputs are not permitted" in str(info.value)


def test_invalid_match_mode_rejected(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: bad-match
    category: A
    match: sometimes
    when: {subject_contains_any: [alpha]}
"""
    )
    with pytest.raises(ConfigError):
        load_rules(path)


@pytest.mark.parametrize("category", ["/Finance", "Finance//Receipts", "Finance/"])
def test_invalid_category_path_rejected(write_rules, category: str) -> None:
    path = write_rules(
        f"""
rules:
  - name: bad-category
    category: "{category}"
    when: {{subject_contains_any: [alpha]}}
"""
    )
    with pytest.raises(ConfigError):
        load_rules(path)


def test_nested_category_is_supported(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: receipts
    category: Finance/Receipts
    when: {subject_contains_any: [receipt]}
"""
    )
    config = load_rules(path)

    assert config.label_name("Finance/Receipts") == "Auto/Finance/Receipts"


@pytest.mark.parametrize("prefix", ["", "/", "Auto//Sub"])
def test_invalid_label_prefix_rejected(write_rules, prefix: str) -> None:
    path = write_rules(
        f"""
label_prefix: "{prefix}"
rules:
  - name: valid
    category: A
    when: {{subject_contains_any: [alpha]}}
"""
    )
    with pytest.raises(ConfigError):
        load_rules(path)


def test_trailing_slash_in_prefix_normalized(write_rules) -> None:
    path = write_rules(
        """
label_prefix: "Auto/"
rules:
  - name: valid
    category: Recruiting
    when: {subject_contains_any: [alpha]}
"""
    )
    config = load_rules(path)

    assert config.label_prefix == "Auto"
    assert config.label_name("Recruiting") == "Auto/Recruiting"


def test_domains_are_normalized(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: domains
    category: A
    when:
      from_domains: ["@LinkedIn.COM", "mail.GREENHOUSE.io"]
"""
    )
    config = load_rules(path)

    assert config.rules[0].when.from_domains == [
        "linkedin.com",
        "mail.greenhouse.io",
    ]


@pytest.mark.parametrize(
    "domain",
    ["https://linkedin.com", "linkedin", "bad..domain.com", " "],
)
def test_invalid_domain_rejected(write_rules, domain: str) -> None:
    path = write_rules(
        f"""
rules:
  - name: bad-domain
    category: A
    when:
      from_domains: ["{domain}"]
"""
    )
    with pytest.raises(ConfigError):
        load_rules(path)


def test_empty_keyword_rejected(write_rules) -> None:
    path = write_rules(
        """
rules:
  - name: blank-keyword
    category: A
    when:
      subject_contains_any: [" "]
"""
    )
    with pytest.raises(ConfigError, match="must not be empty"):
        load_rules(path)
