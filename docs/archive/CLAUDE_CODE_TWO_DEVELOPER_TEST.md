# Neo with Claude Code IDE: Two-Developer Test

**For developers using Claude Code IDE with real-time conflict detection**

Complete guide to testing Neo's semantic coordination with Claude Code IDE. This approach provides **automatic pre-generation conflict checking** before code is generated, saving tokens by preventing expensive re-generations.

---

## Overview

When using Claude Code IDE with Neo:

1. **Before Generation** → Neo checks for conflicts at semantic layer
2. **Risk Assessment** → Returns LOW/MEDIUM/HIGH without generating
3. **Display** → Shows status (✅/⚠️/🚫) in IDE
4. **User Decision** → Block, warn, or allow generation
5. **Log Activity** → Records intent to shared activity log

This prevents conflicts **before expensive token-heavy code generation**, making it the most token-efficient approach for multi-developer teams.

---

## Architecture

```
Claude Code IDE (Developer A)
    ↓ (before generation)
Neo MCP Server (ide.mcp_neo_server)
    ↓
Conflict Detection (check_for_conflicts)
    ↓
Activity Log (.devsync/activity-log.json)
    ↓
Risk Classifier (LOW/MEDIUM/HIGH)
    ↓
IDE Response (✅ Generate / ⚠️ Warn / 🚫 Block)

Claude Code IDE (Developer B) — in parallel, same workflow
```

---

## Prerequisites

### 1. Python Environment

Neo requires Python 3.8+ with the MCP SDK:

```bash
cd /path/to/Neo
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Claude Code IDE Setup

Install Claude Code if you haven't already:
- **Web**: https://claude.ai/code
- **Desktop**: https://claude.ai/downloads
- **VS Code Extension**: Available in marketplace

### 3. MCP Server Configuration

In your Claude Code settings, add the Neo MCP server:

**Location**: `~/.claude/settings.json` or `.claude/settings.json` (project-wide)

```json
{
  "mcp": {
    "neo-conflict-detection": {
      "command": "/absolute/path/to/Neo/.venv/bin/python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Neo",
        "NEO_MULTITENANCY": "false",
        "CLAUDE_TENANT_ID": "default"
      }
    }
  }
}
```

Replace `/absolute/path/to/Neo` with your actual Neo repository path.

### 4. Test Repository Setup

```bash
cd /path/to/Neo
mkdir -p .devsync src lib
```

---

## Two-Developer Test Workflow

### Scenario

Alice and Bob are both using Claude Code IDE, working on the same repository. They're both working on `src/auth.py`:
- Alice: "Add OAuth2 authentication"
- Bob: "Add JWT token support"

Neo should detect the conflict and warn Bob before he generates code.

### Test Steps

#### Step 1: Both Developers Open the Project

**Developer A (Alice)**:
1. Open Claude Code IDE
2. Open the Neo repository
3. Neo MCP server loads automatically
4. Check `.devsync/activity-log.json` exists (created on first use)

**Developer B (Bob)**:
1. Open Claude Code IDE (another instance or window)
2. Open the SAME Neo repository
3. Neo MCP server loads automatically
4. Both developers now share the same activity log

#### Step 2: Alice Declares Intent

In Claude Code IDE (Alice's session):

```
@neo I'm going to add OAuth2 authentication to src/auth.py. Check for conflicts.
```

Or explicitly:
```
@neo check src/auth.py "Add OAuth2 authentication" --region validate_password
```

Neo responds:
```
✅ Conflict Check Result
   Risk: LOW
   No conflicting work detected. Safe to proceed.
   
   Active developers on this file: 1 (you)
   Lock Status: No lock
