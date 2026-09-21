# Neo: Semantic Multi-Developer Coordination Engine

## Project Overview

Neo is a semantic coordination engine that eliminates Git merge conflicts by moving conflict resolution one layer below Git through intelligent semantic coordination and automatic conflict prevention.

---

## MCP Server Configuration

Neo provides an MCP (Model Context Protocol) server for Claude Code IDE integration.

### MCP Servers

This project exposes the **neo-conflict-detection** MCP server:

```json
{
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
```

`command` must point at a Python environment with the `mcp` SDK installed (see `requirements.txt`) — a project-local virtualenv (`.venv`) works well since Claude Code invokes this as a subprocess and won't otherwise see your shell's environment.

### MCP Methods

The Neo MCP server provides 4 tools to Claude Code (tool names use underscores, not slashes, per the MCP tool-naming spec):

1. **neo_check_conflicts** - Check for conflicts before code generation
   - Input: `agent_id`, `file_path`, `intent`, `region`
   - Output: Risk level (LOW/MEDIUM/HIGH), message

2. **neo_log_activity** - Log developer intent
   - Input: `agent_id`, `file_path`, `intent`, `intent_category`
   - Output: Success confirmation

3. **neo_get_active_work** - View all active developers
   - Output: List of active entries with timestamps

4. **neo_get_status** - Check server status
   - Output: Server status, version, multitenancy state

---

## What This Enables

When Claude Code generates code:

1. **Before generation** → Neo checks for conflicts
2. **Risk assessment** → Returns LOW/MEDIUM/HIGH
3. **Display** → Shows status (✅/⚠️/🚫)
4. **User decision** → Block, warn, or allow generation
5. **Log activity** → Records intent to shared activity log

---

## Shared Activity Log

Location: `.devsync/activity-log.json`

This file-based log coordinates all developers:
- Tracks who is working on what file
- Records developer intent and timestamps
- Enables conflict detection at semantic layer (before Git merge)
- No database required (file-based, git-friendly)

---

## Architecture

```
Claude Code IDE
    ↓ (before generation)
Neo MCP Server (ide.mcp_neo_server)
    ↓
Core Neo logic (check_for_conflicts)
    ↓
Activity Log (.devsync/activity-log.json)
    ↓
Risk Classifier
    ↓
IDE Response (✅/⚠️/🚫)
```

---

## Quick Start

1. **MCP server is automatically loaded** by Claude Code when this project is open
2. **Generate code** - Neo will check for conflicts before generation
3. **View activity log** - `cat .devsync/activity-log.json`

---

## Key Files

- `core/mcp_server.py` - Core MCP implementation
- `ide/mcp_neo_server.py` - IDE-specific MCP wrapper
- `core/pre_gen_check.py` - Conflict detection logic
- `core/activity_log.py` - Activity log management
- `.devsync/activity-log.json` - Shared activity log (created on first use)

---

## Testing MCP Connection

The server speaks real MCP (JSON-RPC 2.0 over stdio) via the `mcp` SDK, so
running it directly just blocks waiting for a client — it won't print
anything on its own. Verify it with the SDK's client instead:

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
            print(await session.initialize())
            print(await session.list_tools())

asyncio.run(main())
"
```

A successful run prints the server info and the 4 registered tools
(`neo_check_conflicts`, `neo_log_activity`, `neo_get_active_work`,
`neo_get_status`).

---

## Multitenancy

To enable multitenancy for team isolation:

```json
{
  "neo-conflict-detection": {
    "env": {
      "NEO_MULTITENANCY": "true",
      "CLAUDE_TENANT_ID": "your-team-name"
    }
  }
}
```

Each team gets an isolated activity log.

---

## Status

✅ **MCP Server:** Operational and ready  
✅ **Conflict Detection:** Working  
✅ **Activity Logging:** File-based (no DB required)  
✅ **IDE Integration:** Automatic pre-generation conflict checking  

---

For documentation, see:
- `README.md` - Neo overview and usage
- `ide/README.md` - IDE integration quick start
- `ide/INTEGRATION_GUIDE.md` - Complete IDE integration guide
- `docs/MCP_IDE_INTEGRATION.md` - Technical MCP details
