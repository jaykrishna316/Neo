# Multitenancy Troubleshooting Guide

**Diagnostic procedures for Neo MCP multitenancy issues | v1.0**

---

## Quick Diagnosis

### 1. Check Multitenancy Status

```bash
# Verify environment
env | grep -E "NEO_MULTITENANCY|CLAUDE_TENANT_ID"

# Should show:
# NEO_MULTITENANCY=true or false
# CLAUDE_TENANT_ID=acme-corp (or default)
```

### 2. Verify Log Files Exist

```bash
# If multitenancy enabled
ls -la .devsync/tenants/acme-corp/

# If single-tenant
ls -la .devsync/activity-log.json
```

### 3. Run Quick Health Check

```bash
pytest tests/test_multitenancy_phase1.py::TestSingleTenantMode -v -k "test_legacy_path_used"
```

---

## Common Issues & Solutions

### ❌ "NEO_MULTITENANCY not set"

**Symptom:** Multitenancy features not working, all data going to single log.

**Root Cause:** Environment variable not set or set to wrong value.

**Diagnosis:**
```bash
echo $NEO_MULTITENANCY
# Output should be: true or false
```

**Solution:**
```bash
# Add to shell profile
export NEO_MULTITENANCY=true

# Or set inline
NEO_MULTITENANCY=true python3 -m core.mcp_server

# Verify it took effect
echo $NEO_MULTITENANCY
```

**Verification:**
```python
from core.activity_log import MULTITENANCY_ENABLED
print(f"Multitenancy enabled: {MULTITENANCY_ENABLED}")  # Should be True
```

---

### ❌ "Tenant mismatch: Expected 'acme-corp', but directory contains 'startup-ai-lab'"

**Symptom:** Cannot log activity, error on validate_tenant_id

**Root Cause:** Tenant marker file corrupted or mismatched

**Diagnosis:**
```bash
cat .devsync/tenants/acme-corp/.tenant_id
# Expected: acme-corp
# Got: startup-ai-lab
```

**Solution:**
```bash
# Option 1: Fix the marker file
echo "acme-corp" > .devsync/tenants/acme-corp/.tenant_id

# Option 2: Delete and recreate the directory
rm -rf .devsync/tenants/acme-corp
# It will be recreated on next activity log

# Option 3: Check for typos in CLAUDE_TENANT_ID
echo $CLAUDE_TENANT_ID
```

**Verification:**
```bash
# Verify marker is correct
cat .devsync/tenants/acme-corp/.tenant_id
# Should output: acme-corp

# Verify with Python
from core.activity_log import ensure_tenant_isolation
ensure_tenant_isolation("acme-corp")  # Should not raise
```

---

### ❌ "Cross-tenant entries detected"

**Symptom:** Entries from one tenant visible when querying another

**Root Cause:** Filtering logic bug or multitenancy flag not set consistently

**Diagnosis:**
```python
from core.activity_log import log_activity, get_active_entries

# Log in tenant A
log_activity("agent-1", "src/test.py", "Intent A", tenant_id="acme-corp")

# Log in tenant B
log_activity("agent-2", "src/test.py", "Intent B", tenant_id="startup-ai-lab")

# Query tenant A
entries_a = get_active_entries(tenant_id="acme-corp")
print(f"Tenant A entries: {len(entries_a)}")  # Should be 1
print(f"Tenant IDs: {[e['tenant_id'] for e in entries_a]}")  # Should be all 'acme-corp'

# Check for leakage
if any(e["tenant_id"] != "acme-corp" for e in entries_a):
    print("LEAKAGE DETECTED!")
```

**Solution:**

1. **Verify multitenancy is enabled everywhere:**
   ```bash
   # Check all running processes
   ps aux | grep NEO_MULTITENANCY
   # All should have: NEO_MULTITENANCY=true
   ```

2. **Restart MCP server with fresh environment:**
   ```bash
   pkill -f "python3 -m core.mcp_server"
   export NEO_MULTITENANCY=true
   export CLAUDE_TENANT_ID=acme-corp
   python3 -m core.mcp_server
   ```

3. **Run isolation tests:**
   ```bash
   pytest tests/test_multitenancy_phase1.py::TestMultiTenantMode -v
   ```

4. **If issue persists, check core/activity_log.py::get_active_entries():**
   ```python
   # Look for this in the function:
   if MULTITENANCY_ENABLED:
       resolved_tenant = tenant_id or DEFAULT_TENANT_ID
       if entry.get("tenant_id", "default") != resolved_tenant:
           continue  # This filter is critical
   ```

---

### ❌ "Invalid tenant ID format"

**Symptom:** Tenant operations rejected with format error

