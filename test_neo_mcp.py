#!/usr/bin/env python3
"""Test Neo MCP connectivity by checking if activity log works."""

import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import read_log, log_activity

# Check current activity log
print("📋 Current Activity Log:")
entries = read_log()
print(f"   Total entries: {len(entries)}")
for entry in entries[-3:]:  # Show last 3
    print(f"   - {entry['developer_id']}: {entry['intent'][:50]}")

# Log a test activity
print("\n📝 Logging test activity...")
entry = log_activity(
    developer_id='test-agent',
    file_path='test_file.py',
    intent='Testing Neo MCP connectivity'
)
print(f"   ✅ Logged: {entry.developer_id}")

# Verify it was written
print("\n📋 Updated Activity Log:")
entries = read_log()
print(f"   Total entries: {len(entries)}")
print(f"   Latest: {entries[-1]['developer_id']}")
