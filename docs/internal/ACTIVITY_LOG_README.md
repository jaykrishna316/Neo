# Activity Log System - Neo Integration

Multi-developer coordination system for detecting conflicts, preventing work loss, and enforcing quality gates.

## 🎯 Purpose

Enables safe concurrent development by:
- **Detecting conflicts** when 2+ developers modify the same function
- **Auto-pushing** to feature branches on HIGH conflicts (no blocking)
- **Tracking approvals** required before merging to main
- **Providing visibility** through verbal descriptions (not raw diffs)

## 📁 Files

- `activity_log_manager.py` - Core conflict detection + merge gate
- `activity_log_hook.py` - Integration point for logging changes
- `merge_gate_check.py` - Pre-push hook enforcement
- `settings.json` - Configuration for the system
- `.activity_log/` - Local POC storage (Git ignored)

## 🚀 Quick Start

### 1. Log a Change (When Code Changes)

```python
from .claude.activity_log_hook import ActivityLogHook

hook = ActivityLogHook()

# When developer1 finishes changes
hook.log_change(
    developer="Agent1",
    file_path="auth.py",
    function_name="validate_user",
    old_code="...",  # Previous code
    new_code="...",  # New code
    branch="feature/agent1-auth-refactor",
    verbal_description="Refactored validation logic for clarity"
)
```

### 2. Check Merge Status (Before Pushing to Main)

```python
status = hook.check_merge_status("auth.py", "validate_user")

if status["can_merge"]:
    # Safe to merge
    pass
else:
    # Need approvals
    print(f"Need approval from: {status['approvals_needed']}")
```

### 3. Record Approval (When Developer Approves)

```python
hook.record_approval(
    developer="Agent2",
    file_path="auth.py",
    function_name="validate_user"
)
```

## 🔴 Conflict Severity Levels

| Level | Overlap | Action | Approval | Example |
|-------|---------|--------|----------|---------|
| **LOW** | <10% | Auto-merge OK | None needed | Different files modified |
| **MEDIUM** | 10-50% | Can auto-merge | Optional | Same function, different sections |
| **HIGH** | >50% | Feature branches | **REQUIRED** | Same function, overlapping logic |

## 🔧 Configuration

Edit `settings.json` to customize:
- `auto_push_on_high` - Auto-push to feature branch on HIGH conflicts
- `enforce_on_high_conflict` - Block main merges on HIGH until approved
- `requires_all_approval` - All developers must approve

## 📊 Activity Log Structure

```
.activity_log/
├── .gitignore                    # Ignore JSON (local only)
├── auth_validate_user_*.json     # Change records
├── push_*.json                   # Auto-push logs
└── approvals/
    └── auth_validate_user_approvals.json  # Approval tracking
```

## 🔑 Key Features

### 1. Verbal Descriptions
Not just "changed line 5", but **WHY**:
- "Added fraud protection ceiling"
- "Improved performance with caching"
- "Enhanced security with email validation"

### 2. Auto-Push on HIGH
Immediately push to feature branch when HIGH conflict detected:
```
Benefits:
✓ Prevents work loss
✓ Enables immediate visibility
✓ No blocking/synchronization needed
```

### 3. Approval Gate
Blocks merge to main until all developers approve:
```
Benefits:
✓ Quality control
✓ Forces communication
✓ Prevents silent logic errors
```

## 🛑 Merge Prevention Example

When trying to push HIGH conflict to main:

```bash
$ git push origin main:main

❌ MERGE BLOCKED: HIGH CONFLICT IN auth.py::validate_user
   Reason: HIGH conflict: waiting on 1 approval(s)
   Developers involved: Agent1, Developer2
   Approved by: Agent1
   Still need approval from: Developer2
   
   Fix: Have Developer2 run:
   $ neo-approve auth.py validate_user
```

## 🚀 Phase 2 Plans

- IDE notification system (VSCode sidebar, IntelliJ panel)
- `neo-approve` CLI command
- Metrics dashboard
- Slack notifications

## 🔄 Phase 3 Plans (Future)

- Migrate storage: Git → Database
- Distributed lock mechanism
- Agent coordination protocol
- Analytics dashboard
- Multi-repo support

## 📞 Status

✅ **POC Complete**
- Conflict detection working
- Merge gate enforced
- Auto-push on HIGH
- Full test coverage

✅ **Neo Integration In Progress**
- Core files added (.claude/)
- Git hooks configured
- Ready to test with agents

🚧 **Next Steps**
- Test with real agent workflows
- Gather feedback
- Build IDE integration

## 💾 Storage Notes

**Current:** Local JSON in `.activity_log/`
- ✅ Fast POC
- ✅ No external dependencies
- ✅ Easy to inspect

**Future:** Database migration
- Planned for Phase 2-3
- Drop-in replacement
- Enables distributed agents
