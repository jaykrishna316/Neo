# Neo Staleness Detection & Auto-Refresh Feature

## Overview

Neo now includes **built-in temporal awareness** through staleness detection and automatic context refresh. This is a core feature, not just a test demonstration.

**What it does**: When activity log entries become too old (>300ms), Neo automatically re-fetches them from disk to ensure conflict decisions are made with current state, not stale cached data.

---

## How It Works

### 1. Staleness Detection (Core Feature)

In `core/pre_gen_check.py`, before checking for conflicts:

```python
# Staleness constants
STALE_THRESHOLD_SECONDS = 0.3  # 300ms

# Automatically detect and refresh stale entries
active_entries, staleness_report = _detect_and_refresh_stale_entries(
    active_entries, 
    resolved_tenant
)
```

**Detection logic:**
- Checks each entry: `entry_age = time.time() - entry['timestamp']`
- If `entry_age > 300ms` → mark as STALE
- Automatically triggers refresh (see below)

### 2. Automatic Refresh

When a stale entry is detected:

```python
# Re-read from activity log disk
all_entries = read_log(tenant_id=tenant_id)

# Find the stale developer's latest entry
for fresh_entry in all_entries:
    if fresh_entry['developer_id'] == stale_developer:
        # Replace stale with fresh
        refreshed_entries[stale_developer] = fresh_entry
```

**Key behaviors:**
- Retries up to 2 times on failure
- Captures status changes: `working` → `completed`
- Replaces stale entries before conflict analysis
- Logs refresh events for audit

### 3. System Logging

Staleness events are logged as system entries:

```json
{
  "developer_id": "_neo_system",
  "intent_category": "system",
  "agent_metadata": {
    "system_event": "staleness_detection",
    "stale_count": 3,
    "refresh_count": 3,
    "details": [
      {
        "developer_id": "alice-devin",
        "entry_age_ms": 523.5,
        "status_before": "working",
        "status_after": "completed",
        "refresh_attempt": 1
      }
    ]
  }
}
```

---

## Why This Matters

### Before (No Staleness Detection)
```
Bob checks conflicts at t=0
  - Reads Alice's entry (timestamp: t=-500ms)
  - Alice's status: "working"
  - Decision: Lock applied, Bob waits

Alice completes at t=100ms
  - Logs completion, status: "completed"

Bob checks conflicts again at t=200ms
  - Reads same cached entry (still says "working")
  - Doesn't know Alice finished!
  - Unnecessary wait
```

### After (With Staleness Detection)
```
Bob checks conflicts at t=0
  - Reads Alice's entry (timestamp: t=-500ms)
  - Entry age: 500ms > 300ms threshold → STALE!
  - Core AUTO-REFRESHES from disk
  - If Alice completed, status is updated to "completed"
  - Decision based on CURRENT state, not old cached data
```

---

## Integration Points

### In `check_for_conflicts()` (Main Conflict API)

```python
# Line ~40 in core/pre_gen_check.py
active_entries, staleness_report = _detect_and_refresh_stale_entries(
    active_entries, 
    resolved_tenant
)

# All subsequent conflict checks use refreshed entries
```

### Staleness Reports

Available in the return value when needed (future enhancement):
- `stale_count`: How many entries were stale
- `refresh_count`: How many successfully refreshed
- `details`: Per-entry refresh history

---

## Testing

### Test Files

1. **`tests/devin_staleness_test.py`** - Demonstrates feature in action
   - Alice works for 15 seconds
   - Bob polls every 500ms, observes staleness growing
   - Shows stale detection and core auto-refresh

2. **`tests/devin_multi_agent_test.py`** - Uses core feature implicitly
   - Staleness handled transparently in core
   - No special test code needed

### How to Test

```bash
# Terminal 1: Alice works for 15 seconds
python3 tests/devin_staleness_test.py alice

# Terminal 2: Bob watches for staleness
python3 tests/devin_staleness_test.py bob
```

You'll see Bob's output like:
```
[1.0s] STALE DETECTED: 523ms old | Status: working
       (Core auto-refreshes this)
[2.0s] STALE DETECTED: 1023ms old | Status: working
       (Core auto-refreshes this)
[15.2s] Lock status: LOW (Alice completed, refresh detected it)
```

---

## Configuration

### Adjust Staleness Threshold

In `core/pre_gen_check.py`:

```python
STALE_THRESHOLD_SECONDS = 0.3  # 300ms (default)

# For stricter staleness detection:
STALE_THRESHOLD_SECONDS = 0.1  # 100ms

# For more lenient detection:
STALE_THRESHOLD_SECONDS = 0.5  # 500ms
```

### Adjust Refresh Attempts

```python
MAX_REFRESH_ATTEMPTS = 2  # Current default

# For more aggressive refresh:
MAX_REFRESH_ATTEMPTS = 3
```

---

## Future Enhancements

1. **Metrics & Monitoring**
   - Track staleness frequency per developer
   - Alert if staleness is happening too often (sign of slow disk/I/O)

2. **Adaptive Thresholds**
   - Adjust staleness threshold based on observed latencies
   - Faster systems can use lower thresholds

3. **Caching Strategy**
   - Cache entries for short durations (~100ms)
   - Only refresh on staleness or explicit invalidation

4. **Observability**
   - Export staleness metrics to monitoring system
   - Dashboard showing staleness patterns over time

---

## Status

✅ **Feature**: Built-in to core Neo  
✅ **Location**: `core/pre_gen_check.py`  
✅ **Integration**: Automatic in all conflict checks  
✅ **Testing**: Demonstrated in `devin_staleness_test.py`  
✅ **Auditability**: System events logged for inspection  

**Result**: Neo now has temporal awareness. It knows when data is stale and automatically refreshes it before making decisions. ✨
