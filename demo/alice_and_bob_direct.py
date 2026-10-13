#!/usr/bin/env python3
"""
Direct Neo Coordination Demo - Alice and Bob working on same file
No MCP needed - pure Python demonstration of Neo's coordination layer
"""

import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts
import time
import json

def print_header(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")

def print_activity_log():
    """Display current activity log state"""
    entries = read_log()
    print(f"📋 ACTIVITY LOG ({len(entries)} entries):")
    print("-" * 70)
    for i, entry in enumerate(entries, 1):
        dev = entry['developer_id']
        intent = entry['intent'][:45]
        lock_state = entry.get('lock_state', 'none')
        timestamp = time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))

        lock_symbol = {
            'ACQUIRED': '🔒',
            'WAITING': '⏳',
            'PROMOTED': '✅',
            'RELEASED': '🔓'
        }.get(lock_state, '○')

        print(f"{i}. [{timestamp}] {lock_symbol} {dev:8} | {intent}")
        print(f"   Lock: {lock_state}")
    print()

def main():
    print_header("NEO DIRECT COORDINATION DEMO")
    print("Scenario: Alice and Bob working on src/auth.py\n")

    # Clear previous logs
    clear_log()
    print("✓ Activity log cleared\n")

    # ============================================================================
    # STEP 1: Alice sets intent and acquires lock
    # ============================================================================
    print_header("STEP 1: Alice Starts Working")
    print("Alice: 'I'm going to add bcrypt password hashing to src/auth.py'")
    print("       Declaring intent and acquiring lock...\n")

    alice_entry = log_activity(
        developer_id='alice',
        file_path='src/auth.py',
        intent='Add bcrypt password hashing (hash_password, verify_password functions)',
        lock_state='ACQUIRED',
        lock_scope='file',
        agent_metadata={
            'status': 'working',
            'lines_added': 0,
            'lines_removed': 0,
        }
    )

    print(f"✓ Alice acquired lock: {alice_entry.lock_state}")
    print(f"  File: {alice_entry.file_path}")
    print(f"  Intent: {alice_entry.intent}\n")

    print_activity_log()

    # ============================================================================
    # STEP 2: Alice makes code changes
    # ============================================================================
    print_header("STEP 2: Alice Makes Code Changes")
    print("Alice: 'Writing bcrypt password hashing functions...'")
    print("       (Simulating code generation)\n")

    time.sleep(1)

    alice_code = '''import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
'''

    print("Generated code:")
    print("-" * 70)
    print(alice_code)
    print("-" * 70 + "\n")

    # Update Alice's entry with completed work
    alice_completion = log_activity(
        developer_id='alice',
        file_path='src/auth.py',
        intent='Add bcrypt password hashing (COMPLETED)',
        lock_state='ACQUIRED',
        lock_scope='file',
        agent_metadata={
            'status': 'completed',
            'lines_added': 14,
            'lines_removed': 0,
            'tokens_used': 487,
        }
    )

    print(f"✓ Alice completed her changes")
    print(f"  Lines added: 14")
    print(f"  Tokens used: 487\n")

    print_activity_log()

    time.sleep(1)

    # ============================================================================
    # STEP 3: Bob wants to work on the same file
    # ============================================================================
    print_header("STEP 3: Bob Wants to Work on Same File")
    print("Bob: 'I want to add JWT token support to src/auth.py'")
    print("     Checking for conflicts with Neo...\n")

    risk, msg, lock_info = check_for_conflicts(
        agent_id='bob',
        file_path='src/auth.py',
        intent='Add JWT token support (create_token, verify_token functions)'
    )

    print(f"🔍 Neo's Conflict Check Result:")
    print(f"   Risk Level: {risk}")
    print(f"   Message: {msg}\n")

    if lock_info:
        print(f"   Lock Holder: {lock_info.get('lock_holder')}")
        print(f"   Lock State: {lock_info.get('lock_state')}")
        print()

    # Log Bob's intent (queued behind Alice)
    bob_entry = log_activity(
        developer_id='bob',
        file_path='src/auth.py',
        intent='Add JWT token support (create_token, verify_token functions)',
        lock_state='WAITING',
        waiting_for='alice',
        queue_position=0,
        agent_metadata={
            'status': 'waiting',
            'lines_added': 0,
            'lines_removed': 0,
        }
    )

    print(f"✓ Bob's intent logged (queued)")
    print(f"  Lock State: {bob_entry.lock_state}")
    print(f"  Waiting For: {bob_entry.waiting_for}")
    print(f"  Queue Position: {bob_entry.queue_position}\n")

    print_activity_log()

    # ============================================================================
    # STEP 4: Alice releases lock
    # ============================================================================
    print_header("STEP 4: Alice Releases Lock")
    print("Alice: 'Done with my changes. Releasing lock for next developer...'\n")

    alice_release = log_activity(
        developer_id='alice',
        file_path='src/auth.py',
        intent='RELEASED lock on src/auth.py',
        lock_state='RELEASED',
        agent_metadata={
            'status': 'completed',
            'lines_added': 14,
            'lines_removed': 0,
        }
    )

    print(f"✓ Alice released lock\n")

    print_activity_log()

    time.sleep(1)

    # ============================================================================
    # STEP 5: Bob gets promoted to lock holder
    # ============================================================================
    print_header("STEP 5: Bob Gets Promoted to Lock Holder")
    print("Neo: 'Bob was waiting. Promoting to lock holder...'")
    print("     Bob can now proceed with code generation.\n")

    bob_promoted = log_activity(
        developer_id='bob',
        file_path='src/auth.py',
        intent='Add JWT token support (NOW ACTIVE - lock acquired)',
        lock_state='ACQUIRED',
        lock_acquired_at=time.time(),
        agent_metadata={
            'status': 'working',
            'lines_added': 0,
            'lines_removed': 0,
        }
    )

    print(f"✓ Bob promoted to lock holder")
    print(f"  Lock State: {bob_promoted.lock_state}\n")

    print_activity_log()

    time.sleep(1)

    # ============================================================================
    # STEP 6: Bob makes his code changes
    # ============================================================================
    print_header("STEP 6: Bob Makes Code Changes")
    print("Bob: 'Now adding JWT support on top of Alice's password hashing...'")
    print("     (Simulating code generation)\n")

    bob_code = '''from datetime import datetime, timedelta
import jwt

SECRET_KEY = "your-secret-key"

def create_token(user_id: str, expires_in_hours: int = 24) -> str:
    """Create a JWT token for a user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
'''

    print("Generated code:")
    print("-" * 70)
    print(bob_code)
    print("-" * 70 + "\n")

    bob_completion = log_activity(
        developer_id='bob',
        file_path='src/auth.py',
        intent='Add JWT token support (COMPLETED)',
        lock_state='ACQUIRED',
        lock_scope='file',
        agent_metadata={
            'status': 'completed',
            'lines_added': 22,
            'lines_removed': 0,
            'tokens_used': 612,
        }
    )

    print(f"✓ Bob completed his changes")
    print(f"  Lines added: 22")
    print(f"  Tokens used: 612\n")

    print_activity_log()

    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print_header("FINAL RESULT")

    entries = read_log()
    completed = [e for e in entries if (e.get('agent_metadata') or {}).get('status') == 'completed']

    print(f"✅ Both developers completed their work without conflicts!")
    print(f"   - Total entries in activity log: {len(entries)}")
    print(f"   - Completed tasks: {len(completed)}")
    print(f"   - Total lines added: {sum((e.get('agent_metadata') or {}).get('lines_added', 0) for e in completed)}")
    print(f"   - Total tokens used: {sum((e.get('agent_metadata') or {}).get('tokens_used', 0) for e in completed)}")
    print()

    print("📁 Final merged code would include:")
    print("   1. Alice's: bcrypt password hashing (hash_password, verify_password)")
    print("   2. Bob's:   JWT token support (create_token, verify_token)")
    print()

    print("🎯 Key Points:")
    print("   ✓ Zero Git merge conflicts (coordinated at semantic layer)")
    print("   ✓ No wasted token generations (conflicts detected early)")
    print("   ✓ Clear activity log of who worked on what")
    print("   ✓ Lock state machine enabled queuing and promotion")
    print()

if __name__ == '__main__':
    main()
