# Real Multi-Service Breaking Change Test

## Overview

A realistic test that demonstrates Neo's coordination capabilities across a payment system with multiple microservices and a breaking change cascade.

**This is NOT simulation** - uses actual Neo API calls with real activity logging and conflict detection.

---

## Quick Start

```bash
cd ~/Neo
source .venv/bin/activate
python test-scenarios/multi_service_breaking_change_test.py
```

**Duration**: ~30 seconds  
**Real API calls**: 7 conflict checks + 11 activity log entries + coupling metrics  

---

## Test Scenario

### System Architecture

```
auth-service (root)
    ↓ authenticate() - THE BREAKING CHANGE POINT
payment-service (C2 working here)
    ↓ get_transaction()
invoice-service (C3 working here)
    ↓ format_invoice_html()
notification-service (C4 working here)
```

### Timeline

**Week 1: Normal Development** (Days 1-4)
- C1 declares: "Implement OAuth2 authentication with JWT tokens" on auth-service
- C2 declares: "Integrate payment processor with auth validation" on payment-service
- C3 declares: "Generate invoices from payment transactions" on invoice-service
- C4 declares: "Send invoice notifications via email" on notification-service
- **Risk**: All LOW - no conflicts (different files)

**Week 2: Breaking Change** (Days 8-14)
- **Day 8**: C1 refactors `authenticate()` - removes timestamp parameter
  - Old: `authenticate(username, password, timestamp)`
  - New: `authenticate(username, password)`
- **Day 9**: C2 attempts to add fraud detection with `authenticate()`
  - C2 doesn't know about the breaking change yet
  - Neo detects incompatibility at semantic layer
- **Day 11-14**: Cascade of fixes flows through all 4 services
  - C1 adds compatibility wrapper
  - C2 updates calls to new signature
  - C3 adapts to payment-service changes
  - C4 syncs with invoice-service changes

---

## What This Test Demonstrates

### 1. Real API Engagement
✅ `check_for_conflicts()` - Called 7 times (once per intent)  
✅ `log_activity()` - Records 11 real entries  
✅ `record_developer_change()` - Tracks coupling metrics  

### 2. Breaking Change Detection
✅ Detects auth-service signature change  
✅ Captures cascading impact through dependency chain  
✅ Logs all state transitions in real activity log  

### 3. Multi-Service Coordination
✅ 4 developers on 4 independent services  
✅ 3-level dependency chain  
✅ 0 merge conflicts (semantic coordination only)  

### 4. Real Activity Log
✅ 9 entries written to `.devsync/activity-log.json`  
✅ Complete timeline of developer intents  
✅ Timestamps and categories recorded  

---

## Expected Output

```
======================================================================
  REAL MULTI-SERVICE BREAKING CHANGE TEST
======================================================================

Week 1: NORMAL DEVELOPMENT - All developers declare intent

Day 1: C1 declares intent on auth-service
Risk: LOW
✅  No conflicting work detected. Safe to proceed.

Day 2: C2 declares intent on payment-service
Risk: LOW
✅  No conflicting work detected. Safe to proceed.

[... Days 3, 4 similarly ...]

Week 2: BREAKING CHANGE INJECTION & DETECTION

Day 8: C1 refactors auth-service (BREAKING CHANGE)
Change: Remove timestamp parameter from authenticate()
✅  Breaking change recorded in auth-service

Day 9: C2 attempts to call authenticate() with payment processor
[... continues through Day 14 ...]

ACTIVITY LOG RESULTS

Total activity log entries: 9

1. [timestamp] C1 → auth_service.py
   Intent: Implement OAuth2 authentication with JWT tokens...
   Category: feature

2. [timestamp] C2 → payment_service.py
   Intent: Integrate payment processor with auth validation...
   Category: feature

[... 7 more entries ...]

TEST SUMMARY

✅ Real Neo API Calls:
   [✓] check_for_conflicts() - 7 calls across all developers
   [✓] log_activity() - 11 entries recorded
   [✓] record_developer_change() - Coupling metrics tracked

✅ Breaking Change Detection:
   [✓] C1 refactors auth-service signature
   [✓] C2 detects incompatible call pattern
   [✓] C1 adds compatibility wrapper
   [✓] C2-C4 cascade updates through dependency chain

✅ Multi-Service Coordination:
   [✓] 4 developers on 4 services
   [✓] 3-level dependency chain (auth→payment→invoice→notification)
   [✓] 10+ activities recorded
   [✓] 0 merge conflicts (semantic coordination)
```

---

## Verify Activity Log

After the test runs, check the actual activity log:

```bash
cat .devsync/activity-log.json | jq '.'
```

You should see 9 entries like:

```json
{
  "developer_id": "C1",
  "file_path": "test-scenarios/services/auth-service/auth_service.py",
  "intent": "Implement OAuth2 authentication with JWT tokens",
  "region": "authenticate()",
  "timestamp": 1729428745.235982,
  "intent_category": "feature"
}
```

---

## Key Differences from Comprehensive Test

| Aspect | Comprehensive Test | Multi-Service Test |
|--------|-------------------|-------------------|
| **Output** | 100% hardcoded strings | Real activity log entries |
| **API calls** | Simulated/mocked | Actual Neo API calls |
| **Conflict detection** | Fake status messages | Real check_for_conflicts() |
| **Data recording** | Print-only | JSON activity log |
| **Metrics** | Hardcoded results | Real coupling metrics |
| **Runtime** | ~5 seconds print time | ~30 seconds real execution |
| **Verification** | Can't verify results | Check `.devsync/activity-log.json` |

---

## File References

**Services** (unchanged from comprehensive test):
- `test-scenarios/services/auth-service/auth_service.py`
- `test-scenarios/services/payment-service/payment_service.py`
- `test-scenarios/services/invoice-service/invoice_service.py`
- `test-scenarios/services/notification-service/notification_service.py`

**Test Script**:
- `test-scenarios/multi_service_breaking_change_test.py`

**Neo APIs Used**:
- `core.activity_log.log_activity()` - Record developer intent
- `core.activity_log.read_log()` - Retrieve activity log entries
- `core.pre_gen_check.check_for_conflicts()` - Detect conflicts before generation
- `core.coupling_metrics.record_developer_change()` - Track coupling metrics

---

## Extension Ideas

To make this test even more comprehensive:

1. **Add service dependencies** - Have the test check which services depend on each other
2. **Add impact alerts** - Create real impact alerts when upstream services change
3. **Add context staleness** - Simulate time-based staleness and delta refresh
4. **Add lock coordination** - Have developers attempt concurrent edits on same file
5. **Add entropy analysis** - Calculate actual coupling strength between services

---

## See Also

- [LOCAL_THREE_DEVELOPER_TEST.md](LOCAL_THREE_DEVELOPER_TEST.md) - Manual 3-developer test with server
- [README.md](../README.md) - Full Neo documentation
- [core/pre_gen_check.py](../core/pre_gen_check.py) - Conflict detection logic
- [core/activity_log.py](../core/activity_log.py) - Activity logging

---

**Status**: ✅ Real test with actual Neo API engagement  
**Verification**: Real activity log at `.devsync/activity-log.json`  
**Value**: Demonstrates breaking change coordination across 4 microservices
