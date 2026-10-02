"""
Neo MVP Validation Test Scenarios
100 realistic conflict scenarios for testing coordination
"""

from typing import List, Dict, Any


def generate_scenarios() -> List[Dict[str, Any]]:
    """Generate 100 realistic multi-agent code conflict scenarios"""

    scenarios = []

    # Pattern 1: Overlapping function edits (40 scenarios)
    for i in range(10):
        scenarios.append({
            "id": f"overlap-func-{i}",
            "file": f"src/module_{i}.py",
            "intent_a": "Refactor login() function for better error handling",
            "intent_b": "Add OAuth2 support to login() function",
            "overlap_region": "lines 20-50 (login function body)",
            "conflict_type": "overlapping_function",
            "expected": "CONFLICT",
            "severity": "HIGH"
        })

    for i in range(10):
        scenarios.append({
            "id": f"overlap-class-{i}",
            "file": f"src/models/user_{i}.py",
            "intent_a": "Add email validation to User class",
            "intent_b": "Add phone validation to User class",
            "overlap_region": "lines 10-30 (User __init__ method)",
            "conflict_type": "overlapping_class_method",
            "expected": "CONFLICT",
            "severity": "HIGH"
        })

    for i in range(10):
        scenarios.append({
            "id": f"overlap-import-{i}",
            "file": f"src/app_{i}.py",
            "intent_a": "Import FastAPI and add /health endpoint",
            "intent_b": "Import Pydantic and add data validation",
            "overlap_region": "lines 1-10 (imports + setup)",
            "conflict_type": "overlapping_imports",
            "expected": "CONFLICT",
            "severity": "MEDIUM"
        })

    for i in range(10):
        scenarios.append({
            "id": f"overlap-config-{i}",
            "file": f"config/settings_{i}.json",
            "intent_a": "Add database connection settings",
            "intent_b": "Add cache configuration",
            "overlap_region": "root level JSON object",
            "conflict_type": "overlapping_json_keys",
            "expected": "CONFLICT",
            "severity": "HIGH"
        })

    # Pattern 2: Adjacent but non-overlapping (30 scenarios)
    for i in range(10):
        scenarios.append({
            "id": f"adjacent-func-{i}",
            "file": f"src/utils_{i}.py",
            "intent_a": "Add helper_a() function at line 50-60",
            "intent_b": "Add helper_b() function at line 65-75",
            "overlap_region": "none (separate functions)",
            "conflict_type": "adjacent_functions",
            "expected": "NO_CONFLICT",
            "severity": "LOW"
        })

    for i in range(10):
        scenarios.append({
            "id": f"adjacent-import-{i}",
            "file": f"src/handlers/api_{i}.py",
            "intent_a": "Add import logging at line 1",
            "intent_b": "Add import typing at line 2",
            "overlap_region": "none (different imports)",
            "conflict_type": "adjacent_imports",
            "expected": "NO_CONFLICT",
            "severity": "LOW"
        })

    for i in range(10):
        scenarios.append({
            "id": f"adjacent-method-{i}",
            "file": f"src/db/models_{i}.py",
            "intent_a": "Add save_user() method at line 100-120",
            "intent_b": "Add delete_user() method at line 125-135",
            "overlap_region": "none (separate methods)",
            "conflict_type": "adjacent_methods",
            "expected": "NO_CONFLICT",
            "severity": "LOW"
        })

    # Pattern 3: Same file, different components (20 scenarios)
    for i in range(10):
        scenarios.append({
            "id": f"diff-comp-{i}",
            "file": f"src/main_{i}.py",
            "intent_a": "Add logging setup in __main__ block",
            "intent_b": "Add error handling in separate function",
            "overlap_region": "same file, different logical components",
            "conflict_type": "same_file_diff_components",
            "expected": "NO_CONFLICT",
            "severity": "LOW"
        })

    for i in range(10):
        scenarios.append({
            "id": f"class-field-{i}",
            "file": f"src/entity_{i}.py",
            "intent_a": "Add field 'email: str' to class",
            "intent_b": "Add field 'phone: str' to class",
            "overlap_region": "same class, different fields",
            "conflict_type": "same_class_diff_fields",
            "expected": "NO_CONFLICT",
            "severity": "MEDIUM"
        })

    # Pattern 4: Cross-file dependencies (10 scenarios)
    for i in range(10):
        scenarios.append({
            "id": f"cross-file-{i}",
            "file": f"src/utils/validation_{i}.py",
            "intent_a": "Modify validate_email() function signature",
            "intent_b": "Modify validate_phone() in different file",
            "overlap_region": "different files, no direct overlap",
            "conflict_type": "cross_file_semantic",
            "expected": "NO_CONFLICT",
            "severity": "MEDIUM"
        })

    return scenarios


def get_scenario(scenario_id: str) -> Dict[str, Any]:
    """Get a specific scenario by ID"""
    for scenario in generate_scenarios():
        if scenario["id"] == scenario_id:
            return scenario
    return None


def scenarios_by_type(conflict_type: str) -> List[Dict[str, Any]]:
    """Get all scenarios of a specific type"""
    return [s for s in generate_scenarios() if s["conflict_type"] == conflict_type]


def scenarios_by_severity(severity: str) -> List[Dict[str, Any]]:
    """Get all scenarios of a specific severity"""
    return [s for s in generate_scenarios() if s["severity"] == severity]


if __name__ == "__main__":
    scenarios = generate_scenarios()
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Expected conflicts: {sum(1 for s in scenarios if s['expected'] == 'CONFLICT')}")
    print(f"Expected no conflicts: {sum(1 for s in scenarios if s['expected'] == 'NO_CONFLICT')}")
    print(f"\nBy severity:")
    print(f"  HIGH: {sum(1 for s in scenarios if s['severity'] == 'HIGH')}")
    print(f"  MEDIUM: {sum(1 for s in scenarios if s['severity'] == 'MEDIUM')}")
    print(f"  LOW: {sum(1 for s in scenarios if s['severity'] == 'LOW')}")
