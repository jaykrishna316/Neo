# IDE Integration: Dual-Agent Test Plan (Devin vs Claude Code)

**Purpose:** Validate Neo's coordination layer with two production IDEs simultaneously  
**Target:** Test conflict detection, IDE integration quality, and merge outcomes  
**Duration:** ~15-30 minutes per scenario

---

## Architecture Review: IDE Integration Current State

### What Neo Provides
- ✅ **Intent Declaration API** (`core/activity_log.py`) - Agents declare work before generating
- ✅ **Conflict Detection** (`core/pre_gen_check.py`) - Check for conflicts before code generation
- ✅ **Risk Classification** (`core/risk_classifier.py`) - Returns LOW/MEDIUM/HIGH with explanation
- ✅ **WebSocket Support** (`core/websocket_support.py`) - Real-time event streaming to IDEs
- ✅ **State Machine** (`core/coordination_machine.py`) - Enforcement gates (silent → warning → blocking)

### IDE Integration Points
Both Claude Code and Devin need to integrate these hooks:

1. **Pre-Generation Hook** (Before code is generated)
   ```python
   from core.pre_gen_check import check_for_conflicts
   risk, message = check_for_conflicts(agent_id, file, intent, region)
   # Returns: RiskLevel.LOW/MEDIUM/HIGH + explanation
   ```

2. **Post-Generation Hook** (After code is generated)
   ```python
   from core.activity_log import log_activity
   log_activity(agent_id, file, intent, region, category)
   # Registers work in coordination log
   ```

3. **Event Subscription** (Listen for conflicts)
   ```python
   from core.websocket_support import subscribe_to_conflicts
   # Subscribe to lock notifications in real-time
   # Show UI when another agent claims ownership
   ```

---

## Test Scenarios

### Scenario 1: Same Function, Overlapping Regions (EASY)

**Setup:**
```python
# test_scenarios/test_fixture_scenario1.py
class AuthService:
    def authenticate(self, username: str, password: str) -> bool:
        # Lines 8-15: BOTH AGENTS TARGET THIS REGION
        # Claude Code: Add detailed logging
        # Devin: Add rate limiting + exponential backoff
        
        if not username or not password:
            return False
        return self.verify_credentials(username, password)
```

**Agent Instructions:**

**Devin's Task:**
```
1. Log intent: "Add rate limiting to authenticate() function"
2. Target: lines 8-15 of test_fixture_scenario1.py
3. Changes: Add rate_limit_counter, backoff timing, max attempts
4. Call: log_activity("devin-agent", "test_fixture_scenario1.py", 
            "Add rate limiting", "authenticate() lines 8-15")
```

**Claude Code's Task (3 seconds later):**
```
1. Check conflicts: check_for_conflicts("claude-code", 
   "test_fixture_scenario1.py", "Add logging", "authenticate() lines 8-15")
2. Expected: MEDIUM risk (Devin already working there)
3. Acknowledge warning, then add logging to same region
```

**Expected Result:**
- ✓ MEDIUM risk detected (both in same function)
- ✓ Evidence-based explanation provided
- ✓ Both agents complete work
- ✓ Changes can be manually merged

---

### Scenario 2: Function Signature Change (HARD)

**Setup:**
```python
# test_scenarios/test_fixture_scenario2.py
class UserService:
    def hash_password(self, password: str) -> str:
        # Lines 20-30: Devin will change signature
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> bool:
        # Lines 35-45: Claude Code calls hash_password()
        hashed = self.hash_password(password)
        return self.verify_hash(username, hashed)
```

**Agent Instructions:**

**Devin's Task:**
```
1. Log intent: "Add salt parameter to hash_password() for security"
2. Change signature: hash_password(password, salt="") -> str
3. Update implementation with salt
4. Call: log_activity("devin-agent", "test_fixture_scenario2.py",
            "Add salt to hash_password", "hash_password() lines 20-30")
```

**Claude Code's Task (3 seconds later):**
```
1. Check conflicts: check_for_conflicts("claude-code",
   "test_fixture_scenario2.py", "Add audit logging", "authenticate() lines 35-45")
2. Expected: HIGH risk (transitive - calls modified function)
3. Should be blocked or require explicit acknowledgment
```

**Expected Result:**
- ✓ HIGH risk detected (signature change affects dependent code)
- ✓ Dependency analysis shows root cause
- ✓ Claude Code is blocked/warned appropriately
- ✓ Manual coordination required

---

### Scenario 3: Non-Overlapping Regions (VALIDATION)

**Setup:**
```python
# test_scenarios/test_fixture_scenario3.py
def helper_a():
    # Lines 5-15: Devin adds new function here
    pass

def helper_b():
    # Lines 20-30: Claude Code adds new function here
    pass

class Service:
    def process(self):
        # Lines 35-40: Both functions called here
        pass
```

**Expected Result:**
- ✓ LOW risk detected (separate regions, no overlap)
- ✓ Both agents proceed silently
- ✓ No coordination needed
- ✓ Clean merge

---

### Scenario 4: Sequential Work (EXPIRY TEST)

**Setup:**
```python
# test_scenarios/test_fixture_scenario4.py
def operation():
    # Devin modifies first
    # Waits 35+ seconds (activity expires after 30 min in real usage)
    # Claude Code checks - should see no conflict
    pass
```

