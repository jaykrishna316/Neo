# Neo Illustrative Demo: Simple 3-Terminal Workflow

**TL;DR**: Developers write simple prompts. Neo coordinates automatically. Watch the activity log in real-time.

---

## 3-Terminal Setup

```
┌─────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  Terminal 1         │    │  Terminal 2          │    │  Terminal 3          │
│  (Regular Terminal) │    │  (Claude IDE)        │    │  (Claude IDE)        │
├─────────────────────┤    ├──────────────────────┤    ├──────────────────────┤
│                     │    │                      │    │                      │
│ Watch Activity Log  │    │ Alice: Code Gen      │    │ Bob: Code Gen        │
│ (Real-time stream)  │◄──►│ Simple prompt only   │◄──►│ Simple prompt only   │
│                     │    │                      │    │                      │
│ Shows:              │    │ Writes:              │    │ Writes:              │
│ • 🔒 Who has lock   │    │ "Add bcrypt to       │    │ "Add JWT support     │
│ • ⏳ Who's waiting  │    │  auth.py"            │    │  to auth.py"         │
│ • ✅ Who's done     │    │                      │    │                      │
│ • Lock transitions  │    │ Neo automatically:   │    │ Neo automatically:   │
│ • Notifications     │    │ • Logs intent        │    │ • Detects conflict   │
│                     │    │ • Acquires lock      │    │ • Queues him         │
│                     │    │ • Prevents conflicts │    │ • Notifies: "Busy"   │
└─────────────────────┘    └──────────────────────┘    └──────────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                        .devsync/activity-log.json
                      (Automatic coordination file)
```

---

## Pre-Demo Setup

**In Terminal 1**, before starting the watcher:

```bash
cd ~/Neo
mkdir -p .devsync src
rm -f .devsync/activity-log.json

# Create initial auth.py file
cat > src/auth.py << 'EOF'
"""Authentication module for application."""
import hashlib
from datetime import datetime, timedelta
from typing import Optional

def authenticate_user(username: str, password: str) -> bool:
    if not username or not password:
        return False
    return len(username) > 3 and len(password) > 6

def validate_token(token: str) -> bool:
    if not token:
        return False
    return token.startswith("token_") and len(token) > 20

def hash_password_simple(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_password_simple(password: str, hashed: str) -> bool:
    return hash_password_simple(password) == hashed

def generate_session_token(user_id: str) -> str:
    timestamp = str(int(datetime.now().timestamp()))
    return f"token_{user_id}_{timestamp}"

def get_token_expiry(token: str) -> Optional[datetime]:
    parts = token.split('_')
    if len(parts) < 3:
        return None
    try:
        timestamp = int(parts[2])
        return datetime.fromtimestamp(timestamp) + timedelta(hours=24)
    except (ValueError, IndexError):
        return None

def is_token_expired(token: str) -> bool:
    expiry = get_token_expiry(token)
    return expiry is None or datetime.now() > expiry
EOF

echo "✅ Setup complete. Auth module ready."
```

---

## The Demo Flow

### Step 1: Start Activity Log Watcher (Terminal 1)

```bash
.venv/bin/python scripts/watch_activity_log.py --follow --pretty
```

**Terminal 1 stays open**, showing live updates:
```
NEO ACTIVITY LOG WATCHER - Real-time Coordination View
────────────────────────────────────────────────────────
Time      | Status     | Developer  | Intent & Status
────────────────────────────────────────────────────────
[waiting for activity...]
```

---

### Step 2: Alice Generates Code (Terminal 2)

**In Terminal 2 (Claude IDE)**, Alice just writes a simple prompt:

```
I need to update src/auth.py with secure password hashing using bcrypt:

1. Add import for bcrypt
2. Add password_hash() function that uses bcrypt
3. Add verify_password() function
4. Add validate_password_strength() check
5. Update authenticate_user to use the new password functions

Just update the file with these functions.
```

**What happens automatically**:
- Neo detects Alice's intent
- Activity log gets updated with Alice's work
- Lock is acquired automatically
- Terminal 1 shows: `🔒 LOCKED | alice | password hashing with bcrypt`

Terminal 2 shows Claude's generated code being added to auth.py.

**Expected output in Terminal 1**:
```
────────────────────────────────────────────────────────
01:30:12 | 🔒 LOCKED  | alice      | password hashing with bcrypt
────────────────────────────────────────────────────────
```

---

### Step 3: Bob Tries to Work (Terminal 3)

**In Terminal 3 (Claude IDE)**, Bob writes a similar prompt:

```
Update src/auth.py to add JWT token support:

1. Add jwt import
2. Add create_jwt_token() function
3. Add verify_jwt_token() function  
4. Add refresh_jwt_token() function
5. Add validate_oauth2_scope() helper

Just add these functions to the auth module.
```

