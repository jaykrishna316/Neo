# Developer-1: Neo Coordination Test Prompt

## Context: You are Developer-1

You are about to generate code for the file `core/auth.py`. Before you generate ANY code, you MUST follow the Neo pre-generation coordination protocol:

---

## STEP 1: Check for Conflicts (Semantic Layer Detection)

Run this command to check if other developers are already working on this file:

```bash
cd /home/user/Neo && python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.activity_log import get_active_entries

file_path = 'core/auth.py'
active = get_active_entries(file_path=file_path, expiry_minutes=30)

print(f"\n🔍 NEO CONFLICT CHECK: {file_path}")
print(f"{'='*70}")

if active:
    print(f"\n⚠️  DEVELOPERS ALREADY ON THIS FILE:")
    for entry in active:
        dev = entry['developer_id']
        intent = entry.get('intent', 'N/A')[:60]
        region = entry.get('region', 'N/A')
        print(f"   • {dev}: {intent}")
        print(f"     Region: {region}")
else:
    print(f"\n✅ No conflicts detected - clear to proceed")

print(f"{'='*70}\n")
EOF
```

---

## STEP 2: Check Context Freshness

Run this command to verify your context is not stale:

```bash
cd /home/user/Neo && python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.freshness import check_freshness

file_path = 'core/auth.py'
status = check_freshness('dev-1', file_path)

print(f"\n📋 CONTEXT FRESHNESS: {file_path}")
print(f"{'='*70}")
print(f"Status: {status}")
print(f"{'='*70}\n")
EOF
```

---

## STEP 3: Log Your Intent (Declare Work)

Run this command to log your intent BEFORE you generate:

```bash
cd /home/user/Neo && python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity

dev_id = 'dev-1'
file_path = 'core/auth.py'
intent = 'Refactor authenticate_user function signature and add parameter validation'
region = 'authenticate_user (lines 2-15)'
category = 'refactor'

log_activity(
    developer_id=dev_id,
    file_path=file_path,
    intent=intent,
    intent_category=category,
    region=region
)

print(f"\n📝 INTENT LOGGED")
print(f"{'='*70}")
print(f"Developer: {dev_id}")
print(f"File: {file_path}")
print(f"Intent: {intent}")
print(f"Region: {region}")
print(f"Category: {category}")
print(f"{'='*70}\n")
EOF
```

---

## STEP 4: NOW Generate Your Code

Once you've completed steps 1-3 above, you can now generate your code for `core/auth.py`.

**Your task:** Refactor the `authenticate_user` function to:
- Rename it to `login_user` 
- Add parameter validation
- Improve error handling

Generate the code now.

---

## Success Criteria

✅ Completed Step 1 (conflict check)
✅ Completed Step 2 (freshness check)
✅ Completed Step 3 (intent logging)
✅ Generated code for core/auth.py
✅ Showed Neo detecting conflicts when developer-2 joins

---

## What This Demonstrates

This workflow shows Neo's value:
- **Before generation:** Check semantic conflicts
- **Declare intent:** Log what you're doing
- **Coordinate:** If conflicts exist, talk to other devs
- **Generate:** Only then generate code
- **Result:** No wasted tokens on merge conflict regeneration

**Token savings:** 50%+ on overlapping work by preventing conflicts BEFORE generation instead of after merge conflicts.
