#!/usr/bin/env python3
"""
Neo System Validation Script
Checks that all components are in place and ready for testing
"""

import os
import sys
import json
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark():
    return f"{GREEN}✓{RESET}"

def x_mark():
    return f"{RED}✗{RESET}"

def print_header(title):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def check_file_exists(path, description):
    """Check if a file exists"""
    full_path = Path(path)
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"{check_mark()} {description}: {path} ({size:,} bytes)")
        return True
    else:
        print(f"{x_mark()} {description}: {path} NOT FOUND")
        return False

def check_file_content(path, search_string, description):
    """Check if file contains expected content"""
    try:
        with open(path, 'r') as f:
            content = f.read()
            if search_string in content:
                print(f"{check_mark()} {description}")
                return True
            else:
                print(f"{x_mark()} {description} - content not found")
                return False
    except Exception as e:
        print(f"{x_mark()} {description} - error: {e}")
        return False

def validate_system():
    """Run all validation checks"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}NEO COLLABORATIVE WORKFLOW SYSTEM - VALIDATION{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    all_passed = True

    # Check core system files
    print_header("Core System Files")
    checks = [
        ("activity_log_server.py", ".claude/activity_log_server.py", "Activity Log Server"),
        ("workflow_state_machine.py", ".claude/workflow_state_machine.py", "Workflow State Machine"),
        ("notification_manager.py", ".claude/notification_manager.py", "Notification Manager"),
        ("activity_log_client.py", ".claude/activity_log_client.py", "Activity Log Client"),
    ]

    for _, path, desc in checks:
        if not check_file_exists(path, desc):
            all_passed = False

    # Check test files
    print_header("Test Scripts")
    test_checks = [
        ("test_actual_file_editing.py", ".claude/test_actual_file_editing.py", "Lock Mechanism Test"),
        ("test_complete_end_to_end.py", ".claude/test_complete_end_to_end.py", "End-to-End Test"),
        ("test_agent_vs_human.py", ".claude/test_agent_vs_human.py", "Agent vs Human Test"),
        ("test_complete_workflow.py", ".claude/test_complete_workflow.py", "Complete Workflow Test"),
        ("test2devs.py", "test2devs.py", "Shared Test File (2 Devs)"),
    ]

    for _, path, desc in test_checks:
        if not check_file_exists(path, desc):
            all_passed = False

    # Check documentation files
    print_header("Documentation")
    doc_checks = [
        ("README.md", ".claude/README.md", "Main README"),
        ("SYSTEM_SUMMARY.md", ".claude/SYSTEM_SUMMARY.md", "System Summary"),
        ("COMPLETE_WORKFLOW_GUIDE.md", ".claude/COMPLETE_WORKFLOW_GUIDE.md", "Complete Workflow Guide"),
        ("AGENT_VS_HUMAN_GUIDE.md", ".claude/AGENT_VS_HUMAN_GUIDE.md", "Agent vs Human Guide"),
        ("TEST_WITH_CLAUDE.md", ".claude/TEST_WITH_CLAUDE.md", "Testing with Claude Guide"),
        ("REAL_2DEV_TESTING_GUIDE.md", ".claude/REAL_2DEV_TESTING_GUIDE.md", "Real 2-Dev Testing Guide"),
    ]

    for _, path, desc in doc_checks:
        if not check_file_exists(path, desc):
            all_passed = False

    # Check key features
    print_header("Key Features")
    feature_checks = [
        (".claude/activity_log_server.py", "from workflow_state_machine import", "Workflow State Machine Integration"),
        (".claude/activity_log_server.py", "def start_editing", "Lock-Based Conflict Prevention"),
        (".claude/activity_log_server.py", "/api/start_editing", "REST API Endpoints"),
        (".claude/activity_log_server.py", "def register_developer", "Developer Registration"),
        (".claude/activity_log_server.py", "all_approvers", "Auto-Approver Assignment"),
    ]

    for path, search, desc in feature_checks:
        if not check_file_content(path, search, desc):
            all_passed = False

    # Summary
    print_header("Validation Summary")

    if all_passed:
        print(f"{GREEN}✓ All system components validated successfully!{RESET}\n")
        print(f"{BLUE}Next Steps:{RESET}")
        print(f"  1. Start activity log server:")
        print(f"     python3 .claude/activity_log_server.py")
        print(f"\n  2. Run a test (in another terminal):")
        print(f"     python3 .claude/test_complete_end_to_end.py")
        print(f"\n  3. For 2-developer testing with real git:")
        print(f"     Read .claude/REAL_2DEV_TESTING_GUIDE.md")
        return 0
    else:
        print(f"{RED}✗ Some validation checks failed{RESET}\n")
        print(f"Please check the output above and ensure all files are in place.")
        return 1

if __name__ == "__main__":
    sys.exit(validate_system())