**What happens automatically**:
- Neo checks for conflicts → **MEDIUM_CONFLICT: Alice is working on this file**
- Lock is **NOT** acquired (Bob waits)
- Terminal 3 shows a notification: `⚠️ Alice is working on src/auth.py. Waiting...`
- Terminal 1 shows: `⏳ BLOCKED | bob | JWT token support [waiting for alice]`

Bob's IDE shows he's queued and waiting.

**Expected output in Terminal 1**:
```
────────────────────────────────────────────────────────
01:30:12 | 🔒 LOCKED  | alice      | password hashing with bcrypt
01:30:15 | ⏳ BLOCKED | bob        | JWT token support [waiting for alice]
────────────────────────────────────────────────────────
[SUMMARY] 🔒 1 locked | ⏳ 1 waiting
```

---

### Step 4: Alice Finishes (Terminal 2)

Alice's code generation completes. She commits her changes.

**What happens automatically**:
- Lock is released
- Activity log updated: Alice's work marked as done
- Bob is promoted to lock holder immediately
- Terminal 3 shows: `✅ YOUR TURN! Alice added bcrypt functions. Fresh context ready.`
- Terminal 1 shows lock transition

**Expected output in Terminal 1**:
```
────────────────────────────────────────────────────────
01:30:12 | 🔒 LOCKED  | alice      | password hashing with bcrypt
01:30:15 | ⏳ BLOCKED | bob        | JWT token support [waiting for alice]
01:30:35 | ✅ DONE    | alice      | password hashing with bcrypt [+20,-0]
01:30:35 | 🔒 LOCKED  | bob        | JWT token support (PROMOTED)
────────────────────────────────────────────────────────
[SUMMARY] 🔒 1 locked | ✅ 1 done
```

---

### Step 5: Bob Generates Code (Terminal 3)

Bob's code generation starts automatically. He has fresh context from Alice's work.

**What happens automatically**:
- Bob's code is generated with Alice's functions available
- Terminal 1 shows: `🔒 LOCKED | bob | JWT token support`
- No merge conflicts because Neo prevented concurrent work

**Expected output in Terminal 1**:
```
────────────────────────────────────────────────────────
01:30:12 | 🔒 LOCKED  | alice      | password hashing with bcrypt
01:30:15 | ⏳ BLOCKED | bob        | JWT token support [waiting for alice]
01:30:35 | ✅ DONE    | alice      | password hashing with bcrypt [+20,-0]
01:30:35 | 🔒 LOCKED  | bob        | JWT token support
01:30:50 | ✅ DONE    | bob        | JWT token support [+45,-0]
────────────────────────────────────────────────────────
[SUMMARY] ✅ 2 done
```

---

## What Neo Does Automatically

| Event | Manual Approach | Neo Approach |
|-------|-----------------|-------------|
| **Developer starts work** | Must call `log_activity()` | Automatically detected from prompt |
| **Lock management** | Manual with explicit calls | Automatic state machine |
| **Conflict detection** | Happens at Git merge | Happens at intent (before generation) |
| **Notifications** | Must call notification API | Automatic to Claude terminal |
| **Context sharing** | Manual context copy-paste | Automatic delta refresh |
| **Code merging** | Happens when all done | Never happens (conflicts prevented) |

---

## The Key Insight

**No developers need to write explicit logging code.** They just:
1. Write a natural prompt describing what they want to do
2. Neo intercepts it automatically
3. Coordination happens transparently
4. They see notifications and lock status in their IDE

This is Neo's real power: **automatic semantic coordination without manual API calls.**

---

## What You'll See in the Activity Log

Each entry shows:
- **🔒 LOCKED** - Developer has the lock, can generate
- **⏳ BLOCKED** - Developer waiting in queue
- **✅ DONE** - Developer completed their work

The log updates in real-time as developers work, showing:
- Who is working on which file
- Lock state transitions
- Queue positions
- Notifications automatically pushed

---

## Success Criteria

✅ **Zero merge conflicts** - Despite concurrent intent, no conflicts occur  
✅ **Automatic coordination** - Developers don't write logging code  
✅ **Real-time visibility** - Activity log shows all state in real-time  
✅ **Natural prompts** - Developers use normal Claude prompts, nothing special  
✅ **Automatic notifications** - Developers are notified when it's their turn  

---

## After the Demo

### What You've Learned
- How Neo prevents conflicts before code generation
- How lock state machine manages developer queue
- How notifications guide developers automatically
- How activity log tracks all coordination

### Try This Next
1. Run with 3 developers instead of 2
2. Add longer delays between steps to see queue management
3. Check the raw activity log: `cat .devsync/activity-log.json | jq`
4. Interrupt and restart a developer to see recovery

---

**Key Takeaway**: Developers write simple prompts. Neo handles all the coordination automatically. No manual logging, no explicit API calls, no manual lock management. Just semantic coordination that prevents conflicts before they happen.
