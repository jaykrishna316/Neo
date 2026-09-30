# Debugging the Developer Counting Issue

## Quick Start

The latest code now includes a **DEBUG line** that shows exactly what values are being calculated for the developer count. This will help us understand if the bug is in the calculation logic or elsewhere.

### Step 1: Pull Latest Changes

```bash
cd /home/user/Neo
git pull origin neo-4.0  # or main
```

### Step 2: Clear the Activity Log

Before running tests, always clear the activity log to remove stale entries:

```bash
.venv/bin/python3 -m cli.neo_client reset
```

Or delete directly:
```bash
rm -f .devsync/activity-log.json
```

### Step 3: Run the Server

Start the Neo server in one terminal:

```bash
.venv/bin/python3 -m cli.neo_server --port 8000 --clear
```

**Watch for the DEBUG line** - you should see something like:

```
DEBUG: entries=['alice'], developers_on_file={'alice'}, same_file_count=1
```

### Step 4: Run a Test (in another terminal)

Declare Alice's intent:

```bash
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add OAuth2"
```

**Look at the server terminal** - you should see the DEBUG output.

### Step 5: Declare Alice Again

```bash
.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add JWT"
```

**Again, check the DEBUG output** - should still show `same_file_count=1`

### Step 6: Add Bob

```bash
.venv/bin/python3 -m cli.neo_client declare bob src/auth.py "Add password strength"
```

**Now the DEBUG should show:**

```
DEBUG: entries=['alice', 'bob'], developers_on_file={'alice', 'bob'}, same_file_count=2
```

---

## What the DEBUG Output Means

```
DEBUG: entries=['alice', 'bob'], developers_on_file={'alice', 'bob'}, same_file_count=2
```

- **entries=[...]** - All entry developer_ids for this file
- **developers_on_file={...}** - Set of UNIQUE developers
- **same_file_count=2** - Count of unique developers

If you see `entries=['alice', 'alice', 'bob']` but `same_file_count=2`, that's correct (2 unique devs, 3 total entries).

If you see `same_file_count=2` when Alice is alone, that's the bug and we need to investigate why.

---

## Known Issue Resolved

Previous code counted **entries** instead of **unique developers**. 

**Old (buggy):**
```python
same_file_count = len([e for e in entries if e.get('file_path') == file_path])
```

**New (fixed):**
```python
developers_on_file = set([e.get('developer_id') for e in entries if e.get('file_path') == file_path])
same_file_count = len(developers_on_file)
```

This uses `set()` to count unique developers, not total entries.

---

## Reporting Results

If you still see the bug, please share:

1. The DEBUG output from your test
2. The full output from the neo_server process
3. The activity log file: `cat .devsync/activity-log.json`

This will help us pinpoint exactly where the issue is.
