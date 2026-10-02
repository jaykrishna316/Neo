"""Developer pattern learning for smarter conflict detection.

Tracks how long developers typically take for different types of changes,
enabling better wait time estimation and conflict resolution.
"""

import json
import statistics
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict


PATTERNS_FILE = Path(".devsync/developer-patterns.json")


@dataclass
class CompletionRecord:
    """Record of a developer completing a change."""
    developer_id: str
    intent_category: str  # feature/bugfix/refactor/chore/test/docs
    duration_seconds: int
    timestamp: float


def ensure_patterns_file():
    """Ensure patterns file exists."""
    PATTERNS_FILE.parent.mkdir(exist_ok=True)
    if not PATTERNS_FILE.exists():
        PATTERNS_FILE.write_text(json.dumps({}))


def record_completion(
    developer_id: str,
    intent_category: str,
    duration_seconds: int
) -> None:
    """
    Record that a developer completed a change.

    Args:
        developer_id: Developer identifier
        intent_category: Type of change (feature/bugfix/refactor/etc)
        duration_seconds: How long it took
    """
    ensure_patterns_file()

    patterns = json.loads(PATTERNS_FILE.read_text())
    key = f"{developer_id}:{intent_category}"

    if key not in patterns:
        patterns[key] = []

    patterns[key].append({
        "duration": duration_seconds,
        "timestamp": __import__("time").time()
    })

    # Keep only last 50 records per developer/category (limit file size)
    if len(patterns[key]) > 50:
        patterns[key] = patterns[key][-50:]

    PATTERNS_FILE.write_text(json.dumps(patterns, indent=2))


def estimate_completion_time(
    developer_id: str,
    intent_category: str,
    default_seconds: int = 1800
) -> int:
    """
    Estimate how long a developer typically takes for a change type.

    Args:
        developer_id: Developer identifier
        intent_category: Type of change
        default_seconds: Default if no history (default 30 min)

    Returns:
        Estimated seconds to completion
    """
    ensure_patterns_file()

    patterns = json.loads(PATTERNS_FILE.read_text())
    key = f"{developer_id}:{intent_category}"

    if key not in patterns or not patterns[key]:
        return default_seconds

    durations = [r["duration"] for r in patterns[key]]

    if not durations:
        return default_seconds

    # Use median to avoid outliers
    return int(statistics.median(durations))


def get_developer_stats(developer_id: str) -> Dict[str, Dict]:
    """
    Get completion statistics for a developer.

    Args:
        developer_id: Developer identifier

    Returns:
        Dict mapping intent_category to stats (median, min, max, count)
    """
    ensure_patterns_file()

    patterns = json.loads(PATTERNS_FILE.read_text())
    stats = {}

    for key, records in patterns.items():
        dev_id, category = key.split(":", 1)
        if dev_id != developer_id:
            continue

        durations = [r["duration"] for r in records]
        if durations:
            stats[category] = {
                "median": int(statistics.median(durations)),
                "min": min(durations),
                "max": max(durations),
                "count": len(durations),
                "avg": int(statistics.mean(durations))
            }

    return stats


def get_all_patterns() -> Dict[str, List[Dict]]:
    """Get all recorded patterns."""
    ensure_patterns_file()
    return json.loads(PATTERNS_FILE.read_text())


def clear_patterns() -> None:
    """Clear all patterns (for testing)."""
    ensure_patterns_file()
    PATTERNS_FILE.write_text(json.dumps({}))


if __name__ == "__main__":
    print("Developer Pattern Learning")
    print("=" * 60)

    # Example usage
    record_completion("alice", "feature", 1800)  # 30 min
    record_completion("alice", "feature", 1950)  # 32.5 min
    record_completion("alice", "feature", 1650)  # 27.5 min

    record_completion("bob", "bugfix", 600)      # 10 min
    record_completion("bob", "bugfix", 720)      # 12 min

    print("\nAlice's feature estimates:")
    estimate = estimate_completion_time("alice", "feature")
    print(f"  Estimated time: {estimate}s ({estimate//60}m {estimate%60}s)")

    print("\nAlice's stats:")
    stats = get_developer_stats("alice")
    for category, data in stats.items():
        print(f"  {category}: median={data['median']}s, range={data['min']}-{data['max']}s")

    print("\nBob's bugfix estimate:")
    estimate = estimate_completion_time("bob", "bugfix")
    print(f"  Estimated time: {estimate}s ({estimate//60}m {estimate%60}s)")

    print("\nAll patterns:")
    patterns = get_all_patterns()
    for key, records in patterns.items():
        print(f"  {key}: {len(records)} records")
