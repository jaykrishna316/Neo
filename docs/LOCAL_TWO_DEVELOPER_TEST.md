# Neo Terminal-Based Two-Developer Test

**For developers using regular terminal (Vim, VS Code, etc.) without Claude Code IDE**

Complete guide to testing Neo with two developers using a **local coordination server**. This approach works with **any editor** (Vim, Emacs, VS Code, etc.) and doesn't require Claude Code IDE.

## Overview

This setup allows you to test Neo's multi-developer coordination **without Claude Code IDE**, using only:
- A local Neo coordination server (runs on `localhost:8000`)
- File watchers to detect code changes automatically
- Terminal output showing conflicts and locks in real-time
- Manual intent declaration via CLI commands

Two developers working on the same machine (or networked machines) can coordinate their work automatically using standard terminal tools.

### When to Use This Approach

✅ **Use terminal-based testing when:**
- Testing without Claude Code IDE
- Running on shared servers or remote machines
- Integrating Neo into CI/CD pipelines
- Testing with standard Unix/Linux tools
- Running multiple developers on same terminal server

❌ **Use Claude Code IDE instead when:**
- Developers are using Claude Code IDE for generation
- You want automatic conflict checking before generation
- You need pre-generation conflict prevention (token efficiency)
- You want IDE-native workflow integration

See `CLAUDE_CODE_TWO_DEVELOPER_TEST.md` for IDE-based testing.

---

## Architecture (Terminal-Based)

```
Terminal 1: Neo Server (localhost:8000)
    ↓
    Manages: .devsync/activity-log.json
    Prints: ✅/⚠️/🚫 status messages

Terminal 2: Alice's File Watcher (NEO_DEVELOPER=alice)
    ↓
    Detects: Changes to src/ and lib/
    Verifies: Intent declared, NEO_DEVELOPER=alice
    Logs: To server via HTTP /api/log-activity

Terminal 3: Bob's File Watcher (NEO_DEVELOPER=bob)
    ↓
    Detects: Changes to src/ and lib/
    Verifies: Intent declared, NEO_DEVELOPER=bob
    Logs: To server via HTTP /api/log-activity

Terminal 4+: Developers Edit Code (Vim, VS Code, etc.)
    ↓
    Alice or Bob makes changes
    Matching watcher detects & logs
    Server prints conflict status to Terminal 1
```

---

## Setup

### Prerequisites

Install dependencies:

```bash
cd ~/Neo
.venv/bin/pip install -r requirements.txt
```

**Note**: `~/Neo` refers to your Neo project directory. If you cloned it elsewhere, use the correct path. On Mac it's typically `/Users/yourname/Neo` or `~/Neo`. On Linux it's typically `/home/yourname/Neo` or `~/Neo`.

This installs:
- `watchdog>=3.0` - File system monitoring
- `requests>=2.28` - HTTP client for Neo server
- Other Neo dependencies

### Initialize Test Repository

```bash
cd ~/Neo
# Create test directories if they don't exist
mkdir -p .devsync src lib
```

Create sample files to edit:

```bash
# Create initial files
cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """Authenticate user with password."""
    pass
EOF

cat > src/database.py << 'EOF'
def connect_database():
    """Connect to database."""
    pass
EOF
```

---

## Two-Developer Test Workflow

### Terminal 1: Start the Neo Server

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_server --clear
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
- Prints all activity to terminal with DEBUG information

**DEBUG Output**: Each log line includes a DEBUG line (starting with `DEBUG:`) showing the calculation details. This is helpful for verification and troubleshooting:

```
DEBUG: entries=['alice'], developers_on_file={'alice'}, same_file_count=1
```

- `entries=` shows the full list of developer IDs in the activity log for that file
- `developers_on_file=` shows the unique developers (set notation - no duplicates)
- `same_file_count=` is the final developer count (matches the "developers on file: N" in the status)

---

### Terminal 2: Developer A - Watch for Changes

First, set the developer context environment variable:

```bash
cd ~/Neo
export NEO_DEVELOPER=alice
.venv/bin/python3 -m cli.file_watcher alice --server http://localhost:8000
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
cd ~/Neo
export NEO_DEVELOPER=bob
.venv/bin/python3 -m cli.file_watcher bob --server http://localhost:8000
```

