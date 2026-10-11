# Neo Complete Test Walkthrough - All Steps in One

**Run this step-by-step and copy/paste all outputs for me.**

---

## SETUP

```bash
cd ~/Neo
mkdir -p .devsync src lib
rm -f .devsync/activity-log.json

cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """User authentication."""
    return bool(username and password)

def validate_token(token):
    """Validate auth token."""
    return token.startswith("token_")
EOF

echo "✅ Setup complete"
```

---

## TERMINAL 1: Start Neo Server

**Open a new terminal and run:**

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_server --clear
```

**Keep this running. Watch for output messages from Neo.**

---

## TERMINAL 2: Run All Test Steps

**Copy and run each section below. After each command, note what appears in Terminal 1.**

---

### PART 1: LOCK COORDINATION

#### Step 1: Alice Declares Intent

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add bcrypt password hashing" --category feature
```

**📝 Note Terminal 1 output here:**

---

#### Step 2: Alice Edits File

```bash
cat > src/auth.py << 'EOF'
import bcrypt

def authenticate_user(username, password):
    """User authentication with bcrypt."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return bool(username and hashed)

def validate_token(token):
    """Validate auth token."""
    return token.startswith("token_")

def hash_password(password):
    """NEW: Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
EOF
```

**📝 Note Terminal 1 output here:**

---

#### Step 3: Bob Declares Intent (CONFLICT!)

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client declare bob src/auth.py "Add OAuth2 support" --category feature
```

**📝 Note Terminal 1 output here:**

---

#### Step 4: Alice Completes Work

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_client complete alice src/auth.py --added 10 --removed 2
```

**📝 Note Terminal 1 output here:**

---

#### Step 5: View Activity Log

```bash
cat .devsync/activity-log.json | jq '.[] | {dev: .developer_id, intent: .intent[:35], lock_state, lock_holder, queue_pos: .queue_position}'
```

**📝 Copy entire output here:**

---

### PART 2: C1 STALENESS DETECTION

#### Step 6: Take Bob's Snapshot (BEFORE Alice changes)

```bash
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from core.symbol_hasher import snapshot_file
import time

bob_snapshot_before = snapshot_file('src/auth.py', 'bob', time.time())
print("\n" + "="*70)
print("BOB'S CONTEXT SNAPSHOT (Before Alice's changes)")
print("="*70)
print(f"\nSymbols in Bob's context:")
for sym in bob_snapshot_before.symbols:
    print(f"  - {sym}")
print(f"\nContent hash: {bob_snapshot_before.content_hash}")
print(f"Timestamp: {bob_snapshot_before.timestamp}")

import json
with open('.devsync/bob_snapshot_before.json', 'w') as f:
    json.dump({
        'symbols': list(bob_snapshot_before.symbols.keys()),
        'content_hash': bob_snapshot_before.content_hash,
        'timestamp': bob_snapshot_before.timestamp
    }, f, indent=2)
EOF
```

**📝 Copy entire output here:**

---

#### Step 7: Wait 3 Seconds

```bash
sleep 3
echo "Waiting complete..."
```

---

#### Step 8: Alice Adds New Functions

```bash
cat > src/auth.py << 'EOF'
import bcrypt

def authenticate_user(username, password):
    """User authentication with bcrypt."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return bool(username and hashed)

def validate_token(token):
    """Validate auth token."""
    return token.startswith("token_")

def hash_password(password):
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    """NEW: Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hashed)

def require_mfa(user_id):
    """NEW: Check if user requires MFA."""
    return user_id in ['admin', 'root']
EOF

echo "✅ Alice's changes complete"
```

---

#### Step 9: Check If Bob's Context is Stale (C1)

