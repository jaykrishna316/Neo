"""
1D: Semantic Invariant Checking
Detect logical conflicts that git can't see (invariant violations).
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SemanticInvariant:
    """Represents a semantic invariant (contract) in code"""
    resource: str
    invariant_description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    code_location: str  # file:line
    requires: Set[str]  # what conditions must be true


class SemanticChecker:
    """Detects semantic violations and logical conflicts"""

    def __init__(self):
        self.invariants: Dict[str, List[SemanticInvariant]] = {}  # resource -> invariants
        self.violations: List[Dict] = []

    def register_invariant(self, resource: str, invariant: SemanticInvariant):
        """Register a semantic invariant for a resource"""
        if resource not in self.invariants:
            self.invariants[resource] = []
        self.invariants[resource].append(invariant)

    def check_change(self, developer: str, resource: str,
                    changed_lines: List[int], change_description: str) -> List[Dict]:
        """
        Check if a change violates any semantic invariants.

        Returns: List of violations found
        """
        violations = []

        if resource not in self.invariants:
            return violations

        for invariant in self.invariants[resource]:
            # Check if this change affects the invariant
            if self._affects_invariant(invariant, changed_lines):
                # Check if invariant is violated
                if self._violates_invariant(invariant, change_description):
                    violation = {
                        'developer': developer,
                        'resource': resource,
                        'invariant': invariant.invariant_description,
                        'severity': invariant.severity,
                        'timestamp': datetime.now(),
                        'description': f"{change_description} violates {invariant.invariant_description}",
                        'suggestion': self._get_fix_suggestion(invariant)
                    }
                    violations.append(violation)
                    self.violations.append(violation)

        return violations

    def get_violations_for_developer(self, developer: str) -> List[Dict]:
        """Get all violations for a developer"""
        return [v for v in self.violations if v['developer'] == developer]

    def get_violations_for_resource(self, resource: str) -> List[Dict]:
        """Get all violations for a resource"""
        return [v for v in self.violations if v['resource'] == resource]

    def get_high_severity_violations(self) -> List[Dict]:
        """Get all HIGH and CRITICAL violations"""
        return [v for v in self.violations if v['severity'] in ['HIGH', 'CRITICAL']]

    def _affects_invariant(self, invariant: SemanticInvariant, changed_lines: List[int]) -> bool:
        """Check if changed lines affect this invariant"""
        # Simplified check - in production, would do more sophisticated analysis
        try:
            if ':' in invariant.code_location:
                _, line_str = invariant.code_location.split(':')
                invariant_line = int(line_str)
                # Check if within 10 lines of invariant
                return any(abs(l - invariant_line) <= 10 for l in changed_lines)
        except ValueError:
            pass
        return False

    def _violates_invariant(self, invariant: SemanticInvariant, change_desc: str) -> bool:
        """Check if a change violates the invariant"""
        # Simple keyword-based check - in production, would use AST analysis
        violation_keywords = ['remove', 'delete', 'disable', 'skip', 'bypass', 'eliminate', 'strip']
        preservation_keywords = ['add', 'assert', 'check', 'validate', 'ensure', 'strengthen', 'improve']

        lower_desc = change_desc.lower()
        lower_invariant = invariant.invariant_description.lower()

        # If removing/disabling something required by invariant, likely violation
        has_violation_action = any(kw in lower_desc for kw in violation_keywords)

        # Check if the change mentions the same concepts as the invariant
        # e.g., "null check" in both description and invariant
        invariant_concepts = set(lower_invariant.split())
        change_concepts = set(lower_desc.split())
        concept_overlap = len(invariant_concepts & change_concepts) > 0

        # It's a violation if:
        # 1. Action is removal/disable AND concepts overlap, OR
        # 2. Action is removal/disable AND invariant is about preservation (never/must/always/required)
        if has_violation_action:
            preservation_concepts = ['never', 'must', 'always', 'required', 'necessary', 'critical']
            has_preservation_emphasis = any(kw in lower_invariant for kw in preservation_concepts)

            if concept_overlap or has_preservation_emphasis:
                return True

        return False

    def _get_fix_suggestion(self, invariant: SemanticInvariant) -> str:
        """Suggest how to fix a violation"""
        return f"Ensure {invariant.invariant_description}"

    def print_status(self):
        """Print semantic checker status"""
        print("\n🔍 Semantic Invariant Checker Status")
        print("=" * 60)

        print(f"Registered Invariants: {sum(len(inv) for inv in self.invariants.values())}")
        print(f"  By Resource: {len(self.invariants)}")

        high_violations = self.get_high_severity_violations()
        if high_violations:
            print(f"\n🔴 High-Severity Violations: {len(high_violations)}")
            for v in high_violations[:3]:
                print(f"  {v['resource']}: {v['invariant']}")
                print(f"    Developer: {v['developer']}")

        if not self.violations:
            print("\n✓ No violations detected")

        print("=" * 60)


# Example semantic invariants for common patterns

def create_null_check_invariant(resource: str, variable: str) -> SemanticInvariant:
    """Create invariant that a variable is never null"""
    return SemanticInvariant(
        resource=resource,
        invariant_description=f"{variable} must never be null",
        severity="HIGH",
        code_location=f"{resource}:0",
        requires={f"null_check_{variable}"}
    )


def create_immutability_invariant(resource: str, var_name: str) -> SemanticInvariant:
    """Create invariant that a variable is immutable"""
    return SemanticInvariant(
        resource=resource,
        invariant_description=f"{var_name} must remain immutable",
        severity="MEDIUM",
        code_location=f"{resource}:0",
        requires={f"no_modification_{var_name}"}
    )


def create_api_contract_invariant(resource: str, api_version: str) -> SemanticInvariant:
    """Create invariant for API compatibility"""
    return SemanticInvariant(
        resource=resource,
        invariant_description=f"API must maintain backward compatibility for v{api_version}",
        severity="CRITICAL",
        code_location=f"{resource}:0",
        requires={"api_compatibility", f"version_{api_version}"}
    )
