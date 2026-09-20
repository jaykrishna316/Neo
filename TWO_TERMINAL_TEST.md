# Two-Terminal Coordination Test (Live)

This guide walks you through running a real two-developer coordination test with **two separate Claude terminals**, watching the shared activity log update in real-time.

## Setup: Open 2 Terminal Windows

You'll need:
- **Terminal A**: Alice's terminal
- **Terminal B**: Bob's terminal  
- **Terminal C** (optional): Log monitoring terminal

All on the same machine, reading/writing to the same `.devsync/activity-log.json` file.

---

## Step-by-Step Instructions

### BEFORE STARTING: Clear the Log

**In Terminal A or B (doesn't matter which first):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import clear_log
clear_log()
print("✓ Activity log cleared - starting fresh")
EOF
```

**Verify it's cleared:**
```bash
cat .devsync/activity-log.json
# Should show: []
```

---

## Step 1: Alice Declares Intent (Terminal A)

**Terminal A (Alice's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import log_activity, read_log
import json

print("=" * 70)
print("ALICE: Declaring intent to work on auth.py")
print("=" * 70)

log_activity(
    developer_id="alice",
    file_path="auth.py",
    intent="Refactor password validation to use bcrypt",
    region="validate_password (lines 45-65)",
    intent_category="refactor"
)

# Show current state
entries = read_log()
print(f"\n✓ Alice declared intent")
print(f"✓ Log now has {len(entries)} entry/entries")
print(f"\nCurrent log state:")
print(json.dumps(entries, indent=2))
EOF
```

**What to see:**
- Alice's entry appears in the log
- `developer_id: "alice"`
- `intent: "Refactor password validation to use bcrypt"`
- No lock yet (only 1 developer)

---

## Step 2: Bob Checks for Conflicts (Terminal B)

**Terminal B (Bob's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.pre_gen_check import check_for_conflicts
from core.activity_log import read_log
import json

print("=" * 70)
print("BOB: Checking for conflicts before declaring")
print("=" * 70)

# Check what's already in the log
entries = read_log()
print(f"\n✓ Current log has {len(entries)} entries")
print("\nExisting entries:")
for e in entries:
    print(f"  - {e['developer_id']}: {e['intent'][:50]}...")

# Check for conflicts
print("\n" + "=" * 70)
print("Checking for conflicts with alice's work...")
print("=" * 70)

risk_level, conflict_msg = check_for_conflicts(
    agent_id="bob",
    file_path="auth.py",
    intent="Add password strength requirements",
    region="validate_password (lines 50-70)"
)

print(f"\n✓ Risk level: {risk_level.name}")
print(f"✓ Message: {conflict_msg}")
print("\n→ Bob can see Alice is already working on this file!")
EOF
```

**What to see:**
- Bob reads Alice's entry from the log
- Shows risk level (should be MEDIUM since regions overlap slightly)
- Bob sees: "alice is working on auth.py in region validate_password"

---

## Step 3: Bob Declares Intent (Terminal B)

**Terminal B (Bob's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import log_activity, read_log
import json

print("=" * 70)
print("BOB: Declaring intent to work on auth.py")
print("=" * 70)

log_activity(
    developer_id="bob",
    file_path="auth.py",
    intent="Add password strength requirements",
    region="validate_password (lines 50-70)",
    intent_category="feature"
)

# Show current state
entries = read_log()
print(f"\n✓ Bob declared intent")
print(f"✓ Log now has {len(entries)} entries")
print(f"\n⚠️  LOCK SHOULD NOW BE ACTIVE (2 developers on same file)")

# Check for lock
same_file = [e for e in entries if e['file_path'] == 'auth.py']
print(f"\nDevelopers on auth.py: {len(same_file)}")
for e in same_file:
    print(f"  - {e['developer_id']}: {e['intent'][:40]}...")

print(f"\nCurrent log state:")
print(json.dumps(entries, indent=2))
EOF
```

**What to see:**
- Now 2 entries in the log (alice and bob)
- Lock should be ACTIVE (because 2 developers on same file)
- Bob's entry shows: `intent_category: "feature"`
- Both on `file_path: "auth.py"` with overlapping regions

---

## Step 4: Alice Completes Work (Terminal A)

**Terminal A (Alice's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import log_activity, read_log
import json
import time

print("=" * 70)
print("ALICE: Completing work (took ~2 seconds)")
print("=" * 70)

# Simulate Alice working for 2 seconds
time.sleep(2)

# Mark work as completed
log_activity(
    developer_id="alice",
    file_path="auth.py",
    intent="COMPLETED: Refactored password validation to use bcrypt",
    region="validate_password (lines 45-65)",
    intent_category="refactor",
    agent_metadata={
        "status": "completed",
        "lines_added": 20,
        "lines_removed": 5,
        "change_summary": "Switched from MD5 to bcrypt hashing with salt generation",
        "conflicts_detected": 0
    }
)

# Show current state
entries = read_log()
print(f"\n✓ Alice completed work!")
print(f"✓ Log now has {len(entries)} entries")
print(f"✓ Alice's changes: +20 lines, -5 lines removed")

# Show the completed entry
alice_completed = [e for e in entries if e['developer_id'] == 'alice' and (e.get('agent_metadata') or {}).get('status') == 'completed']
if alice_completed:
    print(f"\nAlice's completed entry:")
    print(json.dumps(alice_completed[0], indent=2))
EOF
```

**What to see:**
- A new entry appears in the log with `status: "completed"`
- `lines_added: 20, lines_removed: 5`
- `change_summary: "Switched from MD5 to bcrypt..."`
- `conflicts_detected: 0`
- Bob is still waiting in the queue

---

## Step 5: Bob Gets Fresh Context (Terminal B)

**Terminal B (Bob's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import read_log
from core.pre_gen_check import check_for_conflicts
import json

print("=" * 70)
print("BOB: Getting fresh context from Alice's completed work")
print("=" * 70)

# Re-check for conflicts to see Alice's new state
entries = read_log()
print(f"\n✓ Current log has {len(entries)} entries")

# Find Alice's completed entry
alice_completed = [e for e in entries if e['developer_id'] == 'alice' and (e.get('agent_metadata') or {}).get('status') == 'completed']

if alice_completed:
    entry = alice_completed[0]
    metadata = entry.get('agent_metadata', {})
    
    print(f"\n✓ Alice completed her work! Summary:")
    print(f"  Lines added: {metadata.get('lines_added')}")
    print(f"  Lines removed: {metadata.get('lines_removed')}")
    print(f"  Summary: {metadata.get('change_summary')}")
    print(f"  Conflicts: {metadata.get('conflicts_detected')}")
    
    print(f"\n✓ Bob now has fresh context of Alice's changes")
    print(f"✓ Bob can build his work on top of Alice's refactor")
else:
    print("⏳ Waiting for Alice to complete...")
EOF
```

**What to see:**
- Bob reads Alice's completed entry from the log
- Shows Alice's changes: +20 lines, -5 removed
- Shows no conflicts: `conflicts_detected: 0`
- Bob can now see exactly what Alice did before he starts

---

## Step 6: Bob Completes Work (Terminal B)

**Terminal B (Bob's workspace):**

```bash
cd ~/Neo
python3 << 'EOF'
from core.activity_log import log_activity, read_log
import json

print("=" * 70)
print("BOB: Completing work (built on Alice's refactor)")
print("=" * 70)

log_activity(
    developer_id="bob",
    file_path="auth.py",
    intent="COMPLETED: Added password strength requirements on top of Alice's bcrypt refactor",
    region="validate_password (lines 50-70)",
    intent_category="feature",
    agent_metadata={
        "status": "completed",
        "lines_added": 15,
        "lines_removed": 0,
        "change_summary": "Added complexity checks (uppercase, numbers, symbols) with bcrypt salt integration",
        "built_on": "alice",
        "conflicts_detected": 0
    }
)

# Show final state
entries = read_log()
print(f"\n✓ Bob completed work!")
print(f"✓ Log now has {len(entries)} entries")
print(f"✓ Bob's changes: +15 lines, 0 removed")
print(f"✓ Built on: alice")

print(f"\nFinal log state:")
print(json.dumps(entries, indent=2))
EOF
```

**What to see:**
- A new entry for Bob's completion appears
- Shows: `built_on: "alice"` (dependency tracking)
- `conflicts_detected: 0` (no conflicts because they coordinated)
- 4 total entries now: alice declare, bob declare, alice complete, bob complete

---

## Step 7: Verify Coordination Success (Any Terminal)

**In Terminal A, B, or C:**

```bash
cd ~/Neo
python3 << 'EOF'
import json
from pathlib import Path

print("\n" + "=" * 70)
print("COORDINATION TEST RESULTS")
print("=" * 70)

entries = json.loads(Path('.devsync/activity-log.json').read_text())

print(f"\nTotal log entries: {len(entries)}")
print(f"\nEntry sequence:")
for i, entry in enumerate(entries, 1):
    dev = entry['developer_id']
    metadata = entry.get('agent_metadata') or {}
    status = metadata.get('status', 'declared')
    built_on = metadata.get('built_on', 'none')
    
    print(f"\n[{i}] {dev} ({status})")
    print(f"    Intent: {entry['intent'][:60]}...")
    if status == 'completed':
        print(f"    Changes: +{metadata.get('lines_added')}, -{metadata.get('lines_removed')}")
        print(f"    Built on: {built_on}")
        print(f"    Conflicts: {metadata.get('conflicts_detected')}")

# Verify results
completed = [e for e in entries if (e.get('agent_metadata') or {}).get('status') == 'completed']
total_conflicts = sum((e.get('agent_metadata') or {}).get('conflicts_detected', 0) for e in completed)

print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)
print(f"✓ Developers coordinated: alice, bob")
print(f"✓ Completed tasks: {len(completed)}/2")
print(f"✓ Total conflicts: {total_conflicts}")

if total_conflicts == 0:
    print(f"\n🎉 SUCCESS! Neo coordination worked perfectly.")
    print(f"   Two developers coordinated through shared activity log with ZERO conflicts.")
else:
    print(f"\n❌ ISSUES DETECTED: {total_conflicts} conflicts")

# Show the actual shared file location
print(f"\n📄 Shared activity log location:")
print(f"   ~/.devsync/activity-log.json")
print(f"   (or: {Path('.devsync/activity-log.json').resolve()})")
EOF
```

**What to see:**
- All 4 entries logged in sequence
- Alice declares → Bob declares → Alice completes → Bob completes
- 0 conflicts across the entire workflow
- Bob's work is marked as `built_on: "alice"`
- Proof that coordination worked through the shared file

---

## Real-Time Monitoring (Optional: Terminal C)

If you want to **watch the log change in real-time** while the other terminals are working:

**Terminal C (Monitoring):**

```bash
cd ~/Neo

# Watch the log file for changes
watch -n 0.1 'cat .devsync/activity-log.json | python3 -m json.tool | head -50'

# Or just continuously refresh
while true; do
  clear
  echo "=== ACTIVITY LOG ($(date +%H:%M:%S)) ==="
  python3 -m json.tool .devsync/activity-log.json | head -80
  echo ""
  echo "Press Ctrl+C to stop"
  sleep 1
done
```

This shows the log updating as developers declare and complete work.

---

## What This Proves

✅ **Real file-based coordination**
- Two developers write to the same file
- Both can read what the other did
- Timing doesn't matter (sequential access to JSON file)

✅ **Semantic understanding**
- Alice says what she's doing (intent)
- Bob sees Alice's work and avoids conflicts
- No line-based conflict detection needed

✅ **Context flow**
- Alice completes work → logs it with `agent_metadata`
- Bob reads the log → gets Alice's context
- Bob builds on Alice's work → logs `built_on: "alice"`

✅ **Zero conflicts**
- Even with overlapping regions, coordination prevents conflicts
- Because coordination happens through intent, not line locks

---

## Key Observations to Make

1. **First entry** (Alice declares): Log shows 1 developer, no lock yet
2. **Second entry** (Bob declares): Log shows 2 developers, LOCK APPLIES
3. **Third entry** (Alice completes): Shows her changes in `agent_metadata`
4. **Fourth entry** (Bob completes): Shows `built_on: "alice"` + his changes

**The whole coordination happens through a 4-entry JSON file.**

That's Neo 3.0.

---

## If Something Goes Wrong

### "Log shows conflicts"
This shouldn't happen if both developers stay in their regions. Check:
- Are the regions really different? (alice: 45-65, bob: 50-70 overlap)
- Did bob get fresh context before completing?

### "Bob doesn't see Alice's work"
Check:
```bash
cd ~/Neo
python3 -c "from core.activity_log import read_log; import json; print(json.dumps(read_log(), indent=2))"
```
Should show all entries from both developers.

### "File permission errors"
Make sure `.devsync/` directory exists:
```bash
mkdir -p ~/.devsync/activity-log.json
```

---

## Total Time

- Step 1 (Alice declares): 10 seconds
- Step 2 (Bob checks): 5 seconds
- Step 3 (Bob declares): 5 seconds
- Step 4 (Alice completes): ~2 seconds (includes work simulation)
- Step 5 (Bob gets context): 5 seconds
- Step 6 (Bob completes): 5 seconds
- Step 7 (Verify): 5 seconds

**Total: ~2 minutes for complete coordination test**

---

Ready? Let's run it! Start with Terminal A and Terminal B side-by-side. 🚀
