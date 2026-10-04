# Neo Team Quick Start (Share This With Your Team)

## What is Neo?

Neo detects Git merge conflicts **before they happen**. When multiple developers work on the same file, Neo:
- Automatically locks the file when conflicts would occur
- Queues developers sequentially
- Prevents merge conflicts entirely
- Saves tokens by preventing re-generations

**One file, 4 developers, 0 conflicts.** ✨

---

## Setup (5 minutes per developer)

### 1. Clone Neo
```bash
git clone https://github.com/jaykrishna316/Neo.git
cd Neo
git checkout neo-4.0
```

### 2. Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Tell Neo about your team
export CLAUDE_TENANT_ID="your-team-name"
export NEO_LOG_DIR="/path/to/shared/activity-log"
```

### 4. Test It Works
```bash
python3 tests/devin_multi_agent_test.py alice
```

### 5. Configure Devin
Add to Devin MCP servers config:
```json
{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "PYTHONPATH": "/path/to/Neo",
      "CLAUDE_TENANT_ID": "your-team-name"
    }
  }
}
```

---

## How It Works (Team Perspective)

### Alice (First Developer)
- Opens file in Devin
- Neo: **✅ LOW RISK** → Proceed with generation
- Alice generates code

### Bob (Second Developer)
- Opens same file while Alice works
- Neo: **🔒 MEDIUM RISK** → **LOCKED, queued at position 0**
- Bob waits for Alice

### Charlie (Third Developer)
- Opens same file
- Neo: **🔒 MEDIUM RISK** → **LOCKED, queued at position 1**
- Charlie waits for Alice & Bob

### Dave (Fourth Developer)
- Same as Charlie, position 2

---

## What You'll See

### In Devin Console
```
Alice: ✅ LOW RISK - Safe to proceed
Bob:   🔒 MEDIUM RISK - Lock applied
       Queue position: 0, waiting_for: alice-devin
Charlie: 🔒 MEDIUM RISK - Lock applied
       Queue position: 1, waiting_for: alice-devin
Dave: 🔒 MEDIUM RISK - Lock applied
       Queue position: 2, waiting_for: alice-devin
```

### In Activity Log
```bash
cat .devsync/activity-log.json | jq '.'

# Shows:
# alice-devin: working on auth.py
# bob-devin: locked, waiting for alice-devin
# charlie-devin: locked, waiting for alice-devin
# dave-devin: locked, waiting for alice-devin
```

---

## Success Indicators

✅ All should see:
- First person: LOW RISK
- Others: MEDIUM RISK + lock message
- Queue showing correct position
- **Zero merge conflicts when all push**

---

## Troubleshooting

### Problem: No lock detected
**Check**: Is `CLAUDE_TENANT_ID` the same for everyone?
```bash
echo $CLAUDE_TENANT_ID
# Everyone should have same value
```

### Problem: Activity log shows no entries
**Check**: Is `NEO_LOG_DIR` shared?
```bash
echo $NEO_LOG_DIR
ls -la $NEO_LOG_DIR/activity-log.json
# Should be same path for all developers
```

### Problem: Getting different risk levels
**Check**: Make sure env vars are set **before** starting Devin
```bash
export CLAUDE_TENANT_ID="your-team-name"
export NEO_LOG_DIR="/shared/path"
# NOW start Devin
```

---

## Test It Now

**Terminal 1 (Alice):**
```bash
cd Neo
python3 tests/devin_multi_agent_test.py alice
```

**Terminal 2 (Bob):**
```bash
cd Neo
python3 tests/devin_multi_agent_test.py bob
```

Watch for:
- Alice: LOW RISK
- Bob: MEDIUM RISK + queue tracking
- Zero conflicts in final log

---

## Questions?

See full guide: `docs/TEAM_ONBOARDING_DEVIN.md`

---

## The Goal

By end of this test, you'll have proven:
- ✅ Multiple developers can work on same file safely
- ✅ Conflicts detected before they happen
- ✅ Zero Git merge conflicts
- ✅ Automatic queue management
- ✅ Neo works with real Devin IDE

**That's the whole point of Neo.** 🚀
