#!/usr/bin/env python3
"""
Agent vs Human Workflow Test

AGENT (Claude):
- Automatically pulls changes
- Automatically reviews code  
- Automatically merges
- Acquires lock and continues editing
- No human intervention needed

HUMAN (Developer):
- Presented with options: pull, ignore, review
- Can manually choose actions
- Gets interactive prompts
- Can make approval decisions
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
CYAN = '\033[96m'
RESET = '\033[0m'

def log_step(step_num, description):
    print(f"\n{BLUE}{'='*90}{RESET}")
    print(f"{BLUE}STEP {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*90}{RESET}")

def log_success(message):
    print(f"{GREEN}✓ {message}{RESET}")

def log_info(message):
    print(f"{YELLOW}→ {message}{RESET}")

def log_agent(message):
    print(f"{CYAN}[AGENT]{RESET} {message}")

def log_human(message):
    print(f"{BLUE}[HUMAN]{RESET} {message}")

def test_agent_workflow():
    print(f"\n{BLUE}{'='*90}{RESET}")
    print(f"{BLUE}AGENT vs HUMAN WORKFLOW TEST{RESET}")
    print(f"{BLUE}{'='*90}{RESET}\n")

    # Step 1: Register developers with types
    log_step(1, "Register Developers")
    
    developers = [
        ("claude_agent", "agent"),
        ("jane_human", "human"),
    ]
    
    for dev_name, dev_type in developers:
        payload = {"developer": dev_name, "type": dev_type}
        response = requests.post(f"{SERVER_URL}/api/register_developer", json=payload)
        if response.status_code == 200:
            log_success(f"{dev_name} registered as {dev_type}")

    # Step 2: Subscribe both
    log_step(2, "Subscribe to Notifications")
    
    for dev_name, _ in developers:
        payload = {"developer": dev_name, "channel": "polling", "endpoint": ""}
        requests.post(f"{SERVER_URL}/api/subscribe", json=payload)
        log_info(f"{dev_name} subscribed")

    # Step 3: Human developer starts editing
    log_step(3, "Human Developer Starts Editing")
    
    log_human("Opening test2devs.py...")
    log_human("Editing process_data() function...")
    
    payload = {"developer": "jane_human", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    if response.status_code == 200 and response.json().get("success"):
        log_success("jane_human acquired lock")

    # Step 4: Agent blocked
    log_step(4, "Agent Tries to Edit - BLOCKED")
    
    log_agent("Attempting to acquire lock...")
    
    time.sleep(0.3)
    payload = {"developer": "claude_agent", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    response = requests.post(f"{SERVER_URL}/api/start_editing", json=payload)
    if response.status_code == 200 and not response.json().get("success"):
        log_info("Agent BLOCKED - jane_human has lock")
        log_agent("Queued for editing. Waiting...")

    # Step 5: Human finishes and creates PR
    log_step(5, "Human Developer Finishes - Creates PR")
    
    log_human("Completed editing")
    log_human("Creating PR #1")
    
    time.sleep(0.3)
    payload = {
        "developer": "jane_human",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
        "branch": "feature/jane-changes",
        "pr_link": "https://github.com/jaykrishna316/Neo/pull/1",
    }
    requests.post(f"{SERVER_URL}/api/finish_editing", json=payload)
    log_success("Human released lock and created PR")

    payload = {
        "developer": "jane_human",
        "file_path": FILE_PATH,
        "function_name": FUNCTION_NAME,
        "pr_number": 1,
        "pr_link": "https://github.com/jaykrishna316/Neo/pull/1",
        "branch": "feature/jane-changes",
    }
    requests.post(f"{SERVER_URL}/api/create_pr", json=payload)

    # Step 6: Agent gets review options - AGENT PATH (AUTO)
    log_step(6, "Agent Gets Review Options - AUTO WORKFLOW")
    
    log_agent("Polling for notifications...")
    log_agent("PR #1 available for review")
    
    response = requests.get(
        f"{SERVER_URL}/api/review_options",
        params={"developer": "claude_agent", "file_path": FILE_PATH, "function_name": FUNCTION_NAME}
    )
    
    if response.status_code == 200:
        data = response.json()
        dev_type = data.get("developer_type")
        
        if dev_type == "agent":
            log_success("Agent detected - triggering AUTO workflow")
            log_agent("Workflow steps:")
            log_agent("  1. auto_pull")
            log_agent("  2. auto_review")
            log_agent("  3. auto_merge")
            log_agent("  4. acquire_lock")
            
            # Agent auto-processes
            payload = {
                "developer": "claude_agent",
                "file_path": FILE_PATH,
                "function_name": FUNCTION_NAME,
            }
            response = requests.post(f"{SERVER_URL}/api/agent_auto_process", json=payload)
            
            if response.status_code == 200:
                auto_data = response.json()
                log_success(f"Agent AUTO workflow completed")
                log_agent("✓ Pulled jane_human's changes")
                log_agent("✓ Reviewed code automatically")
                log_agent("✓ Merged changes")
                log_agent("✓ Acquired lock")
                log_agent("✓ Ready to continue editing")

    # Step 7: Human gets review options - HUMAN PATH (INTERACTIVE)
    log_step(7, "Demonstration: Human Would Get Interactive Options")
    
    log_info("If Human Developer was waiting instead:")
    log_human("Getting review options for agent's PR...")
    log_info("Available actions:")
    log_info("  [ pull  ] - Download and review code changes")
    log_info("  [ ignore] - Skip review and start editing")
    log_info("  [ review] - View detailed code diff")
    log_info("")
    log_info("Human would need to SELECT one of these options")
    log_info("System waits for human's choice before proceeding")

    # Final Summary
    print(f"\n{BLUE}{'='*90}{RESET}")
    print(f"{GREEN}✓ AGENT vs HUMAN WORKFLOW TEST COMPLETE{RESET}")
    print(f"{BLUE}{'='*90}{RESET}\n")
    
    print(f"{CYAN}Key Differences:{RESET}")
    print(f"\n{CYAN}AGENT (Claude):{RESET}")
    print(f"  ✓ Auto-pulls code changes")
    print(f"  ✓ Auto-reviews without delay")
    print(f"  ✓ Auto-merges if acceptable")
    print(f"  ✓ Immediately acquires lock")
    print(f"  ✓ Continues with no intervention")
    print(f"  → Workflow is AUTOMATIC and FAST")
    
    print(f"\n{CYAN}HUMAN (Developer):{RESET}")
    print(f"  → Presented with interactive options")
    print(f"  → Can pull/ignore/review")
    print(f"  → Makes manual approval decisions")
    print(f"  → Can ask questions or request changes")
    print(f"  → Workflow requires HUMAN CHOICES")
    
    print(f"\n{CYAN}Result:{RESET}")
    print(f"  Mixed teams of agents + humans can collaborate")
    print(f"  Each type gets appropriate workflow")
    print(f"  No human bottlenecks for agent work")
    print(f"  Humans maintain control over their decisions")
    print(f"\n")

if __name__ == "__main__":
    test_agent_workflow()

