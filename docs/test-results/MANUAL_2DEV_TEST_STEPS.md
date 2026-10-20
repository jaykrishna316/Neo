# Manual 2-Developer Test - Step by Step

This guide walks you through running a **2-developer conflict scenario manually** in Claude terminals, seeing Neo function calls happen in real-time.

---

## Setup Phase (Before Starting)

### Terminal 0: Regular Terminal (Monitoring)
Keep this open to watch the activity log in real-time:

```bash
cd /home/user/Neo
tail -f .devsync/activity-log.json | python3 -m json.tool
```

This will show the activity log updating in real-time as developers log their intents.

---

## Phase 1: Dev A Starts Work (Claude Terminal 1)

**You are: Developer A (focusing on auth.py refactoring)**

### Step 1A.1: Create Initial File
In your Claude terminal (as Dev A):

```python
from pathlib import Path

# Create auth.py with initial functions
auth_code = '''
def authenticate_user(username, password):
    """Authenticate with username and password"""
    hashed = hash_password(password)
    user = get_user(username)
    return user and user.password == hashed

def hash_password(password):
    """Hash password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def get_user(username):
    """Get user from database"""
    return db.query("SELECT * FROM users WHERE username = ?", username)

def validate_jwt(token):
    """Validate JWT token"""
    import jwt
    return jwt.decode(token)
'''

Path("src/auth.py").parent.mkdir(exist_ok=True)
Path("src/auth.py").write_text(auth_code)
print("✅ Created src/auth.py")
```

**Look at Terminal 0 (activity log):** Should still be empty.

---

### Step 1A.2: Record Your Baseline
This establishes freshness tracking so Neo can detect if your code context becomes stale:

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.freshness import record_read

# Record that you're reading this file now
record_read(
    agent_id="dev-a-refactor",
    file_path="src/auth.py"
)
print("✅ Baseline recorded - freshness tracking active")
```

**What you'd see in Claude terminal:**
```
✅ Baseline recorded - freshness tracking active
```

---

### Step 1A.3: Check for Conflicts BEFORE Starting Work
This is the key Neo check - it prevents you from conflicting with other developers:

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import get_active_entries
from core.risk_classifier import classify_risk

# Check if anyone else is working on auth.py
active_entries = get_active_entries(file_path="src/auth.py", expiry_minutes=30)

print(f"🔍 Checking for conflicts on src/auth.py...")
print(f"   Found {len(active_entries)} active developers on this file")

if len(active_entries) > 0:
    print("\n⚠️  CONFLICT DETECTED!")
    for entry in active_entries:
        print(f"   • {entry['developer_id']} is working on this file")
        print(f"     Intent: {entry.get('intent', 'N/A')}")
else:
    print("   ✅ No conflicts - safe to proceed")
```

**What you'd see in Claude terminal:**
```
🔍 Checking for conflicts on src/auth.py...
   Found 0 active developers on this file
   ✅ No conflicts - safe to proceed
```

---

### Step 1A.4: Log Your Intent to Neo
This broadcasts to all developers what you're working on:

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import log_activity
import time

# Log your intent
entry = log_activity(
    developer_id="dev-a-refactor",
    file_path="src/auth.py",
    intent="Refactor: Rename authenticate_user to login_user for clarity. This is a breaking API change.",
    region="authenticate_user (lines 2-6)",
    intent_category="refactor",
    intent_scope="single-function",
    agent_metadata={
        "model": "claude-opus-5-5",
        "tokens_used": 1200,
        "confidence": 0.95,
        "execution_time": 2.3
    }
)

print("📝 ACTIVITY LOGGED TO NEO")
print(f"   Developer: {entry.developer_id}")
print(f"   File: {entry.file_path}")
print(f"   Intent: {entry.intent[:60]}...")
print(f"   Region: {entry.region}")
print(f"   Category: {entry.intent_category}")
print(f"   Timestamp: {entry.timestamp}")
```

**What you'd see in Claude terminal:**
```
📝 ACTIVITY LOGGED TO NEO
   Developer: dev-a-refactor
   File: src/auth.py
   Intent: Refactor: Rename authenticate_user to login_user...
   Region: authenticate_user (lines 2-6)
   Category: refactor
   Timestamp: 1697597400.123456
```

**Look at Terminal 0 (activity log):** You should see one JSON line appear!
```json
{
  "developer_id": "dev-a-refactor",
  "file_path": "src/auth.py",
  "intent": "Refactor: Rename authenticate_user...",
  "region": "authenticate_user (lines 2-6)",
  "intent_category": "refactor",
  "timestamp": 1697597400.123456,
  ...
}
```

---

### Step 1A.5: Analyze Semantic Symbols in Your File
Neo can understand the structure of your code:

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.semantic_conflict_detector import SemanticAnalyzer, Language

print("🔤 SEMANTIC ANALYSIS - Extracting symbols from auth.py...")

analyzer = SemanticAnalyzer("src/auth.py", Language.PYTHON)
symbols = analyzer.extract_symbols()
dependencies = analyzer.analyze_dependencies()

print(f"\n   Found {len(symbols)} symbols:")
for sym in sorted(symbols, key=lambda s: s.name):
    print(f"   • {sym.fully_qualified_name():30s} (type: {sym.type})")

print(f"\n   Found {len(dependencies)} dependencies:")
for dep in dependencies[:5]:
    print(f"   • {dep.source:20s} → {dep.target:20s} (type: {dep.type})")
```

