# Dual-Agent Test Scenarios

Test fixtures and orchestration tools for validating Neo's coordination layer with multiple IDEs.

## Overview

This directory contains:
- **Test Fixtures:** Python files that simulate real code conflicts
- **Test Harness:** Orchestration script that runs coordinated dual-agent tests
- **Results:** JSON outputs from test runs

## Test Fixtures

### Scenario 1: Overlapping Regions
**File:** `test_fixture_scenario1.py`  
**Setup:** Both agents modify the `authenticate()` function  
**Expected:** MEDIUM risk (same function, overlapping lines)

### Scenario 2: Signature Change (Transitive Conflict)
**File:** `test_fixture_scenario2.py`  
**Setup:** Devin changes `hash_password()` signature; Claude Code calls it  
**Expected:** HIGH or MEDIUM risk (dependency-based conflict)

### Scenario 3: Non-Overlapping Regions
**File:** `test_fixture_scenario3.py`  
**Setup:** Devin modifies `helper_a()`; Claude Code modifies `helper_b()`  
**Expected:** LOW risk (separate functions, no overlap)

### Scenario 4: Sequential Work with Expiry
**File:** `test_fixture_scenario4.py`  
**Setup:** Devin completes work; Claude Code checks after expiry window  
**Expected:** LOW risk (activity log entry expired)

## Running Tests

### Quick Start

```bash
cd Neo
python3 test_scenarios/dual_agent_test_harness.py
```

This runs all 4 scenarios automatically with coordinated timing.

### Expected Output

```
======================================================================
  DUAL-AGENT TEST HARNESS: Devin vs Claude Code
  Neo Coordination Layer Validation
======================================================================

======================================================================
  SCENARIO 1: Overlapping Regions (Expected: MEDIUM)
======================================================================

[T+0s] Devin logs intent...
  [devin-agent] N/A (logger): Add rate limiting...

[T+3s] Waiting for Claude Code to check conflicts...
[T+3s] Claude Code checks for conflicts...
  [claude-code] MEDIUM: Add detailed logging...

  Result: ✓ PASS
  Latency: Devin=2.34ms, Claude=5.67ms
  Expected Risk: MEDIUM, Got: MEDIUM

[... scenarios 2, 3, 4 ...]

======================================================================
  TEST SUMMARY
======================================================================

Scenario 1:
  Passed: 2/2
    ✓ devin-agent: N/A (logger) (2.34ms)
    ✓ claude-code: MEDIUM (5.67ms)

Overall: 8/8 scenarios passed
======================================================================

Results saved to: test_scenarios/test_results/test_results.json
```

### Advanced: Run Individual Scenario

To test a single scenario, modify `dual_agent_test_harness.py` and call:

```python
from test_scenarios.dual_agent_test_harness import DualAgentTestHarness

harness = DualAgentTestHarness()
harness.run_scenario_1()  # Or scenario_2, 3, 4
harness.print_summary()
harness.save_results()
```

## Interpreting Results

### Success Criteria

| Scenario | Expected Risk | Meaning |
|----------|---------------|---------|
| 1 | MEDIUM | Same function targeted by both agents |
| 2 | HIGH/MEDIUM | Transitive dependency conflict detected |
| 3 | LOW | Different functions, no overlap |
| 4 | LOW | Activity expired after time window |

### Latency

- **Target:** < 10ms per conflict check
- **Goal:** Sub-10ms overhead validates real-time IDE integration

### IDE Integration Quality

✓ **Pass Criteria:**
- Devin successfully calls `log_activity()`
- Claude Code successfully calls `check_for_conflicts()`
- Risk levels match expectations
- Latency meets targets

## Test Results

Results are saved to `test_results/test_results.json` with:
- Risk level detected
- Latency for each operation
- Success/failure status
- Explanatory messages

```json
[
  {
    "scenario": "Scenario 1",
    "agent_id": "devin-agent",
    "risk_level": "N/A (logger)",
    "latency_ms": 2.34,
    "success": true,
    "message": "Intent registered"
  },
  {
    "scenario": "Scenario 1",
    "agent_id": "claude-code",
    "risk_level": "MEDIUM",
    "latency_ms": 5.67,
    "success": true,
    "message": "Conflicting work detected..."
  }
]
```

## Troubleshooting

### Module Not Found
```bash
cd Neo
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 test_scenarios/dual_agent_test_harness.py
```

### Coordination Log Missing
```bash
mkdir -p .devsync
touch .devsync/coordination.log
```

### Latency High (>10ms)
- Check system load
- Verify no disk I/O bottlenecks
- Run test in isolation mode

## Integration with CI/CD

The test harness can be integrated into CI/CD pipelines:

```bash
# In CI/CD pipeline
python3 test_scenarios/dual_agent_test_harness.py || exit 1

# Check results
cat test_scenarios/test_results/test_results.json | jq '.[] | select(.success==false)'
```

## Next Steps

1. Run the full test suite: `python3 test_scenarios/dual_agent_test_harness.py`
2. Review `test_results/test_results.json` for detailed metrics
3. Compare with baseline latency targets (<10ms)
4. Verify IDE integration points work with actual Devin and Claude Code instances

## References

- [IDE Integration Test Plan](../docs/IDE_INTEGRATION_DUAL_AGENT_TEST.md)
- [IDE Implementation Guide](../docs/IMPLEMENTATION.md)
- [Core Coordination APIs](../core/)
