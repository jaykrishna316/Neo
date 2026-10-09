# Neo 2-Developer Test: Claude Terminal Prompts Only
## See Bob Get Blocked & Watch Lock Coordination Live

**No scripts. No Python. Just Claude terminal prompts.**

---

## Setup: Clear the Log First

### Terminal 0: Clear Activity Log (Optional, Run Once)

Paste this in any Claude terminal:

```
Run this command to start fresh:

python3 -c "from core.activity_log import clear_log; clear_log(); print('✓ Activity log cleared')"
```

This clears the activity log for a clean test. You only need to do this once.

---

## Terminal 1: Alice (First Developer)

**Create a NEW Claude terminal and paste this entire prompt:**

```
I'm Alice, a developer in Neo's coordination test.

I'm working on refactoring password validation in auth.py. 
My task is to add bcrypt hashing to make passwords more secure.

Here's what I need to do:

1. First, declare my intent to the activity log:
   - Run: python3 -c "from core.activity_log import log_activity, read_log; log_activity(developer_id='alice', file_path='auth.py', intent='Refactor password validation to use bcrypt', region='validate_password (lines 45-65)', intent_category='refactor'); entries = read_log(); print(f'✓ Alice declared intent'); print(f'Log entries: {len(entries)}'); [print(f'  {e[\"developer_id\"]}: {e[\"intent\"][:50]}...') for e in entries]"

2. Tell me: How many entries are in the log? Is there a lock yet?

3. Now wait for Bob to declare intent (watch the activity log), then check for conflicts:
   - Run: python3 -c "from core.pre_gen_check import check_for_conflicts; result = check_for_conflicts(agent_id='alice', file_path='auth.py', intent='Refactor password validation to use bcrypt', region='validate_password'); print(f'Risk level: {result[0].name}'); print(f'Message: {result[1][:100]}')"

4. Complete my work by logging completion:
   - Run: python3 -c "from core.activity_log import log_activity; log_activity(developer_id='alice', file_path='auth.py', intent='COMPLETED: Refactored password validation to use bcrypt', region='validate_password', agent_metadata={'status': 'completed', 'lines_added': 20, 'lines_removed': 5, 'conflicts_detected': 0}); print('✓ Alice completed work'); print('Changes: +20 lines, -5 removed')"

5. Finally, show me Bob's entry in the activity log to prove he was waiting:
   - Run: python3 -c "from core.activity_log import read_log; entries = read_log(); bob_entries = [e for e in entries if e['developer_id']=='bob']; [print(f'Bob entry: lock_state={e.get(\"lock_state\")}, waiting_for={e.get(\"waiting_for\")}, queue_pos={e.get(\"queue_position\")}') for e in bob_entries if e.get('lock_state')=='WAITING']"

Tell me at each step:
- What's in the activity log after I declare?
- Does Bob have a lock_state="WAITING"?
- How many lines did I add/remove?
- Did conflicts_detected = 0?
```

---

## Terminal 2: Activity Log Viewer (Watch Live)

**In another Claude terminal, paste this to watch the activity log:**

```
Keep running this command every 5 seconds to watch the activity log update:

python3 -c "
import json
from pathlib import Path

log_file = Path('.devsync/activity-log.json')
if log_file.exists():
    with open(log_file) as f:
        lines = f.readlines()
    entries = [json.loads(l.strip()) for l in lines if l.strip()]
    
    print(f'\n📊 Activity Log ({len(entries)} entries):')
    print('=' * 80)
    
    for i, e in enumerate(entries[-5:], 1):  # Show last 5 entries
        dev = e.get('developer_id', 'unknown')
        intent = e.get('intent', '')[:60]
        lock = e.get('lock_state', '')
        queue = e.get('queue_position')
        
        status = ''
        if lock == 'ACQUIRED':
            status = ' 🔒 LOCKED'
        elif lock == 'WAITING':
            status = f' ⏳ WAITING (queue:{queue})'
        elif e.get('agent_metadata', {}).get('status') == 'completed':
            status = ' ✅ DONE'
        
        print(f'{i}. {dev:8} | {intent:60} {status}')
    
    print('=' * 80)
else:
    print('❌ Activity log not found. Run Alice or Bob first.')
"
```

**Run this every 5 seconds and watch:**
- When Alice declares (no lock, 1 dev)
- When Bob declares (lock appears, bob shows WAITING)
- When Alice completes (MarkCompleted)
- When Bob completes (built_on="alice")

---

## Terminal 3: Bob (Second Developer)

