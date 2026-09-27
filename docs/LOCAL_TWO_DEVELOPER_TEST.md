# Neo Local Two-Developer Test

Complete guide to testing Neo with two developers using the local coordination server.

## Overview

This setup allows you to test Neo's multi-developer coordination **without Claude Code IDE**, using only:
- A local Neo coordination server
- File watchers to detect changes
- Terminal output showing conflicts and locks in real-time

Two developers working on the same machine (or networked machines) can coordinate their work automatically.

---

## Setup

### Prerequisites

```bash
pip install watchdog requests
```

### Initialize Test Repository

```bash
cd /path/to/Neo
# Create test directories if they don't exist
mkdir -p .devsync src lib
```

---

## Workflow

### Terminal 1: Start the Neo Server

```bash
python -m cli.neo_server --clear
```

Output:
```
============================================================
🚀 Neo Local Coordination Server
============================================================

📍 Server running at http://localhost:8000
📝 Activity log: .devsync/activity-log.json
⏰ Started: 2026-09-27 10:15:30

============================================================
Developers can now declare intent and check conflicts.
Messages will appear below.

```

The server now:
- Manages `.devsync/activity-log.json`
- Listens for conflict checks on port 8000
- Prints all activity to terminal

---

### Terminal 2: Developer A - Watch for Changes

First, set the developer context environment variable:

```bash
export NEO_DEVELOPER=alice
python -m cli.file_watcher alice --server http://localhost:8000
```

Output:
```
============================================================
👁️  Neo File Watcher
============================================================

👤 Watcher Agent ID: alice
📍 Server: http://localhost:8000
📂 Watching: .
⏰ Started: 2026-09-27 10:15:45

✅ Developer context: NEO_DEVELOPER=alice
   File changes will be logged as this developer

REQUIRED: Declare intent before editing
Before editing, run:
  neo declare alice src/auth.py 'Your intent here'

Press Ctrl+C to stop watcher.

```

**Important**: The `NEO_DEVELOPER=alice` environment variable ensures that only alice's watcher logs alice's changes (prevents double-logging when multiple watchers are running).

Now, when alice edits files in `src/` or `lib/`, they'll be detected by this watcher.

---

### Terminal 3: Developer B - Watch for Changes

Set the developer context for bob:

```bash
export NEO_DEVELOPER=bob
python -m cli.file_watcher bob --server http://localhost:8000
```

Same setup, but with `NEO_DEVELOPER=bob` so bob's changes are tracked by bob's watcher only.

---

### Terminal 4: Developer A - Declare Intent First

Before editing, alice must declare intent:

```bash
python -m cli.neo_client declare alice src/auth.py "Add OAuth2 authentication" --category feature
```

Output:
```
✅ Intent Declared
   Developer: alice
   File: src/auth.py
   Developers on file: 1
```

### Terminal 4 (continued): Developer A - Make Changes

Now edit the file:

```bash
# Edit src/auth.py
cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """Authenticate user with bcrypt"""
    # Alice is adding OAuth2 support here
    pass
EOF
```

Terminal 1 (Server) shows:
```
✅ [10:16:22] alice → src/auth.py
   Intent: Working on src/auth.py
   Risk: LOW (developers on file: 1)
```

---

### Terminal 5: Developer B - Tries to Edit Same File

```bash
# Bob tries to edit the same file
cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """Authenticate user with JWT tokens"""
    # Bob is adding JWT support here
    pass
EOF
```

Terminal 1 (Server) shows:
```
⚠️ [10:16:45] bob - Conflict Check
   Risk: MEDIUM
   MEDIUM RISK: alice is Working on src/auth.py. Overlapping regions detected. Proceed with caution.
   🔒 Lock Status:
      Holder: alice
      Queue Position: 0
      Waiting For: alice
```

Bob is now **queued** with position 0, waiting for alice to complete.

---

### Terminal 4: Developer A - Completes Work

Alice finishes and commits:

```bash
git add src/auth.py
git commit -m "Add OAuth2 authentication"
```

When alice's file watcher stops or the developer marks completion, bob is **promoted**.

Terminal 1 (Server) shows:
```
✅ [10:17:15] alice completed: +20 lines, -5 lines
🔓 Lock released, promoting bob
```