Same setup, but with `NEO_DEVELOPER=bob` so bob's changes are tracked by bob's watcher only.

---

### Prerequisite Check: Verify Activity Log is Empty

Before starting the test, ensure the activity log is clean:

```bash
cd ~/Neo
cat .devsync/activity-log.json
```

**Expected output:**
```
[]
```

If you see entries from a previous test, clear the log:

```bash
cd ~/Neo
rm .devsync/activity-log.json
```

Then restart the server:
```bash
.venv/bin/python3 -m cli.neo_server --clear
```

This ensures a fresh start with no lingering entries from previous runs.

---

### Terminal 4: Developer A - Declare Intent First

Before editing, alice must declare intent:

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2 authentication" --category feature
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

### Terminal 5: Developer B - Declare Intent First

**IMPORTANT**: Bob must declare intent BEFORE editing, just like alice did:

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare bob src/auth.py "Add JWT token support" --category feature
```

Output:
```
✅ Intent Declared
   Developer: bob
   File: src/auth.py
   Developers on file: 2
```

Notice: Now it shows **2 developers on file** (alice and bob) — the lock mechanism will activate!

---

### Terminal 5 (continued): Developer B - Tries to Edit Same File

Now bob edits the file:

```bash
cd ~/Neo
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

Alice finishes editing and marks work as complete:

```bash
cd ~/Neo
# First commit the changes
git add src/auth.py
git commit -m "Add OAuth2 authentication"

# Then mark work complete to release lock (in Terminal 4 or new terminal)
.venv/bin/python3 -m cli.neo_client complete alice src/auth.py --added 5 --removed 1
```

Terminal 1 (Server) shows:
```
✅ [10:17:15] alice completed: +5 lines, -1 lines
   File: src/auth.py
   🔓 Lock released, promoting next developer
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
cd ~/Neo
.venv/bin/python3 -m cli.neo_client check alice src/auth.py "Add OAuth2 support"
```

Output:
```
✅ Conflict Check Result
   Risk: LOW
   No conflicting work detected. Safe to proceed.
```

### Declare Intent

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2 support" --category feature
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
cd ~/Neo
.venv/bin/python3 -m cli.neo_client log
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
cd ~/Neo
.venv/bin/python3 -m cli.neo_client status
```

Output:
```
✅ Neo Server Status
   Status: ok
   Version: 4.0
   Activity Log: .devsync/activity-log.json
```

---

### Step 6: Developer B Completes - Developer A Gets Fresh Context

When bob completes work and releases the lock:

```bash
# Terminal 5 (or separate terminal)
cd ~/Neo
.venv/bin/python3 -m cli.neo_client complete bob src/auth.py --added 10 --removed 2
```

Server output (Terminal 1):
```
✅ [10:20:45] bob completed: +10 lines, -2 lines
   File: src/auth.py
   🔓 Lock released, promoting next developer
```

Terminal 4 (Alice's watcher) shows:
```
✅ [10:20:45] alice - Lock Released!
   You are now ACTIVE on src/auth.py
   bob's work is complete. Ready to proceed.
