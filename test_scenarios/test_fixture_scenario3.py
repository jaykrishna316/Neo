"""
Scenario 3: Non-Overlapping Regions
Both agents modify same file but different functions
Expected: LOW risk (no conflict)
"""


def helper_a(data: list) -> int:
    """
    Helper function A.

    Region: lines 8-18
    Devin will add implementation here.
    Claude Code will NOT touch this region.

    Expected: No conflict
    """
    total = 0
    for item in data:
        total += item
    return total


def helper_b(data: list) -> list:
    """
    Helper function B.

    Region: lines 25-35
    Claude Code will add implementation here.
    Devin will NOT touch this region.

    Expected: No conflict, both can work simultaneously
    """
    return sorted(data)


class Service:
    """Service that uses both helpers"""

    def process(self, data: list) -> dict:
        """
        Process data using both helpers.

        This function calls both helper_a() and helper_b().
        If they are modified in non-overlapping regions,
        this should still work correctly.

        Expected: LOW risk (separate functions, no overlap)
        """
        sum_result = helper_a(data)
        sorted_result = helper_b(data)

        return {
            "sum": sum_result,
            "sorted": sorted_result,
            "count": len(data)
        }

    def validate(self, data: list) -> bool:
        """Validate input data"""
        return isinstance(data, list) and len(data) > 0
