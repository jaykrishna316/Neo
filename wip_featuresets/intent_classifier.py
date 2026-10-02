"""Intent classifier for categorizing developer/agent changes.

Classifies change descriptions into categories (feature/bugfix/refactor/chore)
and scopes (single-function/multi-function/file/module).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class ChangeCategory(Enum):
    """Type of change being made."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    CHORE = "chore"
    TEST = "test"
    DOCS = "docs"


class ChangeScope(Enum):
    """Scope of the change."""
    SINGLE_FUNCTION = "single-function"
    MULTI_FUNCTION = "multi-function"
    FILE = "file"
    MODULE = "module"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""
    category: ChangeCategory
    scope: ChangeScope
    keywords: list
    confidence: float


# Keyword patterns for classification
FEATURE_KEYWORDS = [
    "add", "new", "implement", "support", "enable", "introduce",
    "feature", "capability", "functionality"
]

BUGFIX_KEYWORDS = [
    "fix", "bug", "issue", "error", "crash", "broken", "resolve",
    "patch", "workaround", "correct"
]

REFACTOR_KEYWORDS = [
    "refactor", "clean", "improve", "optimize", "reorganize", "reorder",
    "restructure", "simplify", "clarify"
]

TEST_KEYWORDS = [
    "test", "tests", "unit test", "integration", "e2e", "coverage",
    "mock", "fixture"
]

DOCS_KEYWORDS = [
    "docs", "documentation", "comment", "docstring", "readme", "guide",
    "manual", "changelog"
]

CHORE_KEYWORDS = [
    "chore", "maintenance", "update", "upgrade", "bump", "dependency",
    "config", "build", "ci"
]


def classify_intent(description: str) -> ClassifiedIntent:
    """
    Classify a change description into category and scope.

    Args:
        description: Developer/agent intent description

    Returns:
        ClassifiedIntent with category, scope, and confidence
    """
    lower_desc = description.lower()
    found_keywords = []

    category_scores = {
        ChangeCategory.FEATURE: 0,
        ChangeCategory.BUGFIX: 0,
        ChangeCategory.REFACTOR: 0,
        ChangeCategory.TEST: 0,
        ChangeCategory.DOCS: 0,
        ChangeCategory.CHORE: 0,
    }

    for keyword in FEATURE_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.FEATURE] += 1
            found_keywords.append(keyword)

    for keyword in BUGFIX_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.BUGFIX] += 1
            found_keywords.append(keyword)

    for keyword in REFACTOR_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.REFACTOR] += 1
            found_keywords.append(keyword)

    for keyword in TEST_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.TEST] += 1
            found_keywords.append(keyword)

    for keyword in DOCS_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.DOCS] += 1
            found_keywords.append(keyword)

    for keyword in CHORE_KEYWORDS:
        if keyword in lower_desc:
            category_scores[ChangeCategory.CHORE] += 1
            found_keywords.append(keyword)

    category = max(category_scores, key=category_scores.get)
    if category_scores[category] == 0:
        category = ChangeCategory.CHORE

    category_confidence = (
        category_scores[category] /
        (sum(category_scores.values()) + 1)
    )

    scope = classify_scope(description)
    scope_confidence = get_scope_confidence(description)

    overall_confidence = (category_confidence + scope_confidence) / 2

    return ClassifiedIntent(
        category=category,
        scope=scope,
        keywords=list(set(found_keywords)),
        confidence=min(overall_confidence, 0.99)
    )


def classify_scope(description: str) -> ChangeScope:
    """Classify the scope of changes."""
    lower_desc = description.lower()

    if any(word in lower_desc for word in ["function", "method", "single", "one", "just"]):
        return ChangeScope.SINGLE_FUNCTION

    if any(word in lower_desc for word in ["multiple", "several", "functions", "methods"]):
        return ChangeScope.MULTI_FUNCTION

    if any(word in lower_desc for word in ["file", "module", "package", "class entire"]):
        if "module" in lower_desc or "package" in lower_desc:
            return ChangeScope.MODULE
        return ChangeScope.FILE

    if any(word in lower_desc for word in ["system", "architecture", "infrastructure"]):
        return ChangeScope.MODULE

    return ChangeScope.UNKNOWN


def get_scope_confidence(description: str) -> float:
    """Get confidence score for scope classification."""
    explicit_scope_keywords = [
        "function", "method", "file", "module", "package", "class"
    ]

    found = sum(1 for kw in explicit_scope_keywords if kw in description.lower())

    if found == 0:
        return 0.5
    elif found == 1:
        return 0.8
    else:
        return 0.9


def estimate_risk_from_intent(classified: ClassifiedIntent) -> str:
    """Estimate risk level based on classified intent."""
    risk_boosters = {
        ChangeCategory.BUGFIX: 1.2,
        ChangeCategory.REFACTOR: 1.1,
        ChangeCategory.FEATURE: 1.0,
        ChangeCategory.TEST: 0.6,
        ChangeCategory.DOCS: 0.4,
        ChangeCategory.CHORE: 0.7,
    }

    scope_multipliers = {
        ChangeScope.SINGLE_FUNCTION: 1.0,
        ChangeScope.MULTI_FUNCTION: 1.3,
        ChangeScope.FILE: 1.2,
        ChangeScope.MODULE: 1.5,
        ChangeScope.UNKNOWN: 1.0,
    }

    category_boost = risk_boosters.get(classified.category, 1.0)
    scope_mult = scope_multipliers.get(classified.scope, 1.0)
    confidence_factor = classified.confidence

    risk_score = category_boost * scope_mult * confidence_factor

    if risk_score < 0.7:
        return "LOW"
    elif risk_score < 1.2:
        return "MEDIUM"
    else:
        return "HIGH"


if __name__ == "__main__":
    test_descriptions = [
        "Add type hints to login_user function",
        "Fix null pointer exception in auth module",
        "Refactor database layer to use async/await",
        "Add unit tests for payment module",
        "Update README with new features",
        "Bump pytest to version 8.0",
    ]

    print("Intent Classification Examples")
    print("=" * 60)

    for desc in test_descriptions:
        classified = classify_intent(desc)
        risk = estimate_risk_from_intent(classified)

        print(f"\n📝 '{desc}'")
        print(f"   Category: {classified.category.value}")
        print(f"   Scope: {classified.scope.value}")
        print(f"   Keywords: {classified.keywords}")
        print(f"   Confidence: {classified.confidence:.0%}")
        print(f"   Estimated Risk: {risk}")
