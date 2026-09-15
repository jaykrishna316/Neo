"""
Scenario 4: Sequential Work with Activity Expiry
Devin completes work, Claude Code checks later (after expiry window)
Expected: LOW risk (activity expired from log)
"""


def operation_one(x: int) -> int:
    """
    First operation.

    Region: lines 8-15
    Devin modifies this first (T+0s).
    After Devin completes, activity log entry has 30-minute window.

    If Claude Code checks at T+35min (beyond window):
    - Entry should be expired/removed from log
    - No conflict detected (LOW risk)
    """
    return x * 2


def operation_two(x: int) -> int:
    """
    Second operation.

    Region: lines 20-27
    Claude Code modifies this later (T+35min+).
    Since operation_one activity expired, no conflict.

    Expected: LOW risk (expiry validated)
    """
    return x + 10


class SequentialProcessor:
    """Processor for sequential operations"""

    def process_sequential(self, value: int) -> int:
        """
        Process value through sequential operations.

        Simulates:
        - T+0s: Devin modifies operation_one()
        - T+5s: Devin completes
        - T+35min: Claude Code checks and modifies operation_two()
        - Result: No conflict (activity expired after 30min)
        """
        result = operation_one(value)
        result = operation_two(result)
        return result

    def log_activity_timestamp(self) -> str:
        """Get current activity log timestamp"""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S")
