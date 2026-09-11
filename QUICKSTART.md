# Conflict Warning POC - Quick Start

## Run the Full Simulation

```bash
python3 cli_simulation.py
```

This runs 5 scenarios end-to-end (~3 seconds total):
1. **Overlapping regions** → MEDIUM risk, non-blocking warning
2. **Non-overlapping regions** → LOW risk, silent
3. **Signature changes** → HIGH risk, requires confirmation
4. **Entry expiry** → Stale entries ignored after 30 minutes
5. **Multiple developers** → First conflict detected

## Verify Each Component

### Activity Log

```python
from activity_log import log_activity, read_log, get_active_entries

# Log a developer's intent
entry = log_activity("DevA", "src/auth.py", "Fix login bug", "login function (lines 20-40)")

# Read all entries
all_entries = read_log()

# Get active entries for a specific file
active = get_active_entries("src/auth.py")
```

### Risk Classifier

```python
from risk_classifier import classify_risk, RiskLevel

# Assess conflict between two developers
assessment = classify_risk(
    current_developer="DevB",
    current_file="src/auth.py",
    current_intent="Add validation",
    current_region="login function (lines 25-35)",
    other_entry=active[0],  # from activity log
)

print(f"Risk level: {assessment.level}")  # LOW, MEDIUM, or HIGH
print(f"Reason: {assessment.reason}")
```

### Pre-Generation Check

```python
from pre_gen_check import check_for_conflicts

risk_level, message = check_for_conflicts(
    developer_id="DevB",
    file_path="src/auth.py",
    intent="Add validation",
    region="login function (lines 25-35)",
)

if message:
    print(message)  # Shows conflicting developer's intent + reason
```

## Test Scenarios Manually

### Quick Test: Non-Overlapping Regions (Should Be Silent)

```bash
python3 << 'EOF'
from activity_log import clear_log, log_activity, get_active_entries
from pre_gen_check import check_for_conflicts

clear_log()

# Dev A works on function1
log_activity("DevA", "test.py", "Fix function1", "function1 (lines 1-10)")

# Dev B works on function2 in same file
risk, msg = check_for_conflicts(
    "DevB", "test.py", "Add function2", "function2 (lines 50-60)"
)

print(f"Risk: {risk}")
print(f"Message: {msg}")
EOF
```

Expected: `Risk: RiskLevel.LOW`, `Message: None` (silent)

### Quick Test: Overlapping Regions (Should Warn)

```bash
python3 << 'EOF'
from activity_log import clear_log, log_activity
from pre_gen_check import check_for_conflicts

clear_log()

# Dev A works on login_user
log_activity("DevA", "auth.py", "Refactor login", "login_user (lines 20-40)")

# Dev B also works on login_user
risk, msg = check_for_conflicts(
    "DevB", "auth.py", "Add validation", "login_user (lines 30-35)"
)

print(f"Risk: {risk}")
print(msg)  # Shows warning with DevA's intent
EOF
```

Expected: `Risk: RiskLevel.MEDIUM`, shows warning with DevA's details

## Inspect the Activity Log

The log is stored at `.devsync/activity-log.json`:

```bash
cat .devsync/activity-log.json | python3 -m json.tool
```

Each entry:
```json
{
  "developer_id": "DevA",
  "file_path": "src/auth.py",
  "intent": "Refactor login function",
  "region": "login_user function (lines 20-40)",
  "timestamp": 1694358400.123
}
```

## Clean Up

```bash
rm -rf .devsync
```

This removes the activity log (safe, rebuilds on next run).

## Integration Example

```python
# In your IDE/agent before generating code:

from pre_gen_check import check_for_conflicts, handle_conflict_response
from activity_log import log_activity

# Step 1: Log intent
log_activity(
    developer_id="DevA",
    file_path="src/models.py",
    intent="Add email validation to User model",
    region="User.validate_email method",
)

# Step 2: Before generating on a different file, check conflicts
risk_level, message = check_for_conflicts(
    developer_id="DevB",
    file_path="src/models.py",
    intent="Refactor User model for performance",
    region="User class",
)

# Step 3: Handle response (silent for LOW, warn for MEDIUM, block for HIGH)
proceed = handle_conflict_response(risk_level, message)

if proceed:
    # Generate code...
    pass
else:
    # User chose not to override HIGH risk
    print("Generation cancelled")
```

## Expected Output from Full Simulation

```
SCENARIO 1: Overlapping Regions (MEDIUM Risk)
✓ Detected overlapping region
✓ Showed warning with DevA's intent
✓ Proceeded with generation (non-blocking)

SCENARIO 2: Non-Overlapping Regions (LOW Risk)
✓ Detected non-overlapping region
✓ No warning shown (silent)
✓ Proceeded with generation

SCENARIO 3: Signature Change (HIGH Risk)
✓ Detected signature change + overlap
✓ Showed blocking warning
✓ Required confirmation (auto-confirmed in test)

SCENARIO 4: Entry Expiry
✓ Aged entry by 31 minutes
✓ Entry no longer active
✓ No warning shown (expired)

SCENARIO 5: Multiple Developers
✓ Detected first conflict
✓ Proceeded with generation
✓ Log shows multiple concurrent entries
```

## Performance

The pre-generation check is designed to be fast:

- **Activity log read**: ~1-2ms (local JSON file)
- **Risk classification**: ~5-10ms (in-memory analysis)
- **Total**: <10ms overhead (imperceptible to user)

No network calls, no database queries, no heavy computation.
