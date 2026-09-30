# Neo MCP Server — Quick Start Guide

Get Neo running locally in 10 minutes. This guide walks you through cloning the repository, setting up the MCP server, and running tests.

---

## Prerequisites

- **Git** installed
- **Python 3.8+** installed
- **Claude Code IDE** (for IDE integration)
- **Terminal/Shell** access

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/jaykrishna316/neo.git
cd neo
```

---

## Step 2: Create Virtual Environment

```bash
# Create virtual environment in .venv directory
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

---

## Step 3: Install Dependencies

```bash
# Install MCP SDK and other requirements
pip install -r requirements.txt
```

---

## Step 4: Verify MCP Server Starts

```bash
# Test the MCP server (should block waiting for client)
PYTHONPATH=. .venv/bin/python3 -m ide.mcp_neo_server

# Ctrl+C to stop
```

---

## Step 5: Configure Claude Code IDE

Update `.mcp.json` in Neo project root with absolute paths:

```json
{
  "mcpServers": {
    "neo": {
      "command": "/absolute/path/to/neo/.venv/bin/python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/neo",
        "NEO_MULTITENANCY": "false",
        "CLAUDE_TENANT_ID": "default"
      }
    }
  }
}
```

Get absolute path: `pwd` (in the neo/ directory)

Restart Claude Code after updating.

---

## Step 6: Run Tests

### Test 1: MCP Server Connectivity

```bash
PYTHONPATH=. .venv/bin/python3 -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command='.venv/bin/python3',
        args=['-m', 'ide.mcp_neo_server'],
        env={'PYTHONPATH': '.', 'NEO_MULTITENANCY': 'false', 'CLAUDE_TENANT_ID': 'default'},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            print('Initialized:', await session.initialize())
            tools = await session.list_tools()
            print('Tools:', [t['name'] for t in tools['tools']])

asyncio.run(main())
"
```

Expected: Server responds with 4 tools (neo_check_conflicts, neo_log_activity, neo_get_active_work, neo_get_status)

---

### Test 2: Two-Developer Test

```bash
python3 tests/test_two_developer_coordination.py
```

Expected: ✅ PASSED with 0 conflicts

---

### Test 3: Real Two-Terminal Test

**Terminal 1:**
```
You are Developer A. Add two authentication functions to src/auth.py (password validation, hashing). Use Write/Edit tools. Show what you added.
```

**Terminal 2 (start 5-7 seconds later):**
```
You are Developer B. Add two session functions to src/auth.py (create session, validate session). Use Write/Edit tools. Show what you added.
```

Both should call neo_check_conflicts and complete without conflicts.

---

## Verify Activity Log

```bash
cat .devsync/activity-log.json
```

You'll see entries for each developer's work with timestamps and intents.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ModuleNotFoundError: mcp | `source .venv/bin/activate && pip install mcp` |
| CONNECT_TIMEOUT | Verify .mcp.json has absolute paths, restart Claude Code |
| Activity log empty | Run test_two_developer_coordination.py first |
| MCP server exits immediately | Check PYTHONPATH is correct, run with `PYTHONPATH=.` |

---

## Documentation

- `docs/MCP_SETUP_GUIDE.md` — Complete setup reference
- `docs/AUTOMATIC_CONFLICT_DETECTION.md` — Pre-generation hook system
- `CLAUDE.md` — Project configuration
- `core/pre_gen_check.py` — Conflict detection logic

---

**Status:** ✅ Production Ready  
**Last Updated:** 2026-09-21
