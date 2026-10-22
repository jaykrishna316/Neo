"""Same-file risk: a missing region must not be classified as LOW."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.risk_classifier import RiskLevel, classify_risk  # noqa: E402


def _other(region):
    return {
        "developer_id": "alice",
        "file_path": "src/auth.py",
        "intent": "Add OAuth2 login",
        "region": region,
    }


def test_same_file_without_region_is_medium():
    result = classify_risk("bob", "src/auth.py", "Add JWT tokens", None, _other(None))
    assert result.level == RiskLevel.MEDIUM, result.reason


def test_same_file_with_one_missing_region_is_medium():
    result = classify_risk("bob", "src/auth.py", "Add JWT tokens", "lines 10-20", _other(None))
    assert result.level == RiskLevel.MEDIUM, result.reason


def test_same_file_with_distinct_regions_is_not_medium_by_missing_region():
    result = classify_risk("bob", "src/auth.py", "Add JWT tokens", "lines 100-110", _other("lines 1-5"))
    assert result.reason != "One or both developers editing entire file (no region specified)"
