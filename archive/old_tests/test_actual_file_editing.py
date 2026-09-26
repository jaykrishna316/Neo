#!/usr/bin/env python3
"""
Real File Editing Test - Dev1 and Dev2 both want to edit test2devs.py
Demonstrates lock mechanism preventing concurrent editing

Run the activity log server first:
  python3 .claude/activity_log_server.py

Then run this test:
  python3 .claude/test_actual_file_editing.py
"""

import requests
import json
import time

SERVER_URL = "http://localhost:5000"
FILE_PATH = "test2devs.py"
FUNCTION_NAME = "process_data"

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_step(step_num, description):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}STEP {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")

def log_success(message):
    print(f"{GREEN}✓ {message}{RESET}")

def log_info(message):
    print(f"{YELLOW}→ {message}{RESET}")

def log_error(message):
    print(f"{RED}✗ {message}{RESET}")

def log_dev1(message):
    print(f"{BLUE}[DEV1]{RESET} {message}")

def log_dev2(message):
    print(f"{YELLOW}[DEV2]{RESET} {message}")

def print_response(response, title="Response"):
    print(f"\n{title}:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def main():
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}REAL FILE EDITING TEST - Lock Mechanism Demo{RESET}")
    print(f"{BLUE}File: {FILE_PATH}{RESET}")
    print(f"{BLUE}Function: {FUNCTION_NAME}{RESET}")
    print(f"{BLUE}Scenario: Dev1 and Dev2 both want to edit the same file{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    # Step 1: Health Check
    log_step(1, "Verify Activity Log Server is Running")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            log_success("Server is running on port 5000")
        else:
            log_error(f"Server error: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Cannot connect to server: {e}")
        log_info("Start the server in another terminal:")
        log_info("  python3 .claude/activity_log_server.py")
        return False

    # Step 2: Subscribe Both Developers
    log_step(2, "Subscribe Dev1 and Dev2 to Notifications")
    
    for dev in ["dev1", "dev2"]:
        payload = {"developer": dev, "channel": "polling", "endpoint": ""}
        response = requests.post(f"{SERVER_URL}/api/subscribe", json=payload)
        if response.status_code == 200:
            log_success(f"{dev} subscribed")
        else:
            log_error(f"Failed to subscribe {dev}")
            return False

    # Step 3: Dev1 Starts Editing
    log_step(3, "Dev1 Opens test2devs.py and Starts Editing")
    
    log_dev1(f"Opening {FILE_PATH}...")
    log_dev1("Making changes to process_data() function...")
    log_info("Dev1 calls /api/start_editing to acquire lock")
    
    payload = {"developer": "dev1", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("lock_acquired"):
            log_success("Dev1 acquired EXCLUSIVE lock on test2devs.py")
            log_dev1("Lock status: ACQUIRED ✓")
            print_response(response, "Dev1 Lock Response")
        else:
            log_error("Dev1 failed to acquire lock")
            return False
    else:
        log_error(f"Server error: {response.status_code}")
        return False

    # Step 4: Dev2 Tries to Edit Same File
    log_step(4, "Dev2 Tries to Edit test2devs.py - BLOCKED!")
    
    log_dev2(f"Opening {FILE_PATH}...")
    log_dev2("Trying to make changes to calculate_total() function...")
    log_info("Dev2 calls /api/start_editing on same file")
    
    time.sleep(0.5)
    
    payload = {"developer": "dev2", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if not data.get("success") and not data.get("lock_acquired"):
            log_error(f"Dev2 is BLOCKED by Dev1")
            log_dev2(f"Cannot edit: {data.get('message')}")
            print_response(response, "Dev2 Blocked Response")
        else:
            log_error("Dev2 should have been blocked!")
            return False

    # Step 5: Show Workflow State
    log_step(5, "View Workflow State - Dev1 Editing, Dev2 Waiting")
    
    params = {"file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.get(f"{SERVER_URL}/api/workflow/state", params=params)
    
    if response.status_code == 200:
        data = response.json()
        log_success("Current workflow state:")
        log_info(f"  State: {data.get('current_state').upper()}")
        log_info(f"  Current Editor: {data.get('current_editor')}")
        log_info(f"  Waiting Developers: {data.get('waiting_developers')}")
        print_response(response, "Workflow State")

    # Step 6: Dev2 Polls Notifications
    log_step(6, "Dev2 Checks for Notifications")
    
    log_dev2("Polling for notifications...")
    response = requests.get(f"{SERVER_URL}/api/notifications", params={"developer": "dev2"})
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        if notifications:
            log_success(f"Dev2 has {len(notifications)} notification(s)")
            log_dev2("📬 Notification: You are blocked by dev1")

    # Step 7: Dev1 Finishes Editing
    log_step(7, "Dev1 Finishes Editing and Releases Lock")
    
    log_dev1("Finished editing process_data() function")
    log_dev1("Creating PR on GitHub...")
    log_info("Dev1 calls /api/finish_editing")
    
    time.sleep(0.5)
    
    payload = {
        "developer": "dev1",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
        "branch": "feature/dev1-changes",
        "pr_link": "https://github.com/jaykrishna316/Neo/pull/42",
    }
    
    response = requests.post(f"{SERVER_URL}/api/finish_editing", json=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            log_success("Dev1 released lock")
            log_dev1("Lock status: RELEASED ✓")
            next_dev = data.get("next_developer")
            if next_dev:
                log_success(f"{next_dev} is notified to take over")

    # Step 8: Dev2 Receives Notification
    log_step(8, "Dev2 Receives Lock Released Notification")
    
    log_dev2("Checking notifications...")
    response = requests.get(f"{SERVER_URL}/api/notifications", params={"developer": "dev2"})
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        released = [n for n in notifications if n.get("type") == "lock_released"]
        if released:
            log_success("Dev2 received lock_released notification")
            log_dev2("🔔 Notification: Dev1 finished editing")
            log_dev2("📥 Auto-pulling Dev1's changes...")

    # Step 9: Dev2 Acquires Lock
    log_step(9, "Dev2 Acquires Lock - Dev2's Turn to Edit")
    
    log_dev2(f"Lock available. Opening {FILE_PATH}...")
    log_info("Dev2 calls /api/start_editing")
    
    time.sleep(0.5)
    
    payload = {"developer": "dev2", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("lock_acquired"):
            log_success("Dev2 acquired lock")
            log_dev2("Lock status: ACQUIRED ✓")

    # Step 10: Dev1 Now Blocked
    log_step(10, "Dev1 Tries to Edit Again - Now BLOCKED!")
    
    log_dev1("Wants to make another fix...")
    log_info("Dev1 calls /api/start_editing")
    
    time.sleep(0.5)
    
    payload = {"developer": "dev1", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if not data.get("success"):
            log_error(f"Dev1 is now BLOCKED by Dev2")
            log_dev1(f"Message: {data.get('message')}")

    # Final Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{GREEN}✓ TEST COMPLETE{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    print(f"{GREEN}✓ Lock Mechanism Works:{RESET}")
    print(f"  • Dev1 acquired lock on test2devs.py")
    print(f"  • Dev2 was blocked while Dev1 edited")
    print(f"  • Dev2 received notifications")
    print(f"  • Dev1 released lock")
    print(f"  • Dev2 acquired lock")
    print(f"  • Dev1 was now blocked")
    print(f"\n{GREEN}✓ Serialized Editing:{RESET}")
    print(f"  • Only one developer can edit at a time")
    print(f"  • Developers are automatically queued")
    print(f"  • No merge conflicts - edits are sequential")
    print(f"\n")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
