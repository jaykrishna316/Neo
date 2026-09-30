# Neo MCP Server - Quick Setup Guide

Enable Neo coordination in Claude Code IDE with just a few commands.

## Prerequisites

- Python 3.8+
- Claude Code (or Cursor/VS Code)
- MCP library: `pip install mcp`

## Installation

### 1. Install Neo

```bash
git clone https://github.com/jaykrishna316/Neo.git
cd Neo
pip install -e .
pip install -e ".[mcp]"  # Install MCP dependencies
```

### 2. Register MCP Server in Claude Code

Edit `~/.claude/mcp_servers.json`:

```json
{
  "neo": {
    "command": "python3",
    "args": ["-m", "core.mcp_server"],
    "cwd": "/path/to/Neo"
  }
}
```

Replace `/path/to/Neo` with actual path (e.g., `/Users/you/neo` or `C:\Users\you\Neo`).

### 3. Restart Claude Code

MCP servers load on startup. Restart Claude Code or reload the MCP server:

```bash
# In Claude Code terminal
claude mcp reload
```

## Verify Installation

```bash
# Check if MCP server is available
claude mcp list
# Should show: neo-coordination
```

## Use in Claude Code

Now Neo tools are available in any Claude Code session:

```javascript
// Check for conflicts before generating code
const result = await claude.use("mcp").callTool(
    "neo_coordination",
    "neo_check_conflicts",
    {
        "agent_id": "my-agent",
        "file_path": "src/app.py",
        "intent": "Add error handling",
        "region": "main function"
    }
);

console.log(result.text); // Shows risk level and guidance
```

## Available Tools

| Tool | Purpose |
|------|---------|
| `neo_log_activity` | Declare agent intent before code generation |
| `neo_check_conflicts` | Check for conflicts with other agents |
| `neo_get_active_entries` | Get list of active work declarations |
| `neo_clear_log` | Clear activity log (testing only) |

## Common Workflows

### Multi-Agent Coordination

**Agent 1 (Claude Code Session 1):**
```python
# Declare work
await claude.use("mcp").callTool("neo_coordination", "neo_log_activity", {
    "agent_id": "agent-refactor",
    "file_path": "src/auth.py",
    "intent": "Refactor authentication module",
    "region": "authenticate_user function"
})
```

**Agent 2 (Claude Code Session 2 - while Agent 1 is working):**
```python
# Check for conflicts
const check = await claude.use("mcp").callTool("neo_coordination", "neo_check_conflicts", {
    "agent_id": "agent-oauth",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "region": "authenticate_user function"
})

# Result: "MEDIUM RISK: Overlapping regions detected. Coordinate with agent-refactor."
```

## Troubleshooting

### MCP Server won't start

1. Check Python path:
   ```bash
   which python3
   ```

2. Verify Neo is installed:
   ```bash
   python3 -m core.mcp_server
   # Should output: "Neo MCP Server ready"
   ```

3. Check `.claude/mcp_servers.json` syntax:
   ```bash
   python3 -c "import json; json.load(open(os.path.expanduser('~/.claude/mcp_servers.json')))"
   ```

### Tools not appearing in Claude Code

1. Restart Claude Code completely
2. Run: `claude mcp reload`
3. Check logs: `~/.claude/mcp.log`

### Conflicts not detected

- Verify both agents are in same directory
- Check entries haven't expired (30-minute window)
- File paths must match exactly (case-sensitive on Linux/Mac)

## Next Steps

- [MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) - Full integration guide
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - How Neo detects conflicts
- [README.md](README.md) - Overview and feature list

## Support

Questions? Check:
- [GitHub Issues](https://github.com/jaykrishna316/Neo/issues)
- [GitHub Discussions](https://github.com/jaykrishna316/Neo/discussions)
