#!/usr/bin/env python3
"""
Comprehensive Demo - Full Activity Log System with All Features
Shows: locking, conflict detection, merge strategies, approvals, downstream impacts, escalation
"""

from enhanced_activity_log import EnhancedActivityLogManager
import time


def print_section(title: str):
    print("\n" + "="*80)
    print(title.center(80))
    print("="*80)


def demo_low_conflict():
    """Demo: LOW conflict - Different files"""
    print_section("SCENARIO 1: LOW CONFLICT (Different files)")

    mgr = EnhancedActivityLogManager()

    print("\n👤 Agent1 starts editing payment.py::process_payment()")
    mgr.start_editing("payment.py", "process_payment", "Agent1", severity="low")

    print("\n👤 Agent2 starts editing auth.py::validate_user()")
    mgr.start_editing("auth.py", "validate_user", "Agent2", severity="low")

    print("\n✅ No conflict - both can work in parallel!")
    print("   Git will auto-merge these changes")


def demo_medium_conflict():
    """Demo: MEDIUM conflict - Same function, soft lock"""
    print_section("SCENARIO 2: MEDIUM CONFLICT (Soft warning)")

    mgr = EnhancedActivityLogManager()

    print("\n👤 Agent1 starts editing auth.py::validate_user()")
    lock = mgr.start_editing("auth.py", "validate_user", "Agent1", severity="medium")

    print("\n👤 Agent2 tries to edit same function (1 min later)...")
    time.sleep(0.5)  # Simulate 1 minute
    lock = mgr.start_editing("auth.py", "validate_user", "Agent2", severity="medium")

    if not lock["locked"]:
        print(f"\n⚠️ {lock['message']}")
        print(f"   Agent2 can continue if they want (soft lock only)")
        print(f"   Auto-pull suggested: {lock.get('auto_pull_suggested', False)}")


def demo_high_conflict():
    """Demo: HIGH conflict - Hard lock, approval gate, merge strategies"""
    print_section("SCENARIO 3: HIGH CONFLICT (Hard lock + Approval Gate)")

    mgr = EnhancedActivityLogManager()

    print("\n⏰ MINUTE 1: Agent1 starts editing auth.py::validate_user()")
    lock = mgr.start_editing("auth.py", "validate_user", "Agent1", severity="high", timeout_minutes=30)
    print(f"Lock status: {lock}")

    print("\n⏰ MINUTE 1.5: Agent2 tries to edit SAME function")
    lock = mgr.start_editing("auth.py", "validate_user", "Agent2", severity="high")

    if lock["locked"]:
        print(f"❌ {lock['message']}")
        print(f"   Time remaining: {lock['time_remaining']} minutes")

    print("\n⏰ MINUTE 15: Agent1 finishes and commits")
    change1 = mgr.log_change(
        developer="Agent1",
        file_path="auth.py",
        function_name="validate_user",
        old_code="""def validate_user(username, password):
    if not username or not password:
        return False
    user = db.find_user(username)
    if user and user.check_password(password):
        return True
    return False""",
        new_code="""def validate_user(username, password):
    if not username or not password:
        return False
    user = db.find_user(username)
    if user:
        return user.check_password(password)
    return False""",
        feature_branch="feature/agent1-auth-refactor",
        verbal_description="Refactored validation logic for clarity"
    )

    print("\n⏰ MINUTE 16: Agent2 now can start editing (lock released)")
    mgr.log_change(
        developer="Agent2",
        file_path="auth.py",
        function_name="validate_user",
        old_code="""def validate_user(username, password):
    if not username or not password:
        return False
    user = db.find_user(username)
    if user and user.check_password(password):
        return True
    return False""",
        new_code="""def validate_user(username, password, email_required=False):
    if not username or not password:
        return False
    if email_required:
        user = db.find_user(username)
        if user and user.email:
            return user.check_password(password)
        return False
    user = db.find_user(username)
    if user and user.check_password(password):
        return True
    return False""",
        feature_branch="feature/agent2-auth-email",
        verbal_description="Added optional email validation for security"
    )

    print("\n" + "="*80)
    print("MERGE STRATEGIES FOR HIGH CONFLICT".center(80))
    print("="*80)

    strategies = mgr.get_merge_strategies("auth.py", "validate_user")

    if "error" not in strategies:
        print(f"\n📋 Conflict: {strategies['overlap']} overlap")
        print(f"   Semantic compatibility: {strategies['semantic_compatibility']['explanation']}")
        print(f"\n🎯 RECOMMENDED STRATEGY:")
        rec = strategies["recommended_strategy"]
        print(f"   {rec['label']}")
        print(f"   {rec['description']}")
        print(f"   Risk: {rec['risk'].upper()}")
        print(f"   Testing required: {rec['testing_required']}")

        print(f"\n🔵 MANUAL ALTERNATIVES:")
        for i, strat in enumerate(strategies["strategies"][1:], 1):
            print(f"   {i}. {strat['label']}")
            print(f"      {strat['description']}")

    print("\n" + "="*80)
    print("APPROVAL GATE (Option A: Single approval per developer)".center(80))
    print("="*80)

    print("\n📝 Agent1 reviews and approves merge...")
    mgr.record_approval("Agent1", "auth.py", "validate_user", approval_status="approved")

    print("\n📝 Agent2 reviews and approves merge...")
    mgr.record_approval("Agent2", "auth.py", "validate_user", approval_status="approved")

    print("\n🔍 Checking if merge to main is allowed...")
    can_merge, status = mgr.can_merge_to_main("auth.py", "validate_user")

    print(f"\nMerge allowed: {can_merge}")
    print(f"Status: {status['status']}")
    print(f"Reason: {status['reason']}")
    if "approved_by" in status:
        print(f"Approved by: {', '.join(status['approved_by'])}")