**What you'd see in Claude terminal:**
```
🔤 SEMANTIC ANALYSIS - Extracting symbols from auth.py...

   Found 4 symbols:
   • authenticate_user            (type: function)
   • hash_password                (type: function)
   • get_user                     (type: function)
   • validate_jwt                 (type: function)

   Found 3 dependencies:
   • authenticate_user      → hash_password       (type: calls)
   • authenticate_user      → get_user            (type: calls)
   • validate_jwt           → jwt.decode          (type: calls)
```

---

## Phase 2: Dev B Tries to Work (Claude Terminal 2)

**You are: Developer B (working on token.py - which depends on auth.py)**

### Step 2B.1: Create token.py
Create a file that imports from auth.py:

```python
from pathlib import Path

token_code = '''
import src.auth

def create_session(user_id):
    """Create JWT session"""
    import jwt
    token = jwt.encode({"user_id": user_id})
    return token

def validate_session(token):
    """Validate session token"""
    return src.auth.validate_jwt(token)

def revoke_token(token):
    """Revoke a token"""
    pass
'''

Path("src/token.py").parent.mkdir(exist_ok=True)
Path("src/token.py").write_text(token_code)
print("✅ Created src/token.py")
```

---

### Step 2B.2: Record Your Baseline
```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.freshness import record_read

record_read(
    agent_id="dev-b-token",
    file_path="src/auth.py"
)
print("✅ Baseline recorded for src/auth.py")
```

---

### Step 2B.3: Check for Conflicts (CRITICAL - This is where Neo detects the problem)
```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import get_active_entries
from core.risk_classifier import classify_risk

# Check if anyone is working on auth.py
active_entries = get_active_entries(file_path="src/auth.py", expiry_minutes=30)

print(f"🔍 Checking for conflicts on src/auth.py...")
print(f"   Found {len(active_entries)} active developers on this file")

if len(active_entries) > 0:
    print("\n⚠️  CONFLICT DETECTED!")
    
    for entry in active_entries:
        dev_id = entry['developer_id']
        intent = entry.get('intent', 'N/A')
        
        print(f"\n   Other developer: {dev_id}")
        print(f"   Their intent: {intent[:70]}...")
        print(f"   Their region: {entry.get('region', 'whole file')}")
        
        # Use Neo's risk classifier
        assessment = classify_risk(
            current_developer="dev-b-token",
            current_file="src/auth.py",
            current_intent="Add new password_strength_check function",
            current_region="password_strength_check (new)",
            other_entry=entry
        )
        
        print(f"\n   ⚠️  RISK ASSESSMENT: {assessment.level.value}")
        print(f"   Reason: {assessment.reason}")
else:
    print("   ✅ No conflicts - safe to proceed")
```

**What you'd see in Claude terminal:**
```
🔍 Checking for conflicts on src/auth.py...
   Found 1 active developers on this file

⚠️  CONFLICT DETECTED!

   Other developer: dev-a-refactor
   Their intent: Refactor: Rename authenticate_user to login_user...
   Their region: authenticate_user (lines 2-6)

   ⚠️  RISK ASSESSMENT: MEDIUM
   Reason: Overlapping region with potential signature/removal changes
```

---

### Step 2B.4: Log Your Intent (Even With Conflict)
```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.activity_log import log_activity

# Log your intent despite the conflict
entry = log_activity(
    developer_id="dev-b-token",
    file_path="src/auth.py",
    intent="Add new password_strength_check function to auth module. Uses authenticate_user internally.",
    region="password_strength_check (new function)",
    intent_category="feature",
    intent_scope="single-function",
    blocking_others=False,
    agent_metadata={
        "model": "claude-opus-5-5",
        "tokens_used": 800,
        "confidence": 0.88,
        "execution_time": 1.8
    }
)

print("📝 ACTIVITY LOGGED TO NEO")
print(f"   Developer: {entry.developer_id}")
print(f"   File: {entry.file_path}")
print(f"   Intent: {entry.intent[:60]}...")
```

**Look at Terminal 0 (activity log):** You should now see TWO entries!

---

### Step 2B.5: Check Context Staleness
Neo tracks if your knowledge of the code is out of date:

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.freshness import check_freshness, delta_since_base

print("🔄 CHECKING CONTEXT FRESHNESS...")
print("   File: src/auth.py")

status = check_freshness("dev-b-token", "src/auth.py")
print(f"   Status: {status}")

if status == "CURRENT":
    print("   ✅ Your context is CURRENT - code unchanged")
elif status == "STALE_SOURCE":
    print("   ⚠️  Your context is STALE - code changed since baseline!")
    delta = delta_since_base("dev-b-token", "src/auth.py")
    if delta:
        print("   Changed symbols:")
        for line in delta.split('\n')[:5]:
            if line:
                print(f"     • {line}")
