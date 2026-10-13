#!/usr/bin/env python3
"""Test single developer workflow via Neo MCP:
1. View current activity log
2. Developer declares intent
3. Check for conflicts (via MCP)
4. Log activity (via MCP)
5. Show updated activity log
"""

import sys
import time
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import read_log, log_activity
from core.pre_gen_check import check_for_conflicts

def print_header(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")

def print_activity_log(title="ACTIVITY LOG"):
    entries = read_log()
    print(f"📋 {title} ({len(entries)} entries):")
    print("-" * 70)
    for i, entry in enumerate(entries[-5:], 1):  # Show last 5
        dev = entry['developer_id']
        intent = entry['intent'][:50]
        timestamp = time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))
        lock_state = entry.get('lock_state', 'none')
        lock_symbol = {
            'ACQUIRED': '🔒',
            'WAITING': '⏳',
            'PROMOTED': '✅',
            'RELEASED': '🔓',
            'none': '○'
        }.get(lock_state, '○')

        print(f"{i}. [{timestamp}] {lock_symbol} {dev:12} | {intent}")
        if lock_state not in ['none', None]:
            print(f"   Lock: {lock_state}")
    print()

def main():
    print_header("NEO MCP: SINGLE DEVELOPER TEST")

    # ============================================================================
    # STEP 1: Show current activity log
    # ============================================================================
    print_header("STEP 1: Current Activity Log")
    print_activity_log()

    # ============================================================================
    # STEP 2: Developer declares intent
    # ============================================================================
    print_header("STEP 2: Developer Declares Intent")
    developer_id = 'claude-dev-1'
    file_path = 'src/utils.py'
    intent = 'Add utility functions for data validation'

    print(f"Developer: {developer_id}")
    print(f"File: {file_path}")
    print(f"Intent: {intent}\n")

    # ============================================================================
    # STEP 3: Check for conflicts (MCP call simulation)
    # ============================================================================
    print_header("STEP 3: Check for Conflicts via MCP")
    print(f"Calling: neo_check_conflicts()")
    print(f"  agent_id: {developer_id}")
    print(f"  file_path: {file_path}")
    print(f"  intent: {intent}\n")

    risk_level, message, lock_info = check_for_conflicts(
        agent_id=developer_id,
        file_path=file_path,
        intent=intent
    )

    risk_symbol = '✅' if str(risk_level) == 'RiskLevel.LOW' else '⚠️' if 'MEDIUM' in str(risk_level) else '🚫'
    print(f"{risk_symbol} Conflict Check Result:")
    print(f"   Risk Level: {risk_level}")
    print(f"   Message: {message}\n")

    # ============================================================================
    # STEP 4: Log activity (MCP call simulation)
    # ============================================================================
    print_header("STEP 4: Log Activity via MCP")
    print(f"Calling: neo_log_activity()")
    print(f"  agent_id: {developer_id}")
    print(f"  file_path: {file_path}")
    print(f"  intent: {intent}\n")

    entry = log_activity(
        developer_id=developer_id,
        file_path=file_path,
        intent=intent,
        lock_state='ACQUIRED',
        agent_metadata={
            'status': 'working',
            'lines_added': 0,
            'lines_removed': 0,
        }
    )

    print(f"✅ Activity logged")
    print(f"   Developer: {entry.developer_id}")
    print(f"   File: {entry.file_path}")
    print(f"   Lock State: {entry.lock_state}\n")

    # Simulate code generation
    time.sleep(0.5)

    # ============================================================================
    # STEP 5: Log code completion
    # ============================================================================
    print_header("STEP 5: Developer Completes Work")
    print(f"Generating code for {file_path}...\n")

    code = '''def validate_email(email: str) -> bool:
    """Validate email format."""
    return '@' in email and '.' in email

def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    return len(phone) >= 10
'''

    print("Generated code:")
    print("-" * 70)
    print(code)
    print("-" * 70 + "\n")

    completion_entry = log_activity(
        developer_id=developer_id,
        file_path=file_path,
        intent=intent + ' (COMPLETED)',
        lock_state='ACQUIRED',
        agent_metadata={
            'status': 'completed',
            'lines_added': 7,
            'lines_removed': 0,
            'tokens_used': 234,
        }
    )

    print(f"✅ Work completed")
    print(f"   Lines added: 7")
    print(f"   Tokens used: 234\n")

    # ============================================================================
    # STEP 6: Release lock
    # ============================================================================
    print_header("STEP 6: Developer Releases Lock")

    release_entry = log_activity(
        developer_id=developer_id,
        file_path=file_path,
        intent='Released lock after completing utility functions',
        lock_state='RELEASED',
        agent_metadata={
            'status': 'completed',
            'lines_added': 7,
            'lines_removed': 0,
        }
    )

    print(f"✅ Lock released\n")

    # ============================================================================
    # FINAL: Show updated activity log
    # ============================================================================
    print_header("FINAL: Updated Activity Log")
    print_activity_log("ACTIVITY LOG (after single developer workflow)")

    entries = read_log()
    print("📊 Summary:")
    print(f"   Total entries: {len(entries)}")
    print(f"   Latest developer: {entries[-1]['developer_id']}")
    print(f"   Latest lock state: {entries[-1].get('lock_state', 'none')}")
    print()

if __name__ == '__main__':
    main()