**Root Cause:** Tenant ID contains invalid characters

**Diagnosis:**
```bash
echo $CLAUDE_TENANT_ID
# Check for: spaces, special chars, uppercase letters
```

**Solution:**

Valid tenant ID format: `^[a-z0-9_-]{1,64}$`

```bash
# ❌ INVALID
export CLAUDE_TENANT_ID="Acme Corp"        # spaces, uppercase
export CLAUDE_TENANT_ID="acme@corp"        # @ symbol
export CLAUDE_TENANT_ID="../../etc/passwd" # path traversal

# ✅ VALID
export CLAUDE_TENANT_ID="acme-corp"           # hyphens ok
export CLAUDE_TENANT_ID="acme_corp_team_1"    # underscores ok
export CLAUDE_TENANT_ID="acme123"             # numbers ok
export CLAUDE_TENANT_ID="default"             # lowercase ok
```

**Verification:**
```python
from core.mcp_server import validate_tenant_id

valid_ids = [
    "acme-corp",
    "startup_ai_lab",
    "team123",
    "default",
]

invalid_ids = [
    "Acme Corp",      # spaces + uppercase
    "acme@corp",      # @ symbol
    "acme/corp",      # / symbol
    "",               # empty
    "a" * 65,         # too long (>64)
]

for tid in valid_ids:
    assert validate_tenant_id(tid), f"Should be valid: {tid}"
    print(f"✓ {tid}")

for tid in invalid_ids:
    assert not validate_tenant_id(tid), f"Should be invalid: {tid}"
    print(f"✗ {tid}")
```

---

### ❌ "Activity log not found" or "FileNotFoundError"

**Symptom:** Error when reading activity log

**Root Cause:** Log file not initialized or wrong path

**Diagnosis:**
```bash
# Check if using multitenancy
echo $NEO_MULTITENANCY

# If true, check tenant directory
ls -la .devsync/tenants/acme-corp/activity-log.json

# If false, check legacy path
ls -la .devsync/activity-log.json
```

**Solution:**

```bash
# If multitenancy=true, initialize tenant
python3 << 'EOF'
from core.activity_log import ensure_log_exists
ensure_log_exists(tenant_id="acme-corp")
print("✓ Log initialized")
EOF

# If multitenancy=false, initialize legacy
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json
```

**Verification:**
```bash
# Verify log exists and is valid JSON
jq empty .devsync/tenants/acme-corp/activity-log.json
# Should output nothing if valid
```

---

### ❌ Conflict Detection Returns Wrong Risk Level

**Symptom:** Expected MEDIUM/HIGH risk but got LOW (or vice versa)

**Root Cause:** Tenant filtering prevents correct conflict detection

**Diagnosis:**
```python
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

# Setup: Two agents on same file
log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")

# Check conflicts
risk, msg = check_for_conflicts(
    agent_id="bob",
    file_path="src/auth.py",
    intent="Add SAML",
    tenant_id="acme-corp"
)

print(f"Risk level: {risk.value}")  # Should be MEDIUM or HIGH
print(f"Message: {msg}")
```

**Solution:**

1. **Verify tenant filtering is happening:**
   ```python
   from core.activity_log import get_active_entries
   
   # Should return alice's entry
   entries = get_active_entries(file_path="src/auth.py", tenant_id="acme-corp")
   print(f"Entries for conflict detection: {len(entries)}")  # Should be 1
   ```

2. **Check risk classifier logic:**
   ```python
   from core.risk_classifier import classify_risk
   
   # Debug the classification
   current_developer = "bob"
   current_file = "src/auth.py"
   current_intent = "Add SAML"
   
   other_entry = {
       "developer_id": "alice",
       "file_path": "src/auth.py",
       "intent": "Add OAuth2",
       "region": None,
       "tenant_id": "acme-corp"
   }
   
   assessment = classify_risk(
       current_developer=current_developer,
       current_file=current_file,
       current_intent=current_intent,
       current_region=None,
       other_entry=other_entry
   )
   
   print(f"Risk: {assessment.level.value}")
   print(f"Reason: {assessment.reason}")
   ```

3. **Run conflict detection tests:**
   ```bash
   pytest tests/test_multitenancy_phase4.py::TestConcurrentTenants::test_file_conflict_isolation_across_tenants -v -s
   ```

---

### ❌ Performance Degradation (>1% overhead)

**Symptom:** Multitenancy operations are slow

**Root Cause:** Too many entries, inefficient filtering, or disk I/O

**Diagnosis:**
```bash
# Check activity log size
du -h .devsync/tenants/*/activity-log.json

# Count entries
wc -l .devsync/tenants/*/activity-log.json

# Check disk speed
time cat .devsync/tenants/acme-corp/activity-log.json > /dev/null
```