Terminal 5 (Bob's watcher) shows:
```
✅ [10:17:16] bob - Lock Released!
   Now active! Lock acquired.
   Safe to proceed.
```

---

### Terminal 5: Developer B - Proceeds

Bob can now edit the same file without conflict:

```bash
# Bob continues his work
cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """Authenticate user with OAuth2 + JWT"""
    # Building on Alice's work
    pass
EOF
```

Terminal 1 (Server) shows:
```
✅ [10:17:30] bob → src/auth.py
   Intent: Working on src/auth.py
   Risk: LOW (developers on file: 1)
```

---

## Manual Commands (Alternative to Watchers)

If you prefer to manually declare intent instead of using watchers:

### Check for Conflicts

```bash
python -m cli.neo_client check alice src/auth.py "Add OAuth2 support"
```

Output:
```
✅ Conflict Check Result
   Risk: LOW
   No conflicting work detected. Safe to proceed.
```

### Declare Intent

```bash
python -m cli.neo_client declare alice src/auth.py "Add OAuth2 support" --category feature
```

Output:
```
✅ Intent Declared
   Developer: alice
   File: src/auth.py
   Developers on file: 1
```

### View Activity Log

```bash
python -m cli.neo_client log
```

Output:
```
📝 Activity Log (4 entries)
   [2026-09-27T10:16:22] alice → src/auth.py
      Working on src/auth.py
   [2026-09-27T10:16:45] bob → src/auth.py
      Working on src/auth.py
   ...
```

### Check Server Status

```bash
python -m cli.neo_client status
```

Output:
```
✅ Neo Server Status
   Status: ok
   Version: 4.0
   Activity Log: .devsync/activity-log.json
```

---

## Three-Developer Test

Add a third developer easily:

### Terminal 6: Developer C - Watch for Changes

```bash
python -m cli.file_watcher charlie --server http://localhost:8000
```

Now:
1. Alice works on `src/auth.py` (lock acquired)
2. Bob tries same file (queued at position 0)
3. Charlie tries same file (queued at position 1)

Server output:
```
⚠️ [10:18:00] charlie - Conflict Check
   Risk: MEDIUM
   🔒 Lock Status:
      Holder: alice
      Queue Position: 1
      Waiting For: bob
```

When alice completes → bob promoted → when bob completes → charlie promoted.

---

## Testing Lock Behavior

### Test 1: Simple Lock (2 Devs)

1. Alice edits `src/auth.py` → LOW risk ✅
2. Bob edits same file → MEDIUM risk ⚠️ (queued)
3. Alice completes → Bob promoted ✅

### Test 2: Queue Management (3+ Devs)

1. Alice on `src/auth.py` → LOW ✅
2. Bob on `src/auth.py` → MEDIUM ⚠️ (position 0)
3. Charlie on `src/auth.py` → MEDIUM ⚠️ (position 1)
4. Alice completes → Bob promoted
5. Bob completes → Charlie promoted

### Test 3: File Isolation (No Lock)

1. Alice on `src/auth.py` → LOW ✅
2. Bob on `src/database.py` → LOW ✅ (different file, no lock!)
3. Charlie on `lib/utils.py` → LOW ✅ (parallel work, no conflicts)

---

## Understanding Terminal Output

### Icons in Messages

| Icon | Meaning |
|------|---------|
| ✅ | Success, safe to proceed (LOW risk) |
| ⚠️ | Warning, conflicts detected (MEDIUM risk) |
| 🚫 | Blocked, high conflict (HIGH risk) |
| 🔒 | Lock active, queued developers |
| 🔓 | Lock released, next developer promoted |
| 👁️ | File watcher active |
| 🚀 | Server started |

### Server Output Sections

```
✅ [10:16:22] alice → src/auth.py
   Intent: Working on src/auth.py
   Risk: LOW (developers on file: 1)
```

- **✅** = Status icon
- **[10:16:22]** = Timestamp
- **alice** = Developer ID
- **Risk: LOW** = Conflict risk level
- **(developers on file: 1)** = Number of developers on this file

---

## Developer Context Validation

### Why NEO_DEVELOPER and Intent Declaration?

When multiple file watchers are running simultaneously (alice's watcher in Terminal 2 and bob's watcher in Terminal 3), both watchers detect file changes in Terminal 4. Without developer context validation, **both watchers would log the same change with their own agent_id**, making it impossible to determine who actually made the edit.

### How It Works

Neo solves this with two mechanisms working together:

**1. NEO_DEVELOPER Environment Variable**
```bash
export NEO_DEVELOPER=alice
python -m cli.file_watcher alice --server http://localhost:8000
```

- Each watcher checks if `NEO_DEVELOPER` matches its own `agent_id`
- If it matches: the watcher processes and logs the change
- If it doesn't match: the watcher **silently ignores** the change (allows other watchers to handle it)
- If not set: the watcher warns the developer and remains inactive

**2. Intent Declaration Before Editing**
```bash
python -m cli.neo_client declare alice src/auth.py "Add OAuth2 authentication"
```

- Before a file can be logged, the developer must declare intent
- The watcher verifies intent was declared before allowing logs
- If no intent: the watcher blocks the edit and prompts the developer with the required command
- This prevents accidental logging and ensures explicit developer intent

### Example Workflow

```
Terminal 2 (Alice's watcher):
  $ export NEO_DEVELOPER=alice
  $ python -m cli.file_watcher alice --server http://localhost:8000
  ✅ Developer context: NEO_DEVELOPER=alice

Terminal 3 (Bob's watcher):
  $ export NEO_DEVELOPER=bob
  $ python -m cli.file_watcher bob --server http://localhost:8000
  ✅ Developer context: NEO_DEVELOPER=bob

Terminal 4 (Editing):
  $ python -m cli.neo_client declare alice src/auth.py "Add OAuth2"
  ✅ Intent Declared
  
  $ vim src/auth.py  # Make changes
  # Alice's watcher logs the change (NEO_DEVELOPER=alice matches)
  # Bob's watcher ignores it (NEO_DEVELOPER=bob doesn't match)
  
  Result: Only alice's watcher logs alice's work
```

---

## Troubleshooting

### Server Connection Failed

**Error:** `Cannot connect to Neo server at http://localhost:8000`

**Solution:** Make sure the server is running in Terminal 1:
```bash
python -m cli.neo_server --clear
```

### File Watcher Not Detecting Changes

**Problem:** Changes aren't being logged

**Causes and Solutions:**
1. **NEO_DEVELOPER not set or mismatched**
   ```bash
   # Check if environment variable is set
   echo $NEO_DEVELOPER
   
   # Set it correctly before starting the watcher
   export NEO_DEVELOPER=alice
   python -m cli.file_watcher alice --server http://localhost:8000
   ```

2. **Intent not declared**
   ```bash
   # Declare intent before editing
   python -m cli.neo_client declare alice src/auth.py "Your intent here"
   ```

3. **Files not in watched directories**
   - Make sure you're editing files in `src/` or `lib/` directories
   - Other directories are not watched by default

4. **File didn't actually change**
   - Verify the file content actually changed (not just opened/closed)
   - Hash-based detection prevents duplicate logs of the same content

### Edit Blocked: "No intent declared"

**Problem:** Watcher shows error: `Edit blocked for {file_path}. No intent declared by {agent_id}`

**Solution:** Declare intent before editing:
```bash
python -m cli.neo_client declare alice src/auth.py "Your intent here"
```

This prevents accidental logging and ensures explicit developer intent.

### Activity Log Not Clearing

**Problem:** Previous test data still showing

**Solution:** Clear on server startup:
```bash
python -m cli.neo_server --clear
```

Or manually:
```bash
rm .devsync/activity-log.json
```

---

## Full Test Scenario

### Setup (5 minutes)

```bash
# Terminal 1: Server
python -m cli.neo_server --clear

# Terminal 2: Alice watches
python -m cli.file_watcher alice

# Terminal 3: Bob watches
python -m cli.file_watcher bob

# Terminal 4 & 5: Ready for editing
```

### Scenario (10 minutes)

1. **10:15** - Alice edits `src/auth.py` (LOW risk)
2. **10:16** - Bob tries same file (MEDIUM risk, queued)
3. **10:20** - Alice commits, lock released
4. **10:20** - Bob promoted, starts editing
5. **10:25** - Bob commits, completes
6. **Result:** 2 developers, 0 conflicts, sequential coordination ✅

### Verification

```bash
# Check final state
python -m cli.neo_client log
```

Should show:
- 2 developers (alice, bob)
- Same file (`src/auth.py`)
- Sequential work (alice → bob)
- No conflicts recorded

---

## Next Steps

- **Test with 3+ developers** for queue behavior
- **Test different files** for parallel (no-lock) work
- **Test rapid declarations** to see conflict detection
- **Monitor performance** with large activity logs

For production use with Claude Code IDE, see `docs/NEO_4.0_OPENAPI_SPECIFICATION.md`.

---

**Last Updated:** 2026-09-27  
**Neo Version:** 4.0  
**Status:** Ready for Local Testing
