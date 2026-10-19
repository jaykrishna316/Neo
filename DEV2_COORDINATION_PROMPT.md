# Developer-2: Neo Conflict Detection Test Prompt

## Context: You are Developer-2

You are trying to generate code for the file `core/auth.py`. However, Developer-1 is already working on this file. Let's see what Neo tells you about the conflict.

---

## STEP 1: Check for Conflicts (BEFORE You Generate!)

Run this command to see what Neo detects:

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
    print(f"\n⚠️  CONFLICT DETECTED! {len(active)} developer(s) on this file:")
    print()
    for entry in active:
        dev = entry['developer_id']
        intent = entry.get('intent', 'N/A')
        region = entry.get('region', 'N/A')
        print(f"   Developer: {dev}")
        print(f"   Intent: {intent}")
        print(f"   Region: {region}")
        print()
else:
    print(f"\n✅ No conflicts detected")

print(f"{'='*70}\n")
EOF
```

---

## STEP 2: Check Your Target Region vs Other Developers

Run this to see if your planned changes OVERLAP with theirs:

```bash
cd /home/user/Neo && python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.activity_log import get_active_entries

file_path = 'core/auth.py'
your_region = 'authenticate_user (lines 2-20)'  # Your planned changes
active = get_active_entries(file_path=file_path, expiry_minutes=30)

print(f"\n🎯 REGION OVERLAP ANALYSIS")
print(f"{'='*70}")
print(f"Your region: {your_region}")
print()

overlapping = []
for entry in active:
    other_region = entry.get('region', '')
    if 'authenticate_user' in your_region and 'authenticate_user' in other_region:
        overlapping.append({
            'dev': entry['developer_id'],
            'region': other_region
        })

if overlapping:
    print(f"⚠️  OVERLAPPING REGIONS DETECTED:")
    for item in overlapping:
        print(f"   {item['dev']}: {item['region']}")
    print()
    print(f"🚫 RISK LEVEL: HIGH")
    print(f"   Your changes conflict with {len(overlapping)} developer(s)")
    print(f"   Recommendation: Contact them first!")
else:
    print(f"✅ No overlapping regions")

print(f"{'='*70}\n")
EOF
```

---

## STEP 3: CONFLICT RESOLUTION OPTIONS

### Option A: Wait for Developer-1 (Recommended for overlapping regions)
Contact dev-1 and wait for them to finish. Then generate.

### Option B: Coordinate via DM
Message dev-1: "I need to modify authenticate_user too. Can we coordinate?"
Wait for response before generating.

### Option C: Change Your Target (Different region of same file)
If you can make your changes in a non-overlapping region, log that instead:

```bash
cd /home/user/Neo && python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity

# Changed to non-overlapping region
log_activity(
    developer_id='dev-2',
    file_path='core/auth.py',
    intent='Add password_strength_check function (new)',
    intent_category='feature',
    region='password_strength_check (new)'
)

print(f"\n✅ Intent logged for non-overlapping work")
print(f"   Now safe to generate code")
EOF
```

---

## What This Demonstrates

Neo's conflict detection **prevents wasted tokens** by:

1. **Detecting conflicts BEFORE generation** (not after merge)
2. **Showing overlap at semantic layer** (intent + region)
3. **Forcing coordination** instead of silent conflicts
4. **Saving tokens** by preventing re-generation after merge conflicts

**Example token savings:**
- Without Neo: 10k tokens (gen) + 10k tokens (rebase) = 20k total
- With Neo: 10k tokens (gen) + 0 tokens (prevented) = 10k total
- **Saved: 50% on overlapping work**

---

## Next Steps

Once you understand the conflict:

1. **If overlapping regions:** Coordinate with dev-1 first
2. **If different regions:** Log your intent and proceed
3. **Show the detection working:** This proves Neo prevents conflicts before they happen

This is the semantic conflict detection that prevents merge conflicts at generation time.
