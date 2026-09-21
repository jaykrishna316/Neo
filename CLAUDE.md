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
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "PYTHONPATH": "/home/user/Neo",
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```

### MCP Methods

The Neo MCP server provides 4 methods to Claude Code:

1. **neo/check_conflicts** - Check for conflicts before code generation
   - Input: `agent_id`, `file_path`, `intent`, `region`
   - Output: Risk level (LOW/MEDIUM/HIGH), message

2. **neo/log_activity** - Log developer intent
   - Input: `agent_id`, `file_path`, `intent`, `intent_category`
   - Output: Success confirmation

3. **neo/get_active_work** - View all active developers
   - Output: List of active entries with timestamps

4. **neo/get_status** - Check server status
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

Run the MCP server directly:
```bash
python3 -m ide.mcp_neo_server
```

Should output:
```json
{"name": "neo-conflict-detection", "version": "1.0", "supported_methods": [...]}
```

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
