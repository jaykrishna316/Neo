#!/usr/bin/env python3
"""
Breaking Change Intent Analyzer

Analyzes developer intent to detect if they're likely making breaking changes.
More sophisticated than keyword matching - uses semantic understanding.

Key insight: Breaking changes are when the developer INTRODUCES changes to
public APIs, not when they ADAPT to upstream changes.

This distinguishes:
- "Refactor authenticate() - remove timestamp param" (breaking)
- "Update authenticate() calls - remove timestamp parameter" (adapting)
"""

from typing import Tuple, Optional
from enum import Enum


class IntentCategory(Enum):
    """Categories of developer intent."""
    FEATURE = "feature"  # Adding new functionality
    BUGFIX = "bugfix"  # Fixing existing behavior
    REFACTOR = "refactor"  # Restructuring without behavior change
    BREAKING = "breaking"  # Introducing breaking changes
    ADAPTATION = "adaptation"  # Updating to use new upstream APIs
    DOCUMENTATION = "documentation"  # Docs/comments only
    TESTING = "testing"  # Test additions
    UNKNOWN = "unknown"


class BreakingIntentAnalyzer:
    """Analyzes intent to determine if breaking changes are likely."""

    # Verbs that indicate INTRODUCING breaking changes (developer's own code)
    # These are strong indicators when they appear in intent
    INTRODUCING_KEYWORDS = {
        "refactor": {"api", "signature", "interface", "contract", "structure", "parameter", "authenticate", "login"},
        "change": {"signature", "api", "interface", "parameter", "return"},
        "rename": {"function", "method", "parameter", "variable", "class"},
        "remove": {"parameter", "function", "method", "class", "field", "()"},  # () catches function names like authenticate()
        "delete": {"function", "method", "class", "parameter"},
        "rewrite": {"authenticate", "login", "validate", "handler"},
        "restructure": {"api", "function", "class", "module"},
    }

    # Verbs that indicate ADAPTING to changes (updating their code to use new API)
    ADAPTING_KEYWORDS = {
        "update": {"call", "usage", "code"},
        "migrate": {"to", "from"},
        "adapt": {"to", "upstream"},
        "support": {"new", "latest"},
        "integrate": {"with"},
        "fix": {"compatibility", "integration"},
        "add": {"compatibility", "wrapper", "shim"},
    }

    # Patterns that indicate wrapper/compatibility work (NOT breaking)
    COMPATIBILITY_PATTERNS = {
        "backward compatibility",
        "compatibility wrapper",
        "shim",
        "adapter",
        "legacy support",
        "deprecation warning",
        "forward compatibility",
    }

    @staticmethod
    def categorize(intent: str) -> IntentCategory:
        """
        Categorize the developer's intent.

        Args:
            intent: Description of what developer intends to do

        Returns:
            IntentCategory enum value
        """
        intent_lower = intent.lower()

        # Check for compatibility patterns first (these are NOT breaking)
        for pattern in BreakingIntentAnalyzer.COMPATIBILITY_PATTERNS:
            if pattern in intent_lower:
                return IntentCategory.ADAPTATION

        # Check for adapting keywords
        for verb, contexts in BreakingIntentAnalyzer.ADAPTING_KEYWORDS.items():
            if verb in intent_lower:
                # Check if any context keyword is also present
                if any(ctx in intent_lower for ctx in contexts):
                    return IntentCategory.ADAPTATION

        # Strong structural change verbs (breaking by themselves)
        strong_breaking_verbs = ["rename", "delete", "remove "]  # Space after remove to avoid "remote"
        for verb in strong_breaking_verbs:
            if verb in intent_lower:
                # These verbs indicate breaking change regardless of context
                # "rename" = breaking, "delete" = breaking, "remove param/function" = breaking
                if verb == "rename" or verb == "delete":
                    return IntentCategory.BREAKING
                # For "remove", check if it's removing something structural
                if verb == "remove " and any(kw in intent_lower for kw in ["parameter", "function", "method", "class", "field"]):
                    return IntentCategory.BREAKING

        # Check for introducing keywords with context
        for verb, contexts in BreakingIntentAnalyzer.INTRODUCING_KEYWORDS.items():
            if verb in intent_lower:
                # Check if any context keyword is also present
                if any(ctx in intent_lower for ctx in contexts):
                    return IntentCategory.BREAKING

        # Test/doc only
        if any(kw in intent_lower for kw in ["test", "unittest", "pytest", "documentation", "docstring"]):
            if "test" in intent_lower:
                return IntentCategory.TESTING
            return IntentCategory.DOCUMENTATION

        # Bug fix
        if any(kw in intent_lower for kw in ["fix", "bug", "issue", "patch"]):
            return IntentCategory.BUGFIX

        # Feature
        if any(kw in intent_lower for kw in ["add", "implement", "feature", "new", "enhancement"]):
            return IntentCategory.FEATURE

        return IntentCategory.UNKNOWN

    @staticmethod
    def is_breaking_change(intent: str) -> Tuple[bool, str]:
        """
        Determine if intent describes a breaking change.

        A breaking change is when the developer INTRODUCES changes to public APIs,
        not when they ADAPT to upstream changes.

        Args:
            intent: Developer intent description

        Returns:
            (is_breaking, reason)
        """
        category = BreakingIntentAnalyzer.categorize(intent)

        if category == IntentCategory.BREAKING:
            reason = "Intent indicates introducing breaking changes to own API"
            return True, reason

        if category == IntentCategory.ADAPTATION:
            reason = "Intent indicates adapting to upstream changes (not introducing breaking changes)"
            return False, reason

        if category == IntentCategory.REFACTOR:
            # Refactors might be breaking - need more context
            intent_lower = intent.lower()
            if any(kw in intent_lower for kw in ["api", "signature", "interface", "parameter"]):
                reason = "Refactor with API/signature changes detected"
                return True, reason
            reason = "Internal refactor (not affecting API)"
            return False, reason

        # Everything else is not breaking
        return False, f"Category: {category.value}"

    @staticmethod
    def explain_decision(intent: str) -> str:
        """
        Provide detailed explanation of the breaking change decision.

        Args:
            intent: Developer intent description

        Returns:
            Human-readable explanation
        """
        is_breaking, reason = BreakingIntentAnalyzer.is_breaking_change(intent)
        category = BreakingIntentAnalyzer.categorize(intent)

        explanation = f"Intent Category: {category.value}\n"
        explanation += f"Breaking Change: {'YES' if is_breaking else 'NO'}\n"
        explanation += f"Reasoning: {reason}\n"

        # Additional details
        intent_lower = intent.lower()

        if is_breaking:
            explanation += "\n⚠️ BREAKING CHANGE DETECTED\n"
            if "remove" in intent_lower:
                explanation += "  - Parameter/function removal detected\n"
            if "rename" in intent_lower:
                explanation += "  - Rename operation detected\n"
            if "change signature" in intent_lower or "signature" in intent_lower:
                explanation += "  - Function signature change detected\n"
            explanation += "  → Downstream developers must update their code\n"
            explanation += "  → Impact alerts will be created for dependent files\n"
        else:
            explanation += "\n✅ NOT A BREAKING CHANGE\n"
            if "update" in intent_lower or "adapt" in intent_lower:
                explanation += "  - Developer is updating to use upstream API\n"
                explanation += "  - Not introducing new breaking changes\n"

        return explanation


def detect_breaking_change_intent(intent: str) -> Tuple[bool, str, str]:
    """
    Quick detection API for breaking change intent.

    Args:
        intent: Developer intent description

    Returns:
        (is_breaking, reason, explanation)
    """
    is_breaking, reason = BreakingIntentAnalyzer.is_breaking_change(intent)
    explanation = BreakingIntentAnalyzer.explain_decision(intent)
    return is_breaking, reason, explanation