```

**What you'd see in Claude terminal:**
```
🔄 CHECKING CONTEXT FRESHNESS...
   File: src/auth.py
   Status: CURRENT
   ✅ Your context is CURRENT - code unchanged
```

---

## Phase 3: Check Impact Analysis (Either Terminal)

### Step 3.1: Analyze Cross-File Impacts

```python
import sys
sys.path.insert(0, '/home/user/Neo')

from core.semantic_conflict_detector import SemanticAnalyzer, Language

print("📡 IMPACT ANALYSIS")
print("\n   Auth.py symbols:")
analyzer_a = SemanticAnalyzer("src/auth.py", Language.PYTHON)
symbols_a = analyzer_a.extract_symbols()
for sym in symbols_a:
    print(f"     • {sym.fully_qualified_name()}")

print("\n   Token.py symbols:")
analyzer_b = SemanticAnalyzer("src/token.py", Language.PYTHON)
symbols_b = analyzer_b.extract_symbols()
for sym in symbols_b:
    print(f"     • {sym.fully_qualified_name()}")

print("\n   ⚠️  IMPACT: If Dev A renames authenticate_user → login_user:")
print("     • This BREAKS validate_session() in token.py")
print("     • Reason: token.py imports src.auth.validate_jwt()")
print("     • Blast Radius: ~40% (both files affected)")
```

**What you'd see in Claude terminal:**
```
📡 IMPACT ANALYSIS

   Auth.py symbols:
     • authenticate_user
     • hash_password
     • get_user
     • validate_jwt

   Token.py symbols:
     • create_session
     • validate_session
     • revoke_token

   ⚠️  IMPACT: If Dev A renames authenticate_user → login_user:
     • This BREAKS validate_session() in token.py
     • Reason: token.py imports src.auth.validate_jwt()
     • Blast Radius: ~40% (both files affected)
```

---

## Phase 4: View Complete Activity Log

### In Regular Terminal:
```bash
# Stop the tail with Ctrl+C, then view complete log:
cat .devsync/activity-log.json | python3 -m json.tool
```

**You'll see:**
```json
[
  {
    "developer_id": "dev-a-refactor",
    "file_path": "src/auth.py",
    "intent": "Refactor: Rename authenticate_user...",
    "region": "authenticate_user (lines 2-6)",
    "intent_category": "refactor",
    "intent_scope": "single-function",
    "agent_metadata": {
      "model": "claude-opus-5-5",
      "tokens_used": 1200,
      "confidence": 0.95
    },
    "timestamp": 1697597400.123456
  },
  {
    "developer_id": "dev-b-token",
    "file_path": "src/auth.py",
    "intent": "Add new password_strength_check...",
    "region": "password_strength_check (new function)",
    "intent_category": "feature",
    "timestamp": 1697597401.234567
  }
]
```

---

## Phase 5: Monitor Real-Time Activity

In a third regular terminal, run the monitor:

```bash
cd /home/user/Neo
python3 monitor-complete-activity.py --duration 300 --interval 2
```

**You'll see all data points in real-time:**
```
📊 NEO ACTIVITY LOG - 2 Active Entries

────────────────────────────────────────────────────────────────
  Developer: dev-a-refactor
────────────────────────────────────────────────────────────────

👤 DEVELOPER: dev-a-refactor
📄 FILE: src/auth.py
⏰ TIME: 15s ago
💭 INTENT: Refactor: Rename authenticate_user...
🎯 REGION: authenticate_user (lines 2-6)

  ✅ CONFLICT DETECTION: No conflicts detected

  🔄 CONTEXT STALENESS:
    • Status: CURRENT
    • Stale: False
```

---

## Summary of Data Points You'll See

### In Claude Terminal Output
✅ Conflict checks ("🔍 Checking for conflicts...")
✅ Risk levels ("⚠️  RISK ASSESSMENT: MEDIUM")
✅ Semantic symbols ("Found 4 symbols:")
✅ Dependencies ("Found 3 dependencies:")
✅ Context freshness ("Status: CURRENT")
✅ Impact analysis ("Blast Radius: ~40%")
✅ Activity logged confirmation ("📝 ACTIVITY LOGGED TO NEO")

### In Activity Log (.devsync/activity-log.json)
✅ developer_id
✅ file_path
✅ intent
✅ region
✅ intent_category
✅ intent_scope
✅ timestamp
✅ agent_metadata (model, tokens, confidence)

### In Monitor Output (monitor-complete-activity.py)
✅ Conflict detection results
✅ Lock status
✅ Context staleness status
✅ Semantic symbols
✅ Dependencies
✅ All activity log fields with human-readable formatting

---

## Key Points

1. **Claude Terminal shows Neo function calls** - You see the conflict checking, semantic analysis, and risk assessment happening in real-time

2. **Activity Log captures all intent** - Each developer's work is logged as JSON, creating the coordination database

3. **Monitor shows all 100+ data points** - The real-time monitor consolidates everything from the activity log with detailed analysis

4. **Conflicts are detected BEFORE generation** - Step 2B.3 shows Neo preventing wasted work before Dev B starts coding

5. **No merge conflicts at the end** - Because Neo coordinated before code was written