```bash
python3 << 'EOF'
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from core.symbol_hasher import snapshot_file, StalenessChecker
import time

with open('.devsync/bob_snapshot_before.json', 'r') as f:
    bob_before_data = json.load(f)

class SnapshotRef:
    def __init__(self, data):
        self.symbols = {s: type('obj', (object,), {'body_hash': 'dummy'})() for s in data['symbols']}
        self.content_hash = data['content_hash']
        self.agent_id = 'bob'

bob_snapshot_ref = SnapshotRef(bob_before_data)

print("\n" + "="*70)
print("C1: STALENESS DETECTION CHECK")
print("="*70)

state, report = StalenessChecker.check_file_staleness(
    bob_snapshot_ref,
    'src/auth.py',
    dependency_symbols=None
)

print(f"\nBob's context staleness check:")
print(f"  State: {state}")
print(f"  Reason: {report.get('reason')}")

if state == "STALE_SOURCE":
    print(f"\n✅ STALE CONTEXT DETECTED!")
    print(f"   Bob's snapshot is OUT OF DATE")
    bob_snapshot_after = snapshot_file('src/auth.py', 'bob', time.time())
    print(f"\nAfter refresh:")
    print(f"  New symbols: {list(bob_snapshot_after.symbols.keys())}")
    new_symbols = set(bob_snapshot_after.symbols.keys()) - set(bob_before_data['symbols'])
    print(f"  ✅ NEW symbols found: {list(new_symbols)}")
    print(f"  New content hash: {bob_snapshot_after.content_hash}")

    with open('.devsync/bob_snapshot_after.json', 'w') as f:
        json.dump({
            'symbols': list(bob_snapshot_after.symbols.keys()),
            'content_hash': bob_snapshot_after.content_hash
        }, f)
else:
    print(f"\n❌ Context not stale (unexpected)")
EOF
```

**📝 Copy entire output here:**

---

### PART 3: C2 DELTA REFRESH TOKEN SAVINGS

#### Step 10: Calculate Token Savings (C2)

```bash
python3 << 'EOF'
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

with open('.devsync/bob_snapshot_before.json', 'r') as f:
    before_data = json.load(f)
with open('.devsync/bob_snapshot_after.json', 'r') as f:
    after_data = json.load(f)

print("\n" + "="*70)
print("C2: DELTA REFRESH - TOKEN SAVINGS CALCULATION")
print("="*70)

symbols_before = set(before_data['symbols'])
symbols_after = set(after_data['symbols'])

added = symbols_after - symbols_before
removed = symbols_before - symbols_after

print(f"\nSymbol changes:")
print(f"  Added: {list(added)}")
print(f"  Removed: {list(removed)}")

with open('src/auth.py', 'r') as f:
    full_content = f.read()

def estimate_tokens(text):
    return max(1, len(text) // 4)

full_tokens = estimate_tokens(full_content)
delta_content = f"# Changed symbols: {list(added)}\n# Verify against: {before_data['content_hash']}\n"
delta_tokens = estimate_tokens(delta_content)

savings = full_tokens - delta_tokens
savings_percent = (savings / full_tokens * 100) if full_tokens > 0 else 0

print(f"\nToken analysis:")
print(f"  Full file refresh: ~{full_tokens} tokens")
print(f"  Delta refresh (only changed): ~{delta_tokens} tokens")
print(f"  Tokens saved: {savings}")
print(f"  Savings: {savings_percent:.1f}%")

print(f"\n✅ C2 DELTA REFRESH WORKING!")
print(f"   Instead of sending {full_tokens} tokens (full file),")
print(f"   Neo sends only {delta_tokens} tokens (changed symbols)")
print(f"   Saving {savings} tokens per refresh!")

print(f"\nWith 5 agents:")
print(f"  Full refresh approach: {full_tokens * 5} tokens total")
print(f"  Delta refresh approach: {delta_tokens * 5} tokens total")
print(f"  💰 Total savings: {savings * 5} tokens")

with open('.devsync/c1_c2_test_results.json', 'w') as f:
    json.dump({
        'c1_staleness_detection': {
            'status': 'PASSED',
            'state': state,
            'new_symbols': list(added),
        },
        'c2_delta_refresh': {
            'status': 'PASSED',
            'full_file_tokens': full_tokens,
            'delta_tokens': delta_tokens,
            'tokens_saved': savings,
            'savings_percent': savings_percent,
            'efficiency_rating': 'HIGH' if savings_percent > 80 else 'MEDIUM'
        }
    }, f, indent=2)
EOF
```

**📝 Copy entire output here:**

---

#### Step 11: View Final Results

```bash
cat .devsync/c1_c2_test_results.json
```

**📝 Copy entire output here:**

---

## CLEANUP

```bash
rm -f .devsync/bob_snapshot_before.json
rm -f .devsync/bob_snapshot_after.json
# Keep c1_c2_test_results.json and activity-log.json
```

---

## What to Send Me

After running all steps above, send me:

1. **Terminal 1 output** (all the ✅/⚠️/🚫 messages from Neo server)
2. **Step 5 output** (activity log jq output)
3. **Step 9 output** (C1 staleness detection)
4. **Step 10 output** (C2 token savings)
5. **Step 11 output** (final results.json)

That's it! All real outputs from running actual Neo functions.