**Expected Result:**
- ✓ First agent completes and logs completion
- ✓ Second agent checks after expiry window
- ✓ LOW risk (activity log expired)
- ✓ Validates window-based cleanup

---

## Test Execution Protocol

### Pre-Test Checklist
- [ ] Neo coordination server running locally
- [ ] Both Devin and Claude Code connected to this repo
- [ ] Test fixture files created in `test_scenarios/`
- [ ] Output logging directories created
- [ ] All Neo imports working: `from core.activity_log import ...`

### Timing Sequence

```
T+0s:   Start Devin agent
        Devin logs intent → Neo records in .devsync/coordination.log

T+2s:   Devin begins code generation

T+3s:   Start Claude Code agent
        Claude Code calls check_for_conflicts() → Gets risk level from Neo

T+5s:   Claude Code shows user conflict warning (if MEDIUM/HIGH)
        Waits for user acknowledgment

T+7s:   Both agents generate code simultaneously

T+10s:  Both agents commit changes

T+15s:  Test harness validates merge quality

T+20s:  Generate comparison report
```

### Metrics Collection

**Per Agent:**
- Intent declaration success (did Neo accept the entry?)
- Conflict check latency (ms)
- Risk level accuracy (was it correct?)
- Code generation time (seconds)
- Total workflow time (seconds)

**System Level:**
- Conflict detection accuracy (true positive rate)
- False positive rate
- False negative rate
- WebSocket event delivery time (ms)
- Merge conflict count (should be 0)

**IDE Integration Quality:**
- Did Devin successfully call `log_activity()`?
- Did Claude Code successfully call `check_for_conflicts()`?
- Were conflict warnings displayed to user?
- Could user acknowledge/override gates?

---

## Running the Test

### Create Test Files

```bash
cd Neo
mkdir -p test_scenarios

# Create scenario 1 fixture
cat > test_scenarios/test_fixture_scenario1.py << 'EOF'
class AuthService:
    def authenticate(self, username: str, password: str) -> bool:
        if not username or not password:
            return False
        return self.verify_credentials(username, password)
    
    def verify_credentials(self, username: str, password: str) -> bool:
        return True
EOF
```

### Run Scenario 1

**Terminal A - Devin:**
```bash
cd Neo
python3 << 'EOF'
from core.activity_log import log_activity

log_activity(
    agent_id="devin-agent",
    file_path="test_scenarios/test_fixture_scenario1.py",
    intent="Add rate limiting to authenticate() function",
    region="authenticate() lines 8-15",
    intent_category="feature"
)
print("✓ Devin: Intent logged")
EOF

# Wait for Claude Code...
# Then Devin generates changes
```

**Terminal B - Claude Code (After 3 seconds):**
```bash
cd Neo
python3 << 'EOF'
from core.pre_gen_check import check_for_conflicts

risk, message = check_for_conflicts(
    agent_id="claude-code",
    file_path="test_scenarios/test_fixture_scenario1.py",
    intent="Add detailed logging to authenticate()",
    region="authenticate() lines 8-15"
)

print(f"Risk Level: {risk}")
print(f"Message: {message}")
EOF
```

### Validate Results

```bash
# Check coordination log
cat .devsync/coordination.log

# Run validation
python3 tests/multi_model_validation/lean_validation.py
```

---

## Expected Output

### Scenario 1 Success Output
```
╔════════════════════════════════════════════════════════════════╗
║           DUAL-AGENT TEST RESULTS: Scenario 1                  ║
╚════════════════════════════════════════════════════════════════╝

CONFLICT DETECTION:
  ✓ Risk Level: MEDIUM (expected MEDIUM) ✓
  ✓ Evidence Provided:
    - Same function: authenticate()
    - Overlapping lines: 8-15 vs 8-15
    - Confidence: 95%

IDE INTEGRATION:
  ✓ Devin intent logged successfully
  ✓ Claude Code received conflict warning
  ✓ User acknowledged MEDIUM risk
  ✓ Both agents proceeded with awareness

MERGE QUALITY:
  ✓ Merge conflicts: 0
  ✓ Code quality: Valid Python
  ✓ Function calls still work: ✓
  ✓ Manual merge: Successful

PERFORMANCE:
  ✓ Conflict check latency: 3.2ms (target <10ms)
  ✓ Activity log write: 1.8ms
  ✓ Total overhead: 5ms

VERDICT: ✓ PASS
```

---

## Troubleshooting

### "Module not found: core.activity_log"
```bash
cd Neo
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### "Conflict check returns None"
```bash
# Ensure coordination log exists
ls -la .devsync/
# If missing, create it:
mkdir -p .devsync
touch .devsync/coordination.log
```

### "WebSocket subscription not working"
```bash
# Verify websocket_support.py is running
python3 -c "from core.websocket_support import start_server; start_server()"
```

---

## Next Steps

1. Create test fixture files in `test_scenarios/`
2. Run Scenario 1 (easiest, validates basic flow)
3. Run Scenario 2 (tests signature detection)
4. Run Scenario 3 (validates non-overlapping)
5. Generate comparison report
6. Document findings and IDE integration recommendations

---

## Resources

- [IDE Implementation Guide](IMPLEMENTATION.md)
- [Integration Architecture](INTEGRATION_ARCHITECTURE.md)
- [Test Scenarios Framework](../tests/multi_model_validation/lean_scenarios.py)
- [WebSocket Support](../core/websocket_support.py)
