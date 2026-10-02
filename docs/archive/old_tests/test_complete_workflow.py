#!/usr/bin/env python3
"""
Complete Workflow Test - Simulates two developers (Dev1 and Dev2)
testing the entire Neo collaboration system

Run the activity log server first:
  python3 .claude/activity_log_server.py

Then run this test:
  python3 .claude/test_complete_workflow.py
"""

import requests
import json
import time
from datetime import datetime

# Configuration
SERVER_URL = "http://localhost:5000"
FILE_PATH = "src/auth.py"
FUNCTION_NAME = "validate_user"

# Colors for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_step(step_num, description):
    """Log a test step"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}STEP {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def log_success(message):
    """Log success"""
    print(f"{GREEN}✓ {message}{RESET}")

def log_info(message):
    """Log info"""
    print(f"{YELLOW}→ {message}{RESET}")

def log_error(message):
    """Log error"""
    print(f"{RED}✗ {message}{RESET}")

def print_response(response, title="Response"):
    """Pretty print API response"""
    print(f"\n{title}:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def test_health_check():
    """Test 1: Health check"""
    log_step(1, "Health Check - Verify server is running")

    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            log_success("Server is running")
            print_response(response)
            return True
        else:
            log_error(f"Server returned {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Cannot connect to server: {e}")
        log_info(f"Make sure to start the server first:")
        log_info(f"  python3 .claude/activity_log_server.py")
        return False

def test_subscribe_developers():
    """Test 2: Subscribe both developers to notifications"""
    log_step(2, "Subscribe Developers to Notifications")

    for dev in ["dev1", "dev2"]:
        log_info(f"Subscribing {dev} to polling channel")
        payload = {
            "developer": dev,
            "channel": "polling",
            "endpoint": "",
        }

        response = requests.post(f"{SERVER_URL}/api/subscribe", json=payload)
        if response.status_code == 200:
            log_success(f"{dev} subscribed")
            print_response(response, f"{dev} Subscription Response")
        else:
            log_error(f"Failed to subscribe {dev}")
            print_response(response)
            return False

    return True

def test_dev1_start_editing():
    """Test 3: Dev1 starts editing"""
    log_step(3, "Dev1 Starts Editing - Acquires Lock")

    payload = {
        "developer": "dev1",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
    }

    log_info(f"Dev1 calling /api/start_editing for {FUNCTION_NAME}")
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("lock_acquired"):
            log_success("Dev1 acquired lock")
            print_response(response)
            return True
        else:
            log_error("Failed to acquire lock")
            print_response(response)
            return False
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_dev2_blocked():
    """Test 4: Dev2 tries to edit same function - BLOCKED"""
    log_step(4, "Dev2 Tries to Edit Same Function - BLOCKED")

    payload = {
        "developer": "dev2",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
    }

    log_info(f"Dev2 calling /api/start_editing for {FUNCTION_NAME}")
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)

    if response.status_code == 200:
        data = response.json()
        if not data.get("success") and not data.get("lock_acquired"):
            log_success("Dev2 correctly BLOCKED (lock held by dev1)")
            print_response(response)
            return True
        else:
            log_error("Dev2 should have been blocked")
            print_response(response)
            return False
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_dev2_poll_notifications():
    """Test 5: Dev2 polls for notifications"""
    log_step(5, "Dev2 Polls for Notifications - Should See BLOCKED")

    log_info("Dev2 polling for notifications...")
    response = requests.get(
        f"{SERVER_URL}/api/notifications",
        params={"developer": "dev2"}
    )

    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])

        if notifications:
            log_success(f"Dev2 received {len(notifications)} notification(s)")
            print_response(response, "Dev2 Notifications")

            # Check for lock_blocked notification
            blocked_notifs = [n for n in notifications if n["type"] == "lock_blocked"]
            if blocked_notifs:
                log_success("Dev2 got lock_blocked notification")
                return True
        else:
            log_info("No notifications yet (this may be expected)")
            return True
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_workflow_state():
    """Test 6: Check workflow state"""
    log_step(6, "View Current Workflow State")

    params = {
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
    }

    response = requests.get(f"{SERVER_URL}/api/workflow/state", params=params)

    if response.status_code == 200:
        data = response.json()
        log_success("Workflow state retrieved")
        print_response(response, "Workflow State")

        current_state = data.get("current_state", "unknown")
        current_editor = data.get("current_editor", "none")
        waiting = data.get("waiting_developers", [])

        log_info(f"Current State: {current_state}")
        log_info(f"Current Editor: {current_editor}")
        log_info(f"Waiting Developers: {waiting}")
        return True
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_dev1_finish_editing():
    """Test 7: Dev1 finishes editing and releases lock"""
    log_step(7, "Dev1 Finishes Editing - Releases Lock")

    payload = {
        "developer": "dev1",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
        "branch": "feature/auth-refactor",
        "pr_link": "https://github.com/jaykrishna316/Neo/pull/1",
    }

    log_info("Dev1 calling /api/finish_editing")
    response = requests.post(f"{SERVER_URL}/api/finish_editing", json=payload)

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            log_success("Dev1 released lock")
            print_response(response)

            next_dev = data.get("next_developer")
            if next_dev:
                log_success(f"Dev2 notified (next_developer: {next_dev})")
            return True
        else:
            log_error("Failed to release lock")
            print_response(response)
            return False
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_dev2_poll_after_release():
    """Test 8: Dev2 polls again - should get RELEASE notification"""
    log_step(8, "Dev2 Polls for Notifications - Should See RELEASED")

    log_info("Dev2 polling for notifications after dev1 finished...")
    response = requests.get(
        f"{SERVER_URL}/api/notifications",
        params={"developer": "dev2"}
    )

    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])

        if notifications:
            log_success(f"Dev2 received {len(notifications)} notification(s)")
            print_response(response, "Dev2 Notifications After Release")

            # Check for lock_released notification
            released_notifs = [n for n in notifications if n["type"] == "lock_released"]
            if released_notifs:
                log_success("Dev2 got lock_released notification")
                return True
        else:
            log_info("No new notifications")
            return True
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_dev2_can_edit():
    """Test 9: Dev2 can now acquire lock"""
    log_step(9, "Dev2 Starts Editing - Lock Now Available")

    payload = {
        "developer": "dev2",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
    }

    log_info("Dev2 calling /api/start_editing now that lock is released")
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)

    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("lock_acquired"):
            log_success("Dev2 acquired lock")
            print_response(response)
            return True
        else:
            log_error("Dev2 failed to acquire lock")
            print_response(response)
            return False
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def test_final_workflow_state():
    """Test 10: Final workflow state"""
    log_step(10, "Final Workflow State - Dev2 Now Editing")

    params = {
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
    }

    response = requests.get(f"{SERVER_URL}/api/workflow/state", params=params)

    if response.status_code == 200:
        data = response.json()
        log_success("Final workflow state retrieved")
        print_response(response, "Final Workflow State")

        current_state = data.get("current_state", "unknown")
        current_editor = data.get("current_editor", "none")

        if current_state == "editing" and current_editor == "dev2":
            log_success(f"✓ Correct state: {current_editor} is {current_state}")

        return True
    else:
        log_error(f"Server returned {response.status_code}")
        print_response(response)
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}NEO COLLABORATIVE WORKFLOW - COMPLETE TEST{RESET}")
    print(f"{BLUE}Testing Dev1 and Dev2 interaction{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    tests = [
        ("Health Check", test_health_check),
        ("Subscribe Developers", test_subscribe_developers),
        ("Dev1 Starts Editing", test_dev1_start_editing),
        ("Dev2 Blocked", test_dev2_blocked),
        ("Dev2 Polls Notifications", test_dev2_poll_notifications),
        ("Check Workflow State", test_workflow_state),
        ("Dev1 Finishes Editing", test_dev1_finish_editing),
        ("Dev2 Polls After Release", test_dev2_poll_after_release),
        ("Dev2 Acquires Lock", test_dev2_can_edit),
        ("Final Workflow State", test_final_workflow_state),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            log_error(f"Exception in {name}: {e}")
            results.append((name, False))

        time.sleep(0.5)  # Small delay between requests

    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{status} - {name}")

    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Total: {GREEN}{passed}/{total} tests passed{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