**Solution:**

1. **Archive old entries:**
   ```python
   import json
   from pathlib import Path
   from datetime import datetime, timedelta
   import time
   
   log_file = Path(".devsync/tenants/acme-corp/activity-log.json")
   entries = json.loads(log_file.read_text())
   
   # Keep only last 7 days
   cutoff = time.time() - (7 * 24 * 60 * 60)
   recent = [e for e in entries if e["timestamp"] > cutoff]
   
   log_file.write_text(json.dumps(recent, indent=2))
   print(f"Archived {len(entries) - len(recent)} old entries")
   ```

2. **Verify overhead:**
   ```bash
   pytest tests/test_multitenancy_phase4.py::TestPerformanceBenchmark -v -s
   ```

3. **If overhead still >5%, check system resources:**
   ```bash
   # CPU usage
   top -b -n 1 | head -20
   
   # Disk I/O
   iostat -x 1 5
   
   # Memory
   free -h
   ```

---

### ❌ Tenant Directory Not Created

**Symptom:** Expected `.devsync/tenants/acme-corp/` doesn't exist

**Root Cause:** ensure_log_exists() wasn't called, or multitenancy disabled

**Diagnosis:**
```bash
ls -la .devsync/tenants/
# Should list tenant directories

# Check multitenancy status
echo $NEO_MULTITENANCY
```

**Solution:**

```python
# Manually ensure directory exists
from core.activity_log import ensure_log_exists

ensure_log_exists(tenant_id="acme-corp")
print("✓ Directory created")

# Verify
from pathlib import Path
assert Path(".devsync/tenants/acme-corp/activity-log.json").exists()
```

---

## Advanced Diagnostics

### Check Tenant Isolation Comprehensively

```python
#!/usr/bin/env python3
"""Comprehensive tenant isolation validation."""

from core.activity_log import (
    log_activity, get_active_entries, read_log, clear_log
)
from core.pre_gen_check import check_for_conflicts

def validate_tenant_isolation():
    """Run all isolation checks."""
    
    tenants = ["tenant-a", "tenant-b", "tenant-c"]
    
    # Test 1: Logging isolation
    print("Test 1: Logging isolation...")
    for tenant in tenants:
        for i in range(5):
            log_activity(f"agent-{i}", f"src/file{i}.py", f"Intent for {tenant}", tenant_id=tenant)
    
    for tenant in tenants:
        entries = get_active_entries(tenant_id=tenant)
        assert len(entries) == 5, f"{tenant}: expected 5, got {len(entries)}"
        assert all(e["tenant_id"] == tenant for e in entries), f"{tenant}: found cross-tenant entries"
    print("✓ Logging isolation OK")
    
    # Test 2: Filtering isolation
    print("Test 2: Filtering isolation...")
    for tenant in tenants:
        entries = get_active_entries(file_path="src/file0.py", tenant_id=tenant)
        assert len(entries) == 1, f"{tenant}: file filter failed"
        assert entries[0]["tenant_id"] == tenant, f"{tenant}: file filter cross-tenant leak"
    print("✓ Filtering isolation OK")
    
    # Test 3: Conflict detection isolation
    print("Test 3: Conflict detection isolation...")
    # Company A sees conflict
    risk_a, msg_a = check_for_conflicts(
        agent_id="new-agent",
        file_path="src/file0.py",
        intent="New intent",
        tenant_id=tenants[0]
    )
    assert risk_a.value != "LOW", f"{tenants[0]}: should see conflict"
    
    # Company B doesn't see Company A's work
    risk_b, msg_b = check_for_conflicts(
        agent_id="new-agent",
        file_path="src/file0.py",
        intent="New intent",
        tenant_id=tenants[1]
    )
    assert risk_b.value == "LOW", f"{tenants[1]}: shouldn't see {tenants[0]}'s work"
    print("✓ Conflict detection isolation OK")
    
    # Test 4: Read isolation
    print("Test 4: Read log isolation...")
    for tenant in tenants:
        all_entries = read_log(tenant_id=tenant)
        assert len(all_entries) == 5, f"{tenant}: read_log count mismatch"
        assert all(e["tenant_id"] == tenant for e in all_entries), f"{tenant}: read_log leakage"
    print("✓ Read log isolation OK")
    
    # Test 5: Clear isolation
    print("Test 5: Clear log isolation...")
    clear_log(tenant_id=tenants[0])
    entries_0 = get_active_entries(tenant_id=tenants[0])
    entries_1 = get_active_entries(tenant_id=tenants[1])
    
    assert len(entries_0) == 0, f"{tenants[0]}: clear didn't work"
    assert len(entries_1) == 5, f"{tenants[1]}: clear affected other tenant"
    print("✓ Clear log isolation OK")
    
    print("\n✅ ALL ISOLATION TESTS PASSED")

if __name__ == "__main__":
    validate_tenant_isolation()
```

