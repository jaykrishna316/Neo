"""
Test Scenarios for Dual-Agent IDE Integration Testing

This package contains test fixtures and orchestration tools for validating
Neo's coordination layer with multiple IDEs (Devin vs Claude Code).

Scenarios:
1. Overlapping Regions - Same function modified by both agents
2. Signature Change - One agent changes function signature, other calls old
3. Non-Overlapping - Different functions in same file
4. Sequential Work - Activity expiry after window expires
"""

from .dual_agent_test_harness import DualAgentTestHarness

__all__ = ["DualAgentTestHarness"]
