"""Git integration for real conflict detection from staged changes.

Analyzes actual git staged changes (diffs) to detect real function-level
conflicts instead of relying on line-range heuristics.
"""

import re
import subprocess
from typing import List, Set, Optional, Tuple
from pathlib import Path


def get_staged_diff(file_path: str) -> Optional[str]:
    """
    Get staged changes for a file using git diff --cached.

    Args:
        file_path: Path to file to check

    Returns:
        Diff text or None if file not staged
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", file_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def parse_functions_from_diff(diff_text: str) -> Set[str]:
    """
    Parse function names from a git diff.

    Extracts function definitions that appear in the diff using basic regex.
    Works for Python, JavaScript, Java, C, etc.

    Args:
        diff_text: Output from git diff

    Returns:
        Set of function names that changed
    """
    if not diff_text:
        return set()

    functions = set()

    # Pattern matches function definitions in various languages
    patterns = [
        r'^\+\s*def\s+(\w+)\s*\(',           # Python: def func_name(
        r'^\+\s*function\s+(\w+)\s*\(',       # JavaScript: function func_name(
        r'^\+\s*async\s+function\s+(\w+)\s*\(', # Async JS: async function func_name(
        r'^\+\s*async\s+def\s+(\w+)\s*\(',   # Async Python: async def func_name(
        r'^\+\s*public\s+\w+\s+(\w+)\s*\(',   # Java/C: public type func_name(
        r'^\+\s*private\s+\w+\s+(\w+)\s*\(',  # Java/C: private type func_name(
        r'^\+\s*\w+\s+(\w+)\s*\(',             # Generic: type func_name(
    ]

    for line in diff_text.split('\n'):
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                func_name = match.group(1)
                functions.add(func_name)
                break

    return functions


def parse_functions_from_region(region: str) -> Set[str]:
    """
    Extract function names from a region string.

    Handles formats like:
    - "login_user (lines 20-40)"
    - "login_user"
    - "MyClass.method_name"

    Args:
        region: Region description from activity log

    Returns:
        Set of function/method names
    """
    if not region:
        return set()

    functions = set()

    # Remove line numbers
    clean_region = re.sub(r'\s*\(lines\s+\d+-\d+\)', '', region)
    clean_region = re.sub(r'\s*\(.*?\)', '', clean_region)

    # Split on dots (for class methods)
    parts = clean_region.split('.')

    # Add all parts as potential function names
    for part in parts:
        part = part.strip()
        if part and re.match(r'^\w+$', part):
            functions.add(part)

    return functions


def detect_real_conflicts(file_path: str, active_entries: List[dict]) -> bool:
    """
    Detect real conflicts by comparing staged changes with active entries.

    This is more accurate than line-range heuristics because it uses
    actual git diff to see which functions are being modified.

    Args:
        file_path: File to check
        active_entries: List of active activity entries for this file

    Returns:
        True if real conflicts detected, False otherwise
    """
    # Get actual staged changes
    staged_diff = get_staged_diff(file_path)
    if not staged_diff:
        return False

    # Extract functions being changed in staging
    staged_functions = parse_functions_from_diff(staged_diff)
    if not staged_functions:
        return False

    # Check if anyone else is working on the same functions
    for entry in active_entries:
        if entry["developer_id"] == "self":  # Skip self
            continue

        entry_functions = parse_functions_from_region(entry.get("region", ""))

        # Check for overlap
        overlap = staged_functions.intersection(entry_functions)
        if overlap:
            return True

    return False


def get_changed_functions(file_path: str) -> Set[str]:
    """
    Get all functions modified in staged changes.

    Args:
        file_path: File to analyze

    Returns:
        Set of function names being modified
    """
    diff = get_staged_diff(file_path)
    if not diff:
        return set()

    return parse_functions_from_diff(diff)


def get_affected_files() -> Set[str]:
    """
    Get all files with staged changes.

    Returns:
        Set of file paths with staged changes
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return set(f.strip() for f in result.stdout.strip().split('\n') if f.strip())
        return set()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return set()


if __name__ == "__main__":
    print("Git Integration - Real Conflict Detection")
    print("=" * 60)

    # Test with actual staged changes
    staged_files = get_affected_files()
    if staged_files:
        print(f"\n📝 Files with staged changes:")
        for file_path in list(staged_files)[:5]:
            print(f"  - {file_path}")

            functions = get_changed_functions(file_path)
            if functions:
                print(f"    Functions changed: {', '.join(sorted(functions))}")
    else:
        print("\n(No staged changes to analyze)")

    # Test parsing
    print("\n🔍 Testing function parsing:")

    test_regions = [
        "login_user (lines 20-40)",
        "MyClass.method_name",
        "authenticate",
        "process_payment (lines 50-100)"
    ]

    for region in test_regions:
        functions = parse_functions_from_region(region)
        print(f"  '{region}' → {functions}")

    print("\n✅ Git integration ready")