Run it:
```bash
python3 scripts/validate_isolation.py
```

---

## Performance Profiling

```python
#!/usr/bin/env python3
"""Profile multitenancy performance."""

import time
import sys
from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts

def profile_operations():
    """Measure performance of key operations."""
    
    # Setup
    num_ops = 1000
    tenants = ["tenant-1", "tenant-2", "tenant-3"]
    
    # Profile 1: Logging
    start = time.perf_counter()
    for i in range(num_ops):
        tenant = tenants[i % 3]
        log_activity(f"agent-{i}", f"src/file{i % 10}.py", f"Intent {i}", tenant_id=tenant)
    log_time = time.perf_counter() - start
    
    print(f"Logging: {num_ops} ops in {log_time:.4f}s ({log_time/num_ops*1000:.2f}ms/op)")
    
    # Profile 2: Query
    start = time.perf_counter()
    for i in range(100):
        tenant = tenants[i % 3]
        entries = get_active_entries(tenant_id=tenant)
    query_time = time.perf_counter() - start
    
    print(f"Query: 100 ops in {query_time:.4f}s ({query_time/100*1000:.2f}ms/op)")
    
    # Profile 3: Conflict check
    start = time.perf_counter()
    for i in range(100):
        tenant = tenants[i % 3]
        risk, msg = check_for_conflicts(
            agent_id=f"check-{i}",
            file_path=f"src/file{i % 10}.py",
            intent="Check intent",
            tenant_id=tenant
        )
    conflict_time = time.perf_counter() - start
    
    print(f"Conflict: 100 ops in {conflict_time:.4f}s ({conflict_time/100*1000:.2f}ms/op)")
    
    # Summary
    total_overhead = ((log_time + query_time + conflict_time) / (log_time / (num_ops/100))) - 1
    print(f"\nEstimated overhead: {total_overhead*100:.2f}%")

if __name__ == "__main__":
    profile_operations()
```

Run it:
```bash
python3 scripts/profile_performance.py
```

---

## Recovery Procedures

### Full Reset to Single-Tenant

```bash
# 1. Stop MCP server
pkill -f "python3 -m core.mcp_server"

# 2. Remove multitenancy data
rm -rf .devsync/tenants/

# 3. Restore backup
if [ -f ".devsync/activity-log.json.backup" ]; then
    cp .devsync/activity-log.json.backup .devsync/activity-log.json
fi

# 4. Disable multitenancy
export NEO_MULTITENANCY=false
unset CLAUDE_TENANT_ID

# 5. Start MCP server
python3 -m core.mcp_server

# 6. Verify
pytest tests/test_multitenancy_phase1.py::TestSingleTenantMode -v
```

### Recover from Corrupted Tenant

```bash
# Identify corrupted tenant
TENANT="acme-corp"

# 1. Backup current state
cp -r .devsync/tenants/$TENANT .devsync/tenants/$TENANT.corrupt

# 2. Initialize fresh
rm -rf .devsync/tenants/$TENANT
python3 << EOF
from core.activity_log import ensure_log_exists
ensure_log_exists(tenant_id="$TENANT")
EOF

# 3. Verify
pytest tests/test_multitenancy_phase1.py::TestMultiTenantMode -v
```

---

## Testing in Isolation Mode

```bash
# Run only multitenancy tests
pytest tests/test_multitenancy_*.py -v

# Run only isolation tests
pytest tests/test_multitenancy_phase1.py::TestMultiTenantMode -v

# Run with detailed output
pytest tests/test_multitenancy_phase4.py -v -s --tb=long
```

---

## Support

If issues persist after following this guide:

1. Collect diagnostics:
   ```bash
   # Environment
   env | grep -E "NEO_|CLAUDE_" > /tmp/env.txt
   
   # File structure
   find .devsync -type f | head -20 > /tmp/files.txt
   
   # Test results
   pytest tests/test_multitenancy_*.py -v > /tmp/tests.txt 2>&1
   ```

2. Check error logs:
   ```bash
   grep -i "error\|tenant\|isolation" .devsync/tenants/*/mcp-server.log
   ```

3. Report with:
   - Output of diagnostics above
   - Exact error message
   - Reproduction steps
   - Environment (OS, Python version, container type)

---

**Last Updated:** 2026-09-14  
**Version:** 1.0  
**Status:** Stable
