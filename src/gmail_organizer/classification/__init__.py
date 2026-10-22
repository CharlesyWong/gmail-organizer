"""Classification strategies."""

from .base import Classifier
from .rules import RuleBasedClassifier, domain_matches

__all__ = ["Classifier", "RuleBasedClassifier", "domain_matches"]