```

Alice can now generate code for OAuth2.

#### Step 3: Alice Generates Code

Alice uses Claude to write the OAuth2 code:
```
Generate a Python function that authenticates users with OAuth2.
It should:
1. Accept username and password
2. Validate against OAuth2 provider
3. Return authentication token
```

Neo monitors this. Before Claude generates code:
- Activity log updates: Alice is working on `src/auth.py`
- Risk level: LOW (only Alice working)

Alice's code is generated and committed.

#### Step 4: Bob Tries Same File (Conflict Detected!)

In Claude Code IDE (Bob's session):

Bob, unaware of Alice's work, asks:
```
@neo I'm adding JWT token support to src/auth.py. Check for conflicts.
```

Or:
```
@neo check src/auth.py "Add JWT token support" --region validate_password
```

Neo responds with a CONFLICT WARNING:
```
⚠️ Conflict Check Result
   Risk: MEDIUM
   
   MEDIUM RISK: alice is Working on src/auth.py
   Overlapping regions detected: validate_password
   
   🔒 Lock Status:
      Holder: alice
      Queue Position: 0 (you're next)
      Waiting For: alice
      
   💡 Recommendation: Wait for alice to complete or coordinate timing.
```

Bob now sees:
- ⚠️ **WARNING**: Alice is actively working on the same file and region
- **No generation** occurs (Neo blocked it at the semantic layer)
- **No tokens wasted** on conflicting code
- **Queue position**: Bob is first in queue, will be notified when lock is released

#### Step 5: Alice Completes Work

Alice finishes her OAuth2 implementation and marks completion:
```
@neo My work on src/auth.py is complete. OAuth2 is ready.
```

Or uses IDE UI to indicate completion. Neo then:
- Updates activity log: Alice's work is marked COMPLETED
- Releases lock on `src/auth.py`
- **Promotes Bob** to next developer

Bob sees:
```
✅ Lock Released!
   alice has completed their work on src/auth.py
   
   You are now ACTIVE on this file.
   Safe to proceed with JWT token support.
   
   💡 Alice's changes have been integrated into the activity log.
      Review their work before generating JWT code.
```

#### Step 6: Bob Gets Fresh Context from Alice's Changes

Before generating code, Bob reads Alice's completed work:

```
@neo Show me what alice just completed on src/auth.py
```

Neo provides context:
```
Alice's Completed Work (src/auth.py):
- Added OAuth2Provider class
- Implemented validate_password() with OAuth2 flow
- Added token refresh mechanism
- Test coverage: 95%

Recommendations for your JWT work:
- OAuth2Provider is available for composition
- Token storage is handled by OAuth2
- Consider adding JWT fallback mechanism
```

Bob now has full context before generating code.

#### Step 7: Bob Generates Code (with Context)

Bob asks Claude to extend Alice's work with JWT support:

```
Alice just finished OAuth2 authentication for src/auth.py. 
I need to add JWT token support that works alongside OAuth2.
Can you generate code that:
1. Creates JWT tokens
2. Validates JWT tokens
3. Works with Alice's OAuth2 implementation
```

Claude generates code that:
- Builds on Alice's OAuth2 implementation
- Doesn't conflict (already warned at check time)
- Integrates seamlessly with existing code
- No re-generation needed

#### Step 8: Bob Completes Work

Bob marks his work complete:
```
@neo JWT support is ready on src/auth.py
```

Final state:
- ✅ Alice: OAuth2 implementation → COMPLETED
- ✅ Bob: JWT implementation → COMPLETED
- ✅ Both changes in activity log with context
- ✅ **Zero conflicts, zero wasted token re-generations**

---

## Understanding Risk Levels

### LOW Risk (✅ Green)
- You're the **only developer** on this file
- No conflicts detected
- **Action**: Safe to generate code

**Example**:
```
✅ Risk: LOW (developers on file: 1)
   You are the only developer working here.
```

### MEDIUM Risk (⚠️ Yellow)
- **1+ other developers** already working on same file
- Overlapping regions detected
- **Action**: Warn user, offer to wait or coordinate

**Example**:
```
⚠️ Risk: MEDIUM
   alice is Working on src/auth.py
   Overlapping regions: validate_password
   Queue Position: 0 (you're next)
   Waiting For: alice
```

### HIGH Risk (🚫 Red)
- **Critical conflicts** detected
- Semantic incompatibility
- **Action**: Block generation, require coordination

**Example**:
```
🚫 Risk: HIGH
   alice is actively modifying validate_password function signature
   bob is adding calls to that function with old signature
   Generation would break the code flow.
   
   Required: Wait for alice to document new signature
```

---

## Multi-Developer (3+ Devs) Test

### Setup

Open Claude Code IDE for three developers:
- **Alice** (Terminal/Window 1)
- **Bob** (Terminal/Window 2)
- **Charlie** (Terminal/Window 3)

All sharing the same `.devsync/activity-log.json`

### Workflow

1. **Alice declares** on `src/auth.py` → Risk: LOW
2. **Bob tries same file** → Risk: MEDIUM (Queue: 0, Waiting: alice)
3. **Charlie tries same file** → Risk: MEDIUM (Queue: 1, Waiting: bob)
4. **Alice completes** → Bob promoted to active
5. **Bob completes** → Charlie promoted to active
6. **Charlie completes** → All done

**Queue behavior in IDE**:
```
Alice: ✅ ACTIVE (generating OAuth2)
Bob:   ⏳ QUEUED (position: 0, waiting for alice)
Charlie: ⏳ QUEUED (position: 1, waiting for bob)

[Alice finishes...]

Bob: ✅ ACTIVE (you may now generate JWT)
Charlie: ⏳ QUEUED (position: 0, waiting for bob)

[Bob finishes...]

Charlie: ✅ ACTIVE (you may now generate MFA)
```

---

## Token Savings Demonstrated

### Without Neo (Conflict at Merge Time)

```
Time  Action                          Tokens
────────────────────────────────────────────────
10:00 Alice generates OAuth2          5,000 tokens ✅
10:05 Bob generates JWT (conflicting) 5,000 tokens ❌ (wasted!)
10:10 Conflict detected at merge      -
10:11 Bob re-generates JWT (fixed)    5,000 tokens ❌ (wasted!)
10:15 Merge complete
      
      Total: 15,000 tokens
      Wasted: 10,000 tokens (re-generations)
```

### With Neo (Conflict at Check Time)

```
Time  Action                          Tokens
────────────────────────────────────────────────
10:00 Alice checks conflict           50 tokens (API call)
10:00 Alice generates OAuth2          5,000 tokens ✅
10:05 Bob checks conflict             50 tokens (API call) ⚠️ WARNING!
10:06 Bob waits for Alice            (0 tokens, no generation)
10:10 Alice marks complete           50 tokens (API call)
10:10 Bob checks conflict             50 tokens (API call) ✅ CLEAR
10:10 Bob generates JWT (safe)       5,000 tokens ✅ (first try!)
10:15 Merge complete                (0 tokens, no conflicts)
      
      Total: 10,200 tokens
      Saved: 4,800 tokens (prevented re-generation)
      Efficiency: 47% token reduction
```

---

## Troubleshooting

### MCP Server Not Connecting

**Error**: `MCP server 'neo-conflict-detection' not responding`

**Solution**:
1. Check settings file syntax:
```bash
jq . ~/.claude/settings.json  # Validate JSON
```

2. Verify Python path is absolute:
```bash
which python3
# Use full path in settings: /usr/bin/python3 (not python3)
```

3. Verify MCP dependencies:
```bash
cd /path/to/Neo
source .venv/bin/activate
python -c "import mcp; print('✅ MCP installed')"
```

4. Test MCP server directly:
```bash
cd /path/to/Neo
PYTHONPATH=. .venv/bin/python3 -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command='.venv/bin/python3',
        args=['-m', 'ide.mcp_neo_server'],
        env={'PYTHONPATH': '.', 'NEO_MULTITENANCY': 'false'},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
            tools = await session.list_tools()
            print('✅ Server OK')
            print(f'Tools: {[t.name for t in tools.tools]}')

asyncio.run(main())
"
```

### Activity Log Not Shared

**Problem**: Two IDE instances see different activity logs

**Solution**:
1. Verify both use same repository path
2. Check `.devsync/activity-log.json` location:
```bash
pwd  # Should be same for both developers
ls -la .devsync/activity-log.json
```

3. If on different machines, set up shared storage:
```bash
# Example: NFS mount or git sync
git pull origin main  # Sync latest activity log
```

### Conflict Check Always Returns LOW

**Problem**: Risk level never goes above LOW, even with overlaps

**Solution**:
1. Verify other developer has declared intent:
```bash
cat .devsync/activity-log.json | grep "developer_id"
# Should see both alice and bob
```

2. Check that developers are on **same file and region**:
```bash
@neo check src/auth.py "OAuth2" --region validate_password
# Must specify same region as other developer
```

3. Verify activity log is writable:
```bash
chmod 644 .devsync/activity-log.json
```

---

## Key Differences: Claude Code vs Terminal

| Feature | Claude Code IDE | Terminal + Server |
|---------|-----------------|-------------------|
| **Setup** | 5 min (JSON config) | 10 min (watchers) |
| **Conflict Detection** | Automatic (before generation) | Manual or watcher-based |
| **Context Awareness** | Real-time code context | Intent-based context |
| **Developer Context** | Automatic (IDE session) | Requires NEO_DEVELOPER env var |
| **Intent Declaration** | Built into IDE workflow | Manual `neo declare` command |
| **Token Efficiency** | **Highest** (prevents re-gen) | Good (early detection) |
| **Best For** | Production teams, IDE users | Testing, CI/CD, terminal users |

---

## Next Steps

1. **Test solo first** - Declare intent and generate in single IDE session
2. **Test with partner** - Open two IDE instances, follow two-dev workflow
3. **Monitor activity log** - `cat .devsync/activity-log.json | jq` after each step
4. **Scale to 3+ devs** - Add more Claude Code windows, observe queue behavior
5. **Measure token savings** - Compare token usage with/without Neo

---

## For Production Use

Once two-developer testing works:

1. **Add to team workflow** - Document Neo as team coordination tool
2. **Configure multitenancy** (if needed):
```json
{
  "env": {
    "NEO_MULTITENANCY": "true",
    "CLAUDE_TENANT_ID": "your-team-name"
  }
}
```

3. **Monitor activity log** - Version control `.devsync/activity-log.json`
4. **Set up alerts** - Track MEDIUM/HIGH risk events
5. **Document regions** - Define which code regions conflict for your codebase

---

**Status**: Claude Code IDE integration ready for two-developer testing

**Last Updated**: 2026-09-27
**Neo Version**: 4.0
