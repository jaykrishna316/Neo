# Developer Count Fix - Neo 4.0

## Issue
When a single developer (Alice) worked on a file, the developer count would incorrectly show 2 instead of 1:

```
✅ [01:43:16] alice → src/auth.py
   Risk: LOW (developers on file: 1)    ← Correct

🔒 [01:43:23] alice → src/auth.py
   Risk: MEDIUM (developers on file: 2)  ← INCORRECT - should be 1
```

## Root Cause
The activity log stores each developer action as a separate entry:
1. First entry: Alice declares intent ("Add OAuth2 authentication")
2. Second entry: File watcher detects Alice's changes ("Working on src/auth.py")

The server was previously counting ENTRIES instead of UNIQUE DEVELOPERS.

## Solution
Count unique developer IDs, not the number of entries:

```python
# Before (WRONG):
same_file_count = len(entries)  # Counts 2 entries

# After (CORRECT):
developers_on_file = set([e.get('developer_id') for e in entries if e.get('file_path') == file_path])
same_file_count = len(developers_on_file)  # Counts 1 unique developer
```

**File**: `cli/neo_server.py` (lines 160-163)  
**Commit**: `efa976a - Fix developer count to count unique developers, not entries`

## Verification

### Test Results
All 14 tests pass:
- ✅ 9/9 explicit lock tests
- ✅ 5/5 optimization tests

### Tested Scenarios

**Scenario 1: Single Developer (Alice)**
- Alice declares intent on `src/auth.py` → 1 developer ✅
- File watcher logs for Alice → still 1 developer ✅
- Risk correctly shows: LOW ✅

**Scenario 2: Two Developers**
- Alice declares + file watcher logs → 1 developer ✅
- Bob declares on same file → 2 developers ✅
- Risk correctly shows: MEDIUM ✅
- Lock mechanism works: Alice holds lock, Bob queued ✅

**Scenario 3: Three Developers**
- Alice, Bob, Charlie all work on same file
- Correct developer count at each step
- Lock queue properly maintained ✅

## Impact
- ✅ Fixes false MEDIUM/HIGH risk warnings for single developers
- ✅ Improves user experience with accurate conflict detection
- ✅ Maintains backward compatibility with existing workflows
- ✅ No changes to activity log format or API

## Files Modified
- `cli/neo_server.py` - Developer counting logic (line 162)

## Rollout Status
✅ **READY FOR PRODUCTION** - All tests passing, verified on neo-4.0 branch
