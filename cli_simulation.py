#!/usr/bin/env python3
"""CLI simulation harness for the conflict warning POC."""

import time
import sys
from typing import Optional

from activity_log import log_activity, read_log, clear_log, log_entry_age_seconds
from pre_gen_check import check_for_conflicts, handle_conflict_response
from risk_classifier import RiskLevel


class DeveloperSession:
    """Simulates a developer's working session."""

    def __init__(self, developer_id: str):
        self.developer_id = developer_id

    def start_work(
        self,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
    ):
        """Log intent to work on a file."""
        entry = log_activity(self.developer_id, file_path, intent, region)
        print(
            f"[{self.developer_id}] Started work on {file_path}\n"
            f"         Intent: {intent}\n"
            f"         Region: {region or '(whole file)'}"
        )
        return entry

    def generate_code(
        self,
        file_path: str,
        intent: str,
        region: Optional[str] = None,
        auto_confirm: bool = False,
    ) -> bool:
        """
        Simulate code generation with pre-check.

        Returns:
            True if generation proceeded, False if blocked.
        """
        print(f"\n[{self.developer_id}] Attempting to generate code for {file_path}...")

        risk_level, message = check_for_conflicts(
            self.developer_id,
            file_path,
            intent,
            region,
        )

        if message:
            print(message)

        if risk_level == RiskLevel.LOW:
            print(f"✓ No conflicts detected. Proceeding with generation.\n")
            return True

        if risk_level == RiskLevel.MEDIUM:
            if auto_confirm:
                print("(Auto-confirmed, proceeding with generation)\n")
                return True
            else:
                response = input("Proceed? (y/n): ")
                result = response.lower() in ("y", "yes")
                if result:
                    print("✓ Proceeding with generation.\n")
                else:
                    print("✗ Generation cancelled.\n")
                return result

        if risk_level == RiskLevel.HIGH:
            if auto_confirm:
                print("(Auto-confirmed despite HIGH risk, proceeding)\n")
                return True
            else:
                response = input("Proceed anyway? (y/n): ")
                result = response.lower() in ("y", "yes")
                if result:
                    print("✓ Proceeding with generation (user accepted risk).\n")
                else:
                    print("✗ Generation blocked.\n")
                return result

        return True


def scenario_1_basic_overlap():
    """Scenario 1: Dev A and Dev B work on same file, overlapping region."""
    print("\n" + "="*70)
    print("SCENARIO 1: Overlapping Regions (MEDIUM Risk)")
    print("="*70)

    clear_log()

    dev_a = DeveloperSession("DevA")
    dev_b = DeveloperSession("DevB")

    # Dev A starts work
    dev_a.start_work(
        "src/auth.py",
        "Refactor login_user function for better error handling",
        "login_user function (lines 20-40)",
    )

    time.sleep(0.5)

    # Dev B tries to generate on same region
    print("\n" + "-"*70)
    result = dev_b.generate_code(
        "src/auth.py",
        "Add validation to login_user",
        "login_user function (lines 25-35)",
        auto_confirm=True,
    )
    print(f"Generation {'succeeded' if result else 'blocked'}")


def scenario_2_non_overlapping():
    """Scenario 2: Dev A and Dev B work on same file, non-overlapping regions."""
    print("\n" + "="*70)
    print("SCENARIO 2: Non-Overlapping Regions (LOW Risk)")
    print("="*70)

    clear_log()

    dev_a = DeveloperSession("DevA")
    dev_b = DeveloperSession("DevB")

    # Dev A starts work
    dev_a.start_work(
        "src/auth.py",
        "Refactor login_user function",
        "login_user function (lines 20-40)",
    )

    time.sleep(0.5)

    # Dev B works on a different function in the same file
    print("\n" + "-"*70)
    result = dev_b.generate_code(
        "src/auth.py",
        "Add logout_user function",
        "logout_user function (lines 100-120)",
        auto_confirm=True,
    )
    print(f"Generation {'succeeded' if result else 'blocked'}")


def scenario_3_signature_change():
    """Scenario 3: Dev A makes signature changes, Dev B depends on old signature."""
    print("\n" + "="*70)
    print("SCENARIO 3: Signature Change (HIGH Risk)")
    print("="*70)

    clear_log()

    dev_a = DeveloperSession("DevA")
    dev_b = DeveloperSession("DevB")

    # Dev A starts refactoring (changes signature)
    dev_a.start_work(
        "src/auth.py",
        "Rename login_user to authenticate and change signature",
        "login_user function (lines 20-40)",
    )

    time.sleep(0.5)

    # Dev B tries to generate code that uses the function
    print("\n" + "-"*70)
    result = dev_b.generate_code(
        "src/auth.py",
        "Call login_user from new location",
        "login_user function (lines 25-35)",
        auto_confirm=True,  # AUTO-CONFIRM to show it would be blocked
    )
    print(f"Generation {'succeeded' if result else 'blocked'}")


def scenario_4_expiry():
    """Scenario 4: Entries expire after timeout."""
    print("\n" + "="*70)
    print("SCENARIO 4: Entry Expiry (30-minute timeout)")
    print("="*70)

    clear_log()

    dev_a = DeveloperSession("DevA")
    dev_b = DeveloperSession("DevB")

    # Dev A starts work
    dev_a.start_work(
        "src/config.py",
        "Update configuration schema",
        "Config class (lines 5-15)",
    )

    time.sleep(0.5)

    # Manually age the log entry by modifying timestamp
    entries = read_log()
    if entries:
        # Subtract 31 minutes from the timestamp
        entries[0]["timestamp"] -= (31 * 60)
        import json
        from pathlib import Path
        Path(".devsync/activity-log.json").write_text(json.dumps(entries, indent=2))
        print(f"\n[Simulated time skip] Aged entry by 31 minutes")

    time.sleep(0.5)

    # Dev B should now see no conflict (entry expired)
    print("\n" + "-"*70)
    result = dev_b.generate_code(
        "src/config.py",
        "Update configuration schema",
        "Config class (lines 5-15)",
        auto_confirm=True,
    )
    print(f"Generation {'succeeded' if result else 'blocked'}")