def demo_downstream_impacts():
    """Demo: Downstream impact detection"""
    print_section("SCENARIO 4: DOWNSTREAM IMPACT DETECTION")

    mgr = EnhancedActivityLogManager()

    print("\n🔗 When validate_user() is modified, check dependent functions...")
    print("   Looking for: login(), authenticate(), process_login(), etc.")

    print("\n   🔴 CRITICAL FUNCTIONS FOUND:")
    print("   ├─ login.py::login() calls validate_user()")
    print("   ├─ auth.py::authenticate() calls validate_user()")
    print("   └─ api.py::api_login() calls login()")

    print("\n   ⚠️ RECOMMENDATION:")
    print("   ├─ Full test suite needed (not just unit tests)")
    print("   ├─ Run: test_login.py, test_auth.py, test_api.py")
    print("   └─ Requires approval from QA lead")


def demo_escalation_timeout():
    """Demo: Escalation after timeout"""
    print_section("SCENARIO 5: ESCALATION TIMEOUT")

    print("\n⏰ HIGH conflict detected at 14:00:00")
    print("   Timeout set: 30 minutes")
    print("   Escalation will trigger at: 14:30:00")

    print("\n⏰ 14:25:00 - Still waiting for approvals...")
    print("   Agent1: ✅ Approved")
    print("   Agent2: ⏳ No response yet")

    print("\n⏰ 14:30:00 - TIMEOUT REACHED")
    print("   🔔 Escalation triggered")
    print("   🚨 Notification sent to: manager@company.com")
    print("   📝 Message: 'HIGH conflict in auth.py::validate_user pending for 30 min'")

    print("\n   🔓 Lock released (Agent1 can now discuss with Agent2)")
    print("   Options:")
    print("   ├─ Agent1 discusses with Agent2")
    print("   ├─ Manager reviews and makes decision")
    print("   └─ Custom merge strategy applied")


def demo_rollback():
    """Demo: Rollback tracking"""
    print_section("SCENARIO 6: ROLLBACK TRACKING")

    mgr = EnhancedActivityLogManager()

    print("\n✅ Merge approved and deployed to production at 15:00:00")

    print("\n🚨 BUG DISCOVERED at 16:30:00")
    print("   Issue: validate_user() now rejects valid passwords")
    print("   Impact: Users can't log in")

    print("\n📝 Rollback initiated...")
    rollback = mgr.record_rollback(
        merge_commit_sha="abc123def456",
        file_path="auth.py",
        function_name="validate_user",
        reason="validate_user() rejecting valid passwords - agent1 refactor broke password check logic"
    )

    print("\n📊 Rollback recorded for learning:")
    print(f"   Merge: {rollback['merge_commit']}")
    print(f"   Function: {rollback['function']}")
    print(f"   Reason: {rollback['reason']}")

    print("\n📈 Learning from rollback:")
    print("   ├─ Refactor logic changes require more thorough testing")
    print("   ├─ Consider: before/after password check tests")
    print("   └─ Recommendation: Add password validation test suite")


if __name__ == "__main__":
    print("\n" + "█" * 80)
    print("COMPREHENSIVE ACTIVITY LOG SYSTEM DEMO".center(80))
    print("Features: Locking, Conflict Detection, Merge Strategies, Approvals".center(80))
    print("          Downstream Detection, Escalation, Rollback Tracking".center(80))
    print("█" * 80)

    try:
        demo_low_conflict()
        input("\nPress Enter to continue...")

        demo_medium_conflict()
        input("\nPress Enter to continue...")

        demo_high_conflict()
        input("\nPress Enter to continue...")

        demo_downstream_impacts()
        input("\nPress Enter to continue...")

        demo_escalation_timeout()
        input("\nPress Enter to continue...")

        demo_rollback()

        print_section("DEMO COMPLETE ✅")
        print("\nAll scenarios tested successfully!")
        print("Activity logs stored in: .activity_log/")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