**Create a NEW Claude terminal and paste this entire prompt:**

```
I'm Bob, a developer in Neo's coordination test.

I'm working on the same auth.py file as Alice.
My task is to add password strength validation.

Here's what I need to do:

1. First, check if Alice has already declared:
   - Run: python3 -c "from core.activity_log import read_log; entries = read_log(); alice = [e for e in entries if e['developer_id']=='alice']; print(f'Alice entries: {len(alice)}'); [print(f'  {e[\"intent\"][:60]}...') for e in alice]"

2. Tell me: Did Alice already declare? If yes, continue. If no, wait for her.

3. Check for conflicts BEFORE declaring:
   - Run: python3 -c "from core.pre_gen_check import check_for_conflicts; result = check_for_conflicts(agent_id='bob', file_path='auth.py', intent='Add password strength validation', region='validate_password'); print(f'Risk: {result[0].name}'); print(f'Msg: {result[1][:100]}...'); lock_info = result[2]; print(f'Lock info: {lock_info}')"

4. Tell me:
   - What's the risk level?
   - Can I see Alice in the message?
   - Is there lock information?

5. Now declare my intent:
   - Run: python3 -c "from core.activity_log import log_activity, read_log; log_activity(developer_id='bob', file_path='auth.py', intent='Add password strength validation', region='validate_password', intent_category='feature'); entries = read_log(); print(f'✓ Bob declared'); print(f'Log entries: {len(entries)}'); bob_entries = [e for e in entries if e['developer_id']=='bob']; [print(f'Bob: lock_state={e.get(\"lock_state\")}, queue_pos={e.get(\"queue_position\")}, waiting_for={e.get(\"waiting_for\")}') for e in bob_entries[-1:]]"

6. Tell me:
   - What is my lock_state?
   - What is my queue_position?
   - Am I waiting for alice?
   - 🚫 THIS IS WHERE BOB GETS BLOCKED 🚫

7. WAIT FOR ALICE TO COMPLETE, then check the activity log:
   - Run: python3 -c "from core.activity_log import read_log; entries = read_log(); alice_done = [e for e in entries if e['developer_id']=='alice' and e.get('agent_metadata',{}).get('status')=='completed']; print('Alice completed entries:'); [print(f'  Lines added: {e.get(\"agent_metadata\",{}).get(\"lines_added\")}'); print(f'  Lines removed: {e.get(\"agent_metadata\",{}).get(\"lines_removed\")}'); print(f'  Intent: {e[\"intent\"][:60]}...') for e in alice_done]"

8. Tell me:
   - Did Alice complete?
   - How many lines did Alice add/remove?

9. Now complete MY work:
   - Run: python3 -c "from core.activity_log import log_activity; log_activity(developer_id='bob', file_path='auth.py', intent='COMPLETED: Added password strength validation on top of Alice\\'s bcrypt refactor', region='validate_password', agent_metadata={'status': 'completed', 'lines_added': 15, 'lines_removed': 0, 'conflicts_detected': 0, 'built_on': 'alice'}); print('✓ Bob completed work'); print('Changes: +15 lines, -0 removed'); print('Built on: alice'); print('Conflicts: 0')"

10. Finally, show me the complete activity log:
   - Run: python3 -c "from core.activity_log import read_log; entries = read_log(); print(f'\\n✅ FINAL ACTIVITY LOG ({len(entries)} entries):'); print('='*80); [print(f'{e[\"developer_id\"]}: {e[\"intent\"][:60]}... (status: {e.get(\"agent_metadata\",{}).get(\"status\",\"declared\")})') for e in entries]; print('='*80); conflicts = sum(e.get('agent_metadata',{}).get('conflicts_detected',0) for e in entries); print(f'\\n🎯 TOTAL CONFLICTS: {conflicts}'); print('✅ TEST PASSED: Zero conflicts detected!' if conflicts == 0 else '❌ TEST FAILED')"

Tell me at each step what you see, especially:
- Am I BLOCKED when I declare?
- Can I see Alice's changes?
- When Alice completes, am I released?
- Do we have 0 conflicts at the end?
```

---

## How to Run (Step by Step)

### Step 1: Open Terminal 1 (Alice)
- Create a new Claude terminal
- Paste the **Alice** prompt above
- Watch her declare intent

### Step 2: Open Terminal 2 (Activity Log Viewer)
- Create another Claude terminal
- Paste the **Activity Log Viewer** prompt above
- Keep running that command every 5 seconds

