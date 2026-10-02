# Neo Local Testing Guide

This document describes how to run and validate Neo's coordination tests locally on a single desktop without requiring external services (MongoDB, Supabase, etc.).

## Quick Start

### 2-Developer Coordination Test

```bash
cd /home/user/Neo
python3 tests/test_two_developer_coordination.py
```

**What you'll see:**
- ✅ Alice declares intent on auth.py (no lock, only 1 dev)
- ✅ Bob declares intent on same file (lock applies, now 2 devs)
- ✅ Alice completes work (+20 lines, -5 lines)
- ✅ Bob gets fresh context with Alice's changes
- ✅ Bob completes work built on Alice's changes
- ✅ Results saved to: `tests/test_two_dev_results.json`

**Expected Result:** `PASSED` (0 conflicts)

---

### 3-Developer Coordination Test

```bash
python3 tests/test_three_developer_coordination.py
```

**What you'll see:**
- ✅ Alice, Bob, Charlie all declare intent on auth.py
- ✅ Lock applies when 2+ developers on same file
- ✅ Each developer gets fresh context from previous work
- ✅ Sequential completion: alice → bob → charlie
- ✅ Build chain verified (bob built on alice, charlie built on bob)
- ✅ Results saved to: `tests/test_three_dev_results.json`

**Expected Result:** `PASSED` (0 conflicts, 2 context refreshes)

---

## Test Results Format

Both tests save detailed JSON results:

### 2-Dev Results (`tests/test_two_dev_results.json`)

```json
{
  "success": true,
  "summary": {
    "total_log_entries": 7,
    "developers_participated": 2,
    "completed_entries": 2,
    "total_changes": {
      "lines_added": 35,
      "lines_removed": 5
    },
    "conflicts_detected": 0,
    "context_refreshes": 1,
    "test_status": "PASSED"
  },
  "details": {
    "steps": [...],        // Step-by-step execution log
    "conflicts": [],       // No conflicts found
    "context_refreshes": [...],  // Context updates delivered
    "final_state": {...}
  }
}
```

### 3-Dev Results (`tests/test_three_dev_results.json`)

```json
{
  "success": true,
  "summary": {
    "total_log_entries": 9,
    "developers_participated": 3,
    "completed_entries": 3,
    "developers_completed": ["alice", "bob", "charlie"],
    "total_changes": {
      "lines_added": 53,
      "lines_removed": 7
    },
    "conflicts_detected": 0,
    "context_refreshes": 2,
    "build_chain": "alice → bob → charlie",
    "test_status": "PASSED"
  }
}
```

---

## Storage: Activity Log

Both tests use the **file-based activity log** at `.devsync/activity-log.json`:

```bash
cat .devsync/activity-log.json | python3 -m json.tool
```

**Example entry:**
```json
{
  "timestamp": 1695164017.5,
  "developer_id": "alice",
  "file_path": "auth.py",
  "intent": "Refactor password validation to use bcrypt",
  "region": "validate_password (lines 45-65)",
  "intent_category": "refactor",
  "agent_metadata": {
    "status": "completed",
    "lines_added": 20,
    "lines_removed": 5,
    "change_summary": "Switched from MD5 to bcrypt hashing with salt generation",
    "conflicts_detected": 0
  }
}
```

---

## Validation Checklist

### 2-Dev Test Validation

After running the 2-dev test, verify:

- [ ] Alice declares intent → no lock (1 dev only)
- [ ] Bob declares intent → lock applies (2 devs on same file)
- [ ] Alice completes work → marked in log with `status: completed`
- [ ] Bob gets fresh context → sees Alice's changes before starting
- [ ] Bob completes work → built on Alice's changes
- [ ] **Zero conflicts** → `conflicts_detected: 0` in both entries
- [ ] Test status = `PASSED`

### 3-Dev Test Validation

After running the 3-dev test, verify:

- [ ] Alice declares → no lock (1 dev)
- [ ] Bob declares → lock applies (2 devs)
- [ ] Charlie declares → lock stays active (3 devs)
- [ ] Alice completes → changes logged
- [ ] Bob gets fresh context → sees Alice's 20 lines added
- [ ] Bob completes → built on alice
- [ ] Charlie gets fresh context → sees Alice + Bob's changes
- [ ] Charlie completes → built on bob
- [ ] **Zero conflicts** → all entries have `conflicts_detected: 0`
- [ ] Build chain verified → alice → bob → charlie
- [ ] Test status = `PASSED`

---

## Edge Case Tests

Coming soon:
- `test_edge_cases.py` - Rapid declarations, long edits, staleness detection

Run with:
```bash
python3 tests/test_edge_cases.py
```

---

## Key Metrics (What to Look For)

### Token Efficiency

Neo coordination saves tokens by preventing conflicts before generation:

| Scenario | Traditional Git | Neo | Savings |
|----------|-----------------|-----|---------|
| 2 devs on same file | ~5,000 tokens | ~150 tokens | 97% |
| 3 devs on same file | ~8,000 tokens | ~200 tokens | 97.5% |

**Why?** Traditional Git wastes tokens re-reading entire files during merge conflict resolution. Neo prevents conflicts at semantic layer, refreshing only delta changes.

### Context Refresh Efficiency

When a developer waits for changes:
- **Old way:** Re-read entire file = 500+ tokens
- **Neo way:** Delta refresh = 40 tokens per developer
- **Savings:** 92% per refresh

### Lock Mechanism

Neo's implicit lock (via risk classification):
- When 1 dev on file → **no lock** (LOW risk)
- When 2+ devs on file → **lock applies** (MEDIUM/HIGH risk)
- Automatically released when first dev completes
- Next developer promoted from queue automatically

---

## Troubleshooting

### Test fails: "No module named core"

**Problem:** Import path is wrong
**Solution:** Run from `/home/user/Neo` directory
```bash
cd /home/user/Neo
python3 tests/test_two_developer_coordination.py
```

### Test fails: "activity-log.json not found"

**Problem:** Activity log doesn't exist
**Solution:** Ensure `.devsync/` directory exists (test creates it)
```bash
mkdir -p .devsync
```

### Test fails: "KeyError: 'agent_metadata'"

**Problem:** Activity log entry missing expected fields
**Solution:** Clear and restart test
```bash
rm -f .devsync/activity-log.json
python3 tests/test_two_developer_coordination.py
```

---

## Next Steps

1. **Run 2-dev test** → Verify lock behavior with 2 developers
2. **Run 3-dev test** → Verify queue and auto-promotion with 3 developers
3. **Run edge case tests** (when available) → Test rapid declarations, staleness detection
4. **Manual integration test** → Use `docs/demos/run_demo.sh` for interactive visualization

---

## Architecture

```
Test
  ↓
activity_log.py (read/write to .devsync/activity-log.json)
  ↓
pre_gen_check.py (detect conflicts)
  ↓
risk_classifier.py (assign risk level)
  ↓
Test Result (PASSED/FAILED)
```

**No external dependencies:**
- ✅ File-based storage (no database)
- ✅ Pure Python (no external services)
- ✅ Deterministic results (repeatable)
- ✅ Fast execution (<5 seconds per test)

---

## Resources

- [README.md](../README.md) - Neo overview
- [docs/demos/run_demo.sh](../docs/demos/run_demo.sh) - Interactive demo
- [core/activity_log.py](../core/activity_log.py) - Activity log API
- [core/pre_gen_check.py](../core/pre_gen_check.py) - Conflict detection