```

**Alice should now review bob's changes before continuing:**

```bash
# Terminal 4: Check activity log to see what bob did
cd ~/Neo
.venv/bin/python3 -m cli.neo_client log
```

Output:
```
📝 Activity Log (entries with bob's work)
   [2026-09-27T10:04:35] alice → src/auth.py
      Add OAuth2 authentication
   [2026-09-27T10:04:56] bob → src/auth.py
      Add JWT token support
   [2026-09-27T10:13:28] bob completed: +10 lines, -2 lines
      JWT implementation complete
   [2026-09-27T10:20:45] alice → src/auth.py
      (alice can now proceed with bob's context)
```

**Then pull latest code:**

```bash
# Pull bob's changes from git
git pull origin main
```

This ensures alice has:
- ✅ Bob's code changes
- ✅ Bob's context (activity log showing what he did)
- ✅ Fresh lock state (she now holds the lock)

---

## How It Works: The Coordination Flow

### Without NEO_DEVELOPER & Intent Declaration (Broken)

```
Alice edits src/auth.py
    ↓
Both alice_watcher and bob_watcher detect change
    ↓
Both attempt to log with their own agent_id
    ↓
Activity log is ambiguous: who actually edited?
    ↓
❌ RESULT: Hard-coded sequential testing, not true multi-developer
```

### With NEO_DEVELOPER & Intent Declaration (Fixed)

```
Alice declares intent:
  neo declare alice src/auth.py "Add OAuth2"
    ↓
Activity log records: alice has declared intent on src/auth.py

Alice edits src/auth.py
    ↓
both alice_watcher and bob_watcher detect change
    ↓
alice_watcher checks:
  ✅ NEO_DEVELOPER=alice (matches her watcher)
  ✅ Intent declared for alice on src/auth.py
  → LOGS the change
    ↓
bob_watcher checks:
  ❌ NEO_DEVELOPER=bob (doesn't match, is alice)
  → SILENTLY IGNORES (lets alice_watcher handle it)
    ↓
✅ RESULT: Only alice's watcher logs alice's work. True multi-developer!
```

### Data Flow in Activity Log

```json
{
  "developer_id": "alice",
  "file_path": "src/auth.py",
  "intent": "Add OAuth2 authentication",
  "intent_category": "feature",
  "timestamp": 1695164017.5,
  "lock_state": "ACQUIRED",
  "lock_holder": "alice",
  "queue_position": null,
  "waiting_for": null
}
```

When bob tries the same file:

```json
{
  "developer_id": "bob",
  "file_path": "src/auth.py",
  "intent": "Add JWT token support",
  "intent_category": "feature",
  "timestamp": 1695164045.2,
  "lock_state": "WAITING",
  "lock_holder": "alice",
  "queue_position": 0,
  "waiting_for": "alice"
}
```

---

## Three-Developer Test Workflow

**Scenario**: Alice, Bob, and Charlie are all working on the same file with locks and queue management.

This tests Neo's **queue promotion** mechanism - ensuring developers are notified in order and can proceed safely without conflicts.

### Setup: Three Watchers Running

#### Terminal 4: Developer C - Watch for Changes

First, set developer context:

```bash
cd ~/Neo
export NEO_DEVELOPER=charlie
.venv/bin/python3 -m cli.file_watcher charlie --server http://localhost:8000
```

Output:
```
============================================================
👁️  Neo File Watcher
============================================================

👤 Watcher Agent ID: charlie
📍 Server: http://localhost:8000
📂 Watching: .
⏰ Started: 2026-09-27 10:18:00

✅ Developer context: NEO_DEVELOPER=charlie
   File changes will be logged as this developer

REQUIRED: Declare intent before editing
Before editing, run:
  neo declare charlie src/auth.py 'Your intent here'

Press Ctrl+C to stop watcher.
```

Now you have:
- Terminal 2: alice's watcher (NEO_DEVELOPER=alice)
- Terminal 3: bob's watcher (NEO_DEVELOPER=bob)
- Terminal 4: charlie's watcher (NEO_DEVELOPER=charlie)
- Terminal 5: Server (printing status messages)

### Workflow: Sequential Queue Management

#### Step 1: Alice Declares Intent (Lock = ALICE)

**Terminal 5 (or separate terminal)**:
```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2 authentication"
```

**Server output (Terminal 1)**:
```
✅ [10:18:15] alice → src/auth.py
   Intent: Add OAuth2 authentication
   Risk: LOW (developers on file: 1)
```

**State**:
- ✅ alice: ACTIVE (lock holder)
- ❌ bob: not yet involved
- ❌ charlie: not yet involved

#### Step 2: Bob Declares Intent (Queued at Position 0)

**Terminal 5**:
```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare bob src/auth.py "Add JWT token support"
```

**Server output (Terminal 1)**:
```
⚠️ [10:18:30] bob - Conflict Check
   Risk: MEDIUM
   MEDIUM RISK: alice is Working on src/auth.py
   Overlapping regions detected.
   🔒 Lock Status:
      Holder: alice
      Queue Position: 0
      Waiting For: alice
```

**State**:
- ✅ alice: ACTIVE (lock holder)
- ⏳ bob: WAITING (queue position: 0)
- ❌ charlie: not yet involved

#### Step 3: Charlie Declares Intent (Queued at Position 1)

**Terminal 5**:
```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare charlie src/auth.py "Add multi-factor authentication"
```

**Server output (Terminal 1)**:
```
⚠️ [10:18:45] charlie - Conflict Check
   Risk: MEDIUM
   MEDIUM RISK: alice is Working on src/auth.py
   Overlapping regions detected.
   🔒 Lock Status:
      Holder: alice
      Queue Position: 1
      Waiting For: bob
```

**State**:
- ✅ alice: ACTIVE (lock holder)
- ⏳ bob: WAITING (queue position: 0, next in line)
- ⏳ charlie: WAITING (queue position: 1, behind bob)

Notice:
- Bob's "Waiting For" = alice
- Charlie's "Waiting For" = bob
- Queue is ordered: alice → bob → charlie

#### Step 4: Alice Completes (Bob Promoted)

Alice finishes OAuth2 work and completes:

**Terminal 5**:
```bash
cd ~/Neo
# Alice marks work complete
.venv/bin/python3 -m cli.neo_client log
# View the updated activity log to confirm alice is complete
```

**Server output (Terminal 1)**:
```
✅ [10:19:00] alice completed: +45 lines, -5 lines
🔓 Lock released, promoting bob
```

**Immediate notification to Bob**:
```
✅ [10:19:00] bob - Lock Released!
   You are now ACTIVE on src/auth.py
   
   alice's work is complete. Queue position: 0 → ACTIVE
   Ready to proceed with JWT support.
```

**State**:
- ✅ alice: COMPLETED
- ✅ bob: ACTIVE (newly promoted, now lock holder)
- ⏳ charlie: WAITING (queue position: 0, waiting for bob)

#### Step 5: Bob Gets Fresh Context from Alice

Bob should review what Alice accomplished before generating:

**Terminal 5**:
```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client log
```

Output shows:
```
📝 Activity Log (3 entries)
   [2026-09-27T10:18:15] alice → src/auth.py
      Add OAuth2 authentication
   [2026-09-27T10:19:00] alice completed: +45 lines, -5 lines
   [2026-09-27T10:18:30] bob → src/auth.py
      Add JWT token support
```

Bob reads this context before generating JWT code.

#### Step 6: Bob Edits File (Charlie Waiting)

Bob makes changes to implement JWT:

**Terminal 6 (editing)**:
```bash
vim src/auth.py
# Bob adds JWT implementation on top of Alice's OAuth2
```

**Server sees**:
```
✅ [10:19:15] bob → src/auth.py
   Intent: Add JWT token support
   Risk: LOW (developers on file: 1)
   
   Note: 1 developer waiting (charlie)
```

Charlie's watcher shows:
```
⏳ [10:19:15] charlie - Still waiting...
   Queue Position: 0
   Waiting For: bob (currently editing)
```

#### Step 7: Bob Completes (Charlie Promoted)

Bob finishes JWT implementation:

**Terminal 5**:
```bash
.venv/bin/python3 -m cli.neo_client log
```

**Server output (Terminal 1)**:
```
✅ [10:19:45] bob completed: +60 lines, -10 lines
🔓 Lock released, promoting charlie
```

**Immediate notification to Charlie**:
```
✅ [10:19:45] charlie - Lock Released!
   You are now ACTIVE on src/auth.py
   
   bob's work is complete. Queue position: 0 → ACTIVE
   Ready to proceed with multi-factor authentication.
```

**State**:
- ✅ alice: COMPLETED
- ✅ bob: COMPLETED
- ✅ charlie: ACTIVE (newly promoted, now lock holder)

#### Step 8: Charlie Gets Context from Both

Charlie reviews what both Alice and Bob accomplished:

**Terminal 5**:
```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client log
```

Output shows full history:
```
📝 Activity Log (5 entries)
   [2026-09-27T10:18:15] alice → src/auth.py
      Add OAuth2 authentication
   [2026-09-27T10:19:00] alice completed: +45 lines, -5 lines
   [2026-09-27T10:18:30] bob → src/auth.py
      Add JWT token support
   [2026-09-27T10:19:45] bob completed: +60 lines, -10 lines
   [2026-09-27T10:18:45] charlie → src/auth.py
      Add multi-factor authentication
```

Charlie sees:
- OAuth2 foundation (alice)
- JWT tokens (bob)
- Can now add MFA on top of both

#### Step 9: Charlie Edits File

Charlie implements MFA with full context:

**Terminal 6 (editing)**:
```bash
vim src/auth.py
# Charlie adds MFA that works with Alice's OAuth2 + Bob's JWT
```

**Server output (Terminal 1)**:
```
✅ [10:20:00] charlie → src/auth.py
   Intent: Add multi-factor authentication
   Risk: LOW (developers on file: 1)
   
   Note: Build on alice's OAuth2 + bob's JWT
```

#### Step 10: Charlie Completes (All Done)

**Terminal 5**:
```bash
.venv/bin/python3 -m cli.neo_client log
```

**Server output (Terminal 1)**:
```
✅ [10:20:45] charlie completed: +75 lines, -15 lines
🔓 Lock released

🎉 All developers complete on src/auth.py!
   - alice: OAuth2 (45 lines)
   - bob: JWT (60 lines)
   - charlie: MFA (75 lines)
   Total: 180 lines added, 30 lines removed
```

**Final State**:
```
✅ alice: COMPLETED
✅ bob: COMPLETED
✅ charlie: COMPLETED

Activity Log:
  - 7 entries total
  - 3 developers tracked
  - Sequential coordination: alice → bob → charlie
  - No conflicts detected
  - No re-generations needed
```

### What Queue Management Proves

| Aspect | Behavior | Verified |
|--------|----------|----------|
| **Lock Acquisition** | First developer gets lock | ✅ alice acquired lock |
| **Queue Ordering** | Developers queued in order | ✅ bob (pos 0) before charlie (pos 1) |
| **Waiting For** | Each dev knows who they're waiting for | ✅ bob waits for alice, charlie waits for bob |
| **Auto-Promotion** | Next in queue promoted when holder completes | ✅ bob promoted when alice completed |
| **Context Chain** | Each dev has full context before starting | ✅ charlie saw alice + bob's work |
| **No Conflicts** | Sequential coordination prevents conflicts | ✅ Zero conflicts, zero re-gens |

---

## Summary: 2-Dev vs 3-Dev Tests

### Two-Developer Test
- **Setup**: 5 minutes
- **Test**: 10 minutes
- **Validates**:
  - Lock creation and release
  - Queue management (position 0)
  - Context refresh between developers
  - Simple conflict detection

### Three-Developer Test
- **Setup**: 10 minutes
- **Test**: 15 minutes
- **Validates**:
  - Queue with multiple waiters
  - Sequential promotion (alice → bob → charlie)
  - "Waiting For" chain (bob waits alice, charlie waits bob)
  - Context aggregation (each developer sees previous work)
  - Scaling beyond 2 developers
  - **Key insight**: Proves Neo works for teams, not just pairs

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
.venv/bin/python3 -m cli.file_watcher alice --server http://localhost:8000
```

- Each watcher checks if `NEO_DEVELOPER` matches its own `agent_id`
- If it matches: the watcher processes and logs the change
- If it doesn't match: the watcher **silently ignores** the change (allows other watchers to handle it)
- If not set: the watcher warns the developer and remains inactive

**2. Intent Declaration Before Editing**
```bash
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2 authentication"
```

- Before a file can be logged, the developer must declare intent
- The watcher verifies intent was declared before allowing logs
- If no intent: the watcher blocks the edit and prompts the developer with the required command
- This prevents accidental logging and ensures explicit developer intent

### Example Workflow

```
Terminal 2 (Alice's watcher):
  $ export NEO_DEVELOPER=alice
  $ .venv/bin/python3 -m cli.file_watcher alice --server http://localhost:8000
  ✅ Developer context: NEO_DEVELOPER=alice

Terminal 3 (Bob's watcher):
  $ export NEO_DEVELOPER=bob
  $ .venv/bin/python3 -m cli.file_watcher bob --server http://localhost:8000
  ✅ Developer context: NEO_DEVELOPER=bob

Terminal 4 (Editing):
  $ .venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2"
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
.venv/bin/python3 -m cli.neo_server --clear
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
   .venv/bin/python3 -m cli.file_watcher alice --server http://localhost:8000
   ```

2. **Intent not declared**
   ```bash
   # Declare intent before editing
   .venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Your intent here"
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
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Your intent here"
```

This prevents accidental logging and ensures explicit developer intent.

### Activity Log Not Clearing

**Problem:** Previous test data still showing

**Solution:** Clear on server startup:
```bash
.venv/bin/python3 -m cli.neo_server --clear
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
cd ~/Neo
.venv/bin/python3 -m cli.neo_server --clear

# Terminal 2: Alice watches
cd ~/Neo
.venv/bin/python3 -m cli.file_watcher alice

# Terminal 3: Bob watches
cd ~/Neo
.venv/bin/python3 -m cli.file_watcher bob

# Terminal 4 & 5: Ready for editing
cd ~/Neo
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
cd ~/Neo
.venv/bin/python3 -m cli.neo_client log
```

Should show:
- 2 developers (alice, bob)
- Same file (`src/auth.py`)
- Sequential work (alice → bob)
- No conflicts recorded

---

## Comparison: Terminal vs Claude Code IDE Testing

### Terminal-Based Testing (This Guide)

**Best for:**
- Testing without Claude Code IDE
- CI/CD integration
- Remote/server environments
- Learning Neo fundamentals
- Testing with standard Unix tools

**How it works:**
```
1. Start server (localhost:8000)
2. Start file watchers (one per developer)
3. Developers declare intent manually
4. Developers edit files with any editor
5. Watchers detect changes and log automatically
```

**Key Metrics:**
- Server detects conflicts: ✅ Yes
- Pre-generation prevention: ⚠️ No (logs after generation)
- Token savings: ✅ Good (catches early)
- Setup complexity: Low (just Python + terminal)
- IDE integration: No (works with any editor)

**Typical workflow:**
```
neo declare alice src/auth.py "Add OAuth2"
→ vim src/auth.py  (alice edits)
→ Server logs: alice → src/auth.py
→ neo declare bob src/auth.py "Add JWT"
→ Server warns: MEDIUM RISK (bob queued)
→ (alice completes)
→ Server: bob promoted, safe to proceed
→ vim src/auth.py  (bob edits)
```

### Claude Code IDE Testing

**Best for:**
- Production teams using Claude Code
- Maximum token efficiency
- Pre-generation conflict checking
- IDE-native workflows
- Automatic developer context

**How it works:**
```
1. Configure MCP server in IDE settings
2. Open IDE for each developer
3. Before generating: @neo check conflicts
4. IDE shows: ✅/⚠️/🚫 status
5. If safe: proceed with generation
6. If conflict: wait or coordinate
```

**Key Metrics:**
- Server detects conflicts: ✅ Yes
- Pre-generation prevention: ✅ **YES** (blocks before gen)
- Token savings: ✅ **Highest** (prevents re-gen)
- Setup complexity: Medium (MCP config)
- IDE integration: ✅ Yes (native @neo commands)

**Typical workflow:**
```
@neo check src/auth.py "Add OAuth2"
→ Risk: LOW - safe to proceed
→ Claude generates OAuth2 code
→ (alice's IDE shows: ✅ ACTIVE on src/auth.py)
→ (bob opens IDE, asks to add JWT)
→ @neo check src/auth.py "Add JWT"
→ Risk: MEDIUM - alice is active (queued)
→ Bob waits without generating
→ (alice completes)
→ @neo check src/auth.py "Add JWT"
→ Risk: LOW - now safe
→ Claude generates JWT code (first try, no re-gen!)
```

### Feature Comparison Table

| Feature | Terminal | Claude Code IDE |
|---------|----------|-----------------|
| **Setup Time** | 5-10 min | 5-10 min |
| **Editor Support** | Any (Vim, VS Code, etc.) | Claude Code IDE only |
| **File Detection** | Watcher-based | Automatic (IDE) |
| **Intent Declaration** | Manual `neo declare` | Built into workflow |
| **Developer Context** | NEO_DEVELOPER env var | Automatic (IDE session) |
| **Conflict Check** | Manual or auto (watcher) | Pre-generation hook |
| **Pre-gen Prevention** | No (logs after) | **Yes (blocks before)** |
| **Token Efficiency** | Good | **Excellent** |
| **Queue Management** | ✅ Yes | ✅ Yes |
| **Queue Visibility** | Terminal output | IDE status bar |
| **Multi-team Support** | Single (or env var) | Multitenancy ready |
| **CI/CD Integration** | ✅ Easy | ⚠️ Needs IDE |

### Decision Tree

**Use Terminal-Based If:**
```
Do you have Claude Code IDE?
  → No → Use Terminal Testing ✅
  → Yes, but...
    → Not using for generation? → Use Terminal Testing ✅
    → On a server/remote machine? → Use Terminal Testing ✅
    → Running in CI/CD? → Use Terminal Testing ✅
    → Integrating with other tools? → Use Terminal Testing ✅
```

**Use Claude Code IDE If:**
```
Do you have Claude Code IDE?
  → Yes
  → Using for code generation? → Use IDE Testing ✅
  → Care about token efficiency? → Use IDE Testing ✅ (saves 40-50% tokens)
  → Want pre-generation checks? → Use IDE Testing ✅
  → Team has IDE access? → Use IDE Testing ✅
```

---

## Next Steps

### Testing Progression

1. **Two-Developer Test** (this guide)
   - ✅ Lock creation and release
   - ✅ Basic queue management
   - ✅ Context refresh

2. **Three-Developer Test** (section above)
   - ✅ Multi-developer queue ordering
   - ✅ Sequential promotion
   - ✅ Context aggregation
   - ✅ Proves Neo scales beyond pairs

3. **Advanced Tests** (optional)
   - Test with 4+ developers
   - Test different files (no-lock, parallel work)
   - Test rapid concurrent declarations
   - Test with large activity logs (performance)
   - Test on networked machines (file sync)

### Production Use

**Terminal-Based (Current Setup)**:
- Run Neo server in background: `screen` or `nohup`
- Integrate with CI/CD pipelines
- Monitor activity log as team metric

**Claude Code IDE (Recommended for Teams)**:
- See `CLAUDE_CODE_TWO_DEVELOPER_TEST.md` for MCP setup
- Provides pre-generation conflict detection
- Saves 40-50% tokens on generation
- **Recommended path for production teams**

### Documentation References

- `CLAUDE_CODE_TWO_DEVELOPER_TEST.md` - IDE-based testing (recommended for teams)
- `ADVANCED_WORKFLOWS_AND_STATE_TRANSITIONS.md` - ⭐ Complex workflows, state transitions, activity log analysis (recommended for deeper understanding)
- `NEO_4.0_OPENAPI_SPECIFICATION.md` - Technical specification
- `CLAUDE.md` - Project overview and MCP configuration

---

## Advanced Workflows: State Transitions & Activity Log Analysis

**Want to see complex scenarios with full state machine transitions and annotated activity log output?**

See: **[`ADVANCED_WORKFLOWS_AND_STATE_TRANSITIONS.md`](ADVANCED_WORKFLOWS_AND_STATE_TRANSITIONS.md)**

Covers:
- ✅ Three-developer queue with context staleness (Phase 3 auto-refresh)
- ✅ Region-level locking (precise coordination at function level)  
- ✅ Rapid declarations (sub-millisecond conflict detection)
- ✅ Lock timeout & auto-promotion (30-min timeout, disconnection recovery)
- ✅ Overlapping regions with mixed conflicts (risk calculation)
- ✅ Complete activity log reference with real examples
- ✅ Full state machine transitions (v1.0 → v2.0 → v3.0 → v4.0)

Best for: Understanding Neo's complete lock mechanism, queue behavior, and seeing real `.devsync/activity-log.json` output at each state transition.

---

**Last Updated:** 2026-09-27  
**Neo Version:** 4.0  
**Status:** Ready for Local Testing