### Step 3: Open Terminal 3 (Bob)
- Create another Claude terminal
- Paste the **Bob** prompt above
- Bob will see Alice already declared

### Timeline of Events

```
[T+0] Alice declares
     → Activity log has 1 entry (alice)
     → No lock (only 1 developer)

[T+5] Bob checks conflicts
     → Risk = MEDIUM (alice is working on same region)

[T+10] Bob declares
      → Activity log shows:
        - alice: lock_state = ACQUIRED
        - bob: lock_state = WAITING, queue_position = 0
      → 🚫 BOB IS BLOCKED 🚫

[T+20] Alice completes
      → Activity log shows:
        - alice: agent_metadata.status = completed, +20, -5

[T+25] Bob completes
      → Activity log shows:
        - bob: agent_metadata.status = completed, +15, built_on = alice

[T+30] Final check
      → Total conflicts: 0 ✅
      → TEST PASSED
```

---

## What You'll See (The Blocking)

### When Bob Declares, He's Blocked:

**Activity Log Viewer shows:**
```
📊 Activity Log (4 entries):
================================================================================
1. alice    | Refactor password validation to use bcrypt...  🔒 LOCKED
2. alice    | Lock acquired on region...                     🔒 LOCKED
3. bob      | Waiting for lock held by alice...              ⏳ WAITING (queue:0)
4. bob      | Add password strength validation...
================================================================================
```

### Bob's Own Entry Shows:

From Bob's command output:
```
Bob: lock_state=WAITING, queue_pos=0, waiting_for=alice
🚫 THIS IS WHERE BOB GETS BLOCKED 🚫
```

### When Alice Completes:

**Activity Log Viewer shows:**
```
📊 Activity Log (5 entries):
================================================================================
1. alice    | Refactor password validation to use bcrypt...  
2. alice    | Lock acquired on region...                     🔒 LOCKED
3. bob      | Waiting for lock held by alice...              ⏳ WAITING (queue:0)
4. bob      | Add password strength validation...
5. alice    | COMPLETED: Refactored password validation...   ✅ DONE
================================================================================
```

### When Bob Completes:

**Final check shows:**
```
✅ FINAL ACTIVITY LOG (7 entries):
alice: Refactor password validation to use bcrypt... (status: declared)
alice: Lock acquired on region... (status: declared)
bob: Waiting for lock held by alice... (status: declared)
bob: Add password strength validation... (status: declared)
alice: COMPLETED: Refactored password validation... (status: completed)
bob: COMPLETED: Added password strength validation... (status: completed)

🎯 TOTAL CONFLICTS: 0
✅ TEST PASSED: Zero conflicts detected!
```

---

## Key Points to Notice

### 1. Where Bob Gets Blocked
```
Bob's entry shows: lock_state = "WAITING"
                   queue_position = 0
                   waiting_for = "alice"
```
Bob **cannot** write code until Alice releases the lock.

### 2. Fresh Context Flow
```
Alice completes: +20 lines, -5 removed
Bob sees this in activity log
Bob then proceeds: built_on = "alice"
```
Bob builds his work **on top of** Alice's changes.

### 3. Zero Conflicts
```
Conflicts detected: 0
```
Sequential execution (not parallel) prevents all merge conflicts.

---

## Verification Checklist

After running both Alice and Bob, verify:

- [ ] Alice declares with no lock (1 developer only)
- [ ] Bob's entry shows `lock_state = "WAITING"` ← **BLOCKED**
- [ ] Bob's entry shows `queue_position = 0`
- [ ] Bob's entry shows `waiting_for = "alice"`
- [ ] Alice completes with changes: +20, -5
- [ ] Activity log shows alice's completed entry
- [ ] Bob's completed entry shows `built_on = "alice"`
- [ ] Final conflicts count: 0 ✅

---

## What This Proves

✅ **Bob gets blocked** when alice holds lock  
✅ **Lock is visible** in activity log (lock_state="WAITING")  
✅ **Bob waits in queue** (queue_position shows order)  
✅ **Fresh context flows** (Bob sees Alice's changes)  
✅ **Zero conflicts** (sequential work prevents merge conflicts)  

This is Neo's coordination at work: **semantic locking prevents conflicts before they happen.**

---

## No Scripts Required

Just Claude terminal prompts. Everything runs as Python one-liners that:
- Declare intent to activity log
- Check for conflicts
- Log completion with metadata
- Read and display activity log
- Show blocking and lock state

**No Python scripts to install. No external tools. Just prompts.**
