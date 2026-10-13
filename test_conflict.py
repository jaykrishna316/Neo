#!/usr/bin/env python3
"""Test Neo conflict detection."""

import sys
sys.path.insert(0, '/home/user/Neo')

from core.pre_gen_check import check_for_conflicts
from core.activity_log import log_activity

# Simulate Agent A starting work
print("Agent A wants to work on auth.py...")
log_activity(
    developer_id='agent-a',
    file_path='src/auth.py',
    intent='Add OAuth2 support',
    lock_state='ACQUIRED'
)

# Simulate Agent B trying to work on same file
print("Agent B wants to work on same file...")
risk_level, message, lock_info = check_for_conflicts(
    agent_id='agent-b',
    file_path='src/auth.py',
    intent='Add JWT tokens'
)

print(f"\n🔍 Conflict Check Result:")
print(f"   Risk Level: {risk_level}")
print(f"   Message: {message}")
if lock_info:
    print(f"   Lock Holder: {lock_info.get('lock_holder')}")
    print(f"   Lock State: {lock_info.get('lock_state')}")