def scenario_5_multiple_developers():
    """Scenario 5: More than two developers (show first conflict detection)."""
    print("\n" + "="*70)
    print("SCENARIO 5: Multiple Developers Working on Same File")
    print("="*70)

    clear_log()

    dev_a = DeveloperSession("DevA")
    dev_b = DeveloperSession("DevB")
    dev_c = DeveloperSession("DevC")

    # Dev A and B start work
    dev_a.start_work(
        "src/models.py",
        "Refactor User model",
        "User class (lines 10-50)",
    )

    time.sleep(0.3)

    dev_b.start_work(
        "src/models.py",
        "Add password hashing to User",
        "User class (lines 20-35)",
    )

    time.sleep(0.3)

    # Dev C tries to work on the same file
    print("\n" + "-"*70)
    result = dev_c.generate_code(
        "src/models.py",
        "Add email validation to User",
        "User class (lines 30-45)",
        auto_confirm=True,
    )
    print(f"Generation {'succeeded' if result else 'blocked'}")


def scenario_6_agent_conflict_detection():
    """Scenario 6: Agent checks for conflicts before generation."""
    print("\n" + "="*70)
    print("SCENARIO 6: Agent Pre-Generation Conflict Detection")
    print("="*70)

    clear_log()

    # Import agent integration
    from agent_integration import check_conflicts_for_agent, format_conflict_guidance_for_prompt
    from intent_classifier import classify_intent

    # Developer A starts work
    dev_a = DeveloperSession("DevA")
    dev_a.start_work(
        "src/payment.py",
        "Refactor payment processing logic to handle retries",
        "process_payment function (lines 50-100)",
    )

    time.sleep(0.5)

    # Agent checks for conflicts
    print("\n" + "-"*70)
    print("[Claude-Agent-1] Checking for conflicts before generation...")

    report = check_conflicts_for_agent(
        agent_id="claude-agent-1",
        file_path="src/payment.py",
        intent="Add detailed logging to payment processing",
        region="process_payment function (lines 60-80)",
        model="claude-opus-5"
    )

    print(f"\n📊 Conflict Report:")
    print(f"   Risk Level: {report.risk_level}")
    print(f"   Has Conflicts: {report.has_conflicts}")
    print(f"   Recommendation: {report.recommended_action}")
    print(f"   Confidence: {int(report.confidence_score * 100)}%")

    if report.conflicting_developers:
        print(f"\n   ⚠️  Conflicting Developers:")
        for dev in report.conflicting_developers:
            print(f"      - {dev.developer_id} ({dev.time_ago}): {dev.intent}")

    print(f"\n   💡 Guidance: {report.agent_guidance}")

    # Show prompt injection
    print("\n📋 Prompt Injection Context:")
    prompt_context = format_conflict_guidance_for_prompt(report)
    for line in prompt_context.split("\n"):
        print(f"   {line}")


def scenario_7_intent_classification():
    """Scenario 7: Intent classification for conflict prediction."""
    print("\n" + "="*70)
    print("SCENARIO 7: Intent Classification for Smarter Conflict Detection")
    print("="*70)

    # Import intent classifier
    from intent_classifier import classify_intent, estimate_risk_from_intent

    test_intents = [
        "Add type hints to the login function",
        "Fix critical security bug in authentication",
        "Refactor database layer to use async/await",
        "Add unit tests for payment module",
    ]

    print("\n📝 Classifying Developer/Agent Intents:\n")

    for intent in test_intents:
        classified = classify_intent(intent)
        estimated_risk = estimate_risk_from_intent(classified)

        print(f"Intent: \"{intent}\"")
        print(f"  Category:   {classified.category.value}")
        print(f"  Scope:      {classified.scope.value}")
        print(f"  Risk:       {estimated_risk}")
        print(f"  Confidence: {int(classified.confidence * 100)}%")
        print()


def show_activity_log():
    """Display the current activity log."""
    print("\n" + "="*70)
    print("CURRENT ACTIVITY LOG")
    print("="*70)

    entries = read_log()
    if not entries:
        print("(empty)")
        return

    for i, entry in enumerate(entries, 1):
        age = log_entry_age_seconds(entry)
        age_str = f"{int(age)}s" if age < 60 else f"{int(age/60)}m"
        print(
            f"{i}. [{entry['developer_id']}] {entry['file_path']}\n"
            f"   Intent: {entry['intent']}\n"
            f"   Region: {entry.get('region', '(not specified)')}\n"
            f"   Age: {age_str}"
        )


def main():
    print("="*70)
    print("PRE-GENERATION CONFLICT WARNING POC")
    print("Enhanced with Agent Integration & Intent Classification")
    print("="*70)

    # Run basic developer scenarios
    scenario_1_basic_overlap()
    time.sleep(1)

    scenario_2_non_overlapping()
    time.sleep(1)

    scenario_3_signature_change()
    time.sleep(1)

    scenario_4_expiry()
    time.sleep(1)

    scenario_5_multiple_developers()
    time.sleep(1)

    # Run agent integration scenarios
    scenario_6_agent_conflict_detection()
    time.sleep(1)

    scenario_7_intent_classification()

    # Show final state
    show_activity_log()

    print("\n" + "="*70)
    print("POC COMPLETE - All 7 Scenarios Demonstrated")
    print("="*70)


if __name__ == "__main__":
    main()
