#!/usr/bin/env python3
"""Test script to verify Neo pre-generation checks work.

Run this to simulate what the hooks should do:
  python3 test_neo_hooks.py <file_path>
"""

import sys
import os

sys.path.insert(0, '.')

from core.activity_log import get_active_entries
from core.freshness import check_freshness


def test_pre_gen_check(file_path: str):
    """Test pre-generation conflict check."""
    print("\n" + "="*70)
    print("🔍 NEO PRE-GENERATION CHECK")
    print("="*70)

    # Get active developers on this file
    active = get_active_entries(file_path=file_path, expiry_minutes=30)

    if active:
        print(f"\n⚠️  CONFLICT WARNING: {len(active)} developer(s) on {file_path}")
        for e in active:
            intent = e.get("intent", "N/A")[:70]
            dev_id = e["developer_id"]
            print(f"   • {dev_id}: {intent}")
    else:
        print(f"\n✅ No conflicts detected on {file_path}")

    # Check context freshness
    status = check_freshness('claude-code', file_path)
    print(f"\n🔄 Context Status: {status}")
    print("="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_neo_hooks.py <file_path>")
        print("\nExample: python3 test_neo_hooks.py core/activity_log.py")
        sys.exit(1)

    file_path = sys.argv[1]
    test_pre_gen_check(file_path)
