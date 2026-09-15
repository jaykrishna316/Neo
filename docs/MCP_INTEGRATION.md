# Neo MCP Server Integration

Neo now exposes its coordination APIs via MCP (Model Context Protocol), enabling seamless integration with Claude Code, Cursor, VS Code, and multi-agent Claude sessions.

## Overview

The Neo MCP Server provides:
- **Resources**: Real-time access to activity logs and conflict status
- **Tools**: Coordination functions (log intent, check conflicts, get status)
- **Multi-session coordination**: Agents across different Claude Code sessions can coordinate

## Installation

### Option 1: Claude Code MCP (Recommended)

```bash
# Install Neo as an MCP server in Claude Code
claude mcp install neo --source https://github.com/jaykrishna316/Neo.git

# Verify installation
claude mcp list
# Output should include: neo-coordination
```

### Option 2: Manual Setup

```bash
# Clone Neo repository
git clone https://github.com/jaykrishna316/Neo.git
cd Neo

# Install dependencies
pip install mcp

# Start the MCP server
python3 -m core.mcp_server
```

### Option 3: Development (Local Path)

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

## Usage in Claude Code

### 1. Declare Work Intent

Before starting code generation, declare your agent's intent:

```python
# In any Claude Code session
await claude.use("mcp").callTool("neo_coordination", "neo_log_activity", {
    "agent_id": "claude-opus-1",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "region": "authenticate_user function",
    "intent_category": "feature"
})
```

### 2. Check for Conflicts

Before generating code, check if another agent is working on overlapping code:

```python
const result = await claude.use("mcp").callTool(
    "neo_coordination", 
    "neo_check_conflicts", 
    {
        "agent_id": "claude-opus-2",
        "file_path": "src/auth.py",
        "intent": "Add password validation",
        "region": "authenticate_user function"
    }
);

// Result format:
// {
//   "risk_level": "MEDIUM",
//   "message": "MEDIUM RISK: Overlapping regions detected...",
//   "guidance": "Proceed with caution and consider coordinating..."
// }
```

### 3. Respond to Risk Levels

```python
if result.includes("BLOCKING")) {
    // HIGH risk - require manual coordination
    console.log("⚠️  Conflict detected. Please coordinate with the other agent.");
    return false; // Don't generate
} else if (result.includes("WARNING")) {
    // MEDIUM risk - warn but allow
    console.log("⚠️  Warning: Other agent working on overlapping code");
    return true; // Proceed with caution
} else {
    // LOW risk - proceed silently
    return true; // Safe to generate
}
```

## Available Resources

### `neo://activity-log`
Full activity log of all agent work declarations.

```bash
# Read via MCP
claude mcp read neo activity-log
```

**Format:**
```json
[
  {
    "developer_id": "claude-opus-1",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "region": "authenticate_user function",
    "timestamp": 1694857200.123,
    "intent_category": "feature"
  }
]
```

### `neo://active-entries`
Current non-expired work entries (within 30 minutes).

```bash
claude mcp read neo active-entries
```

### `neo://conflict-status`
Real-time coordination metrics and conflict summary.

```bash
claude mcp read neo conflict-status
```

**Format:**
```json
{
  "active_entries": 3,
  "files_with_activity": 2,
  "potential_conflicts": 1,
  "files_with_multiple_agents": {
    "src/auth.py": ["claude-opus-1", "claude-opus-2"]
  }
}
```

## Available Tools

### `neo_log_activity`
Declare an agent's intent to work on a file.

**Parameters:**
- `agent_id` (required): Unique agent identifier
- `file_path` (required): File path being modified
- `intent` (required): Description of work (e.g., "Add OAuth2 support")
- `region` (optional): Specific region (e.g., "authenticate_user lines 20-40")
- `intent_category` (optional): "feature" | "bugfix" | "refactor" | "chore"

**Returns:** Confirmation of logged activity

### `neo_check_conflicts`
Check for conflicts before code generation.

**Parameters:**
- `agent_id` (required): Your agent's ID
- `file_path` (required): File path
- `intent` (required): Your intended changes
- `region` (optional): Specific region you're modifying

**Returns:**
- `Risk Level`: LOW | MEDIUM | HIGH
- `Message`: Description of conflicts and reasoning
- `Guidance`: Recommended action based on risk level

### `neo_get_active_entries`
Get all currently active work entries.

**Parameters:**
- `file_path` (optional): Filter by file

**Returns:** Array of active activity log entries

### `neo_clear_log`
Clear the activity log (testing/cleanup only).

## Workflow Example

### Scenario: Two Claude Sessions Coordinating

**Session 1 (Agent A):**
```python
# Declare intent
await mcp.callTool("neo_coordination", "neo_log_activity", {
    "agent_id": "claude-opus-1",
    "file_path": "src/auth.py",
    "intent": "Refactor login_user function",
    "region": "lines 20-40",
    "intent_category": "refactor"
})
print("✓ Declared work on auth.py")
```

**Session 2 (Agent B - while Agent A is working):**
```python
# Check for conflicts
result = await mcp.callTool("neo_coordination", "neo_check_conflicts", {
    "agent_id": "claude-opus-2",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "region": "lines 25-35"
})

if "MEDIUM" in result:
    print("⚠️  Agent A is already refactoring this function")
    print("Waiting for Agent A to complete...")
    # Agent B waits or coordinates
else:
    print("Safe to generate code")
    # Agent B proceeds with code generation
```

## Three-Tier Enforcement via MCP

Neo's three-tier system works through MCP:

| Risk Level | Behavior | Action |
|-----------|----------|--------|
| **LOW** | Silent pass | Generate code immediately |
| **MEDIUM** | Warning | Warn developer, allow generation |
| **HIGH** | Blocking | Require manual confirmation |

## IDE Integration Examples

### Claude Code Extension

```javascript
// In VS Code extension for Claude Code
const conflictCheck = async (editor) => {
    const result = await claude.mcp.callTool("neo_coordination", 
        "neo_check_conflicts", {
        agent_id: editor.agent,
        file_path: editor.file.path,
        intent: editor.userPrompt,
        region: editor.selection.text
    });
    
    if (result.includes("BLOCKING")) {
        editor.showWarning("⚠️  " + result);
        return false;
    }
    return true;
};
```

### Cursor IDE Integration

```python
# Similar approach in Cursor plugins
def before_generation_hook(agent_context):
    result = check_neo_conflicts(
        agent_id=agent_context.agent_id,
        file_path=agent_context.file_path,
        intent=agent_context.prompt,
        region=agent_context.selection
    )
    return result.risk_level != "HIGH"
```

## Performance

- **Log Activity**: <5ms (local file I/O)
- **Check Conflicts**: <10ms (JSON read + classification)
- **Get Resources**: <50ms (file read)
- **Total overhead**: <10ms per check (imperceptible)

All operations are local; no network calls.

## Troubleshooting

### MCP Server Not Starting

```bash
# Verify MCP installation
pip install mcp

# Test server directly
python3 -m core.mcp_server
# Should output: "Neo MCP Server ready"
```

### Cannot Find Activity Log

Ensure Neo has been used at least once in the directory:
```bash
python3 -c "from core.activity_log import log_activity; log_activity('test', 'test.py', 'test')"
```

### Conflicts Not Detected

Check that:
1. Both agents are in same directory (sharing `.devsync/activity-log.json`)
2. Entries haven't expired (30-minute window)
3. File paths match exactly

## Next Steps

- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Integration guide for IDEs/agents
- [ARCHITECTURE.md](ARCHITECTURE.md) - How Neo detects conflicts
- [README.md](../README.md) - Main overview and quick start

## Support

- Issues: [GitHub Issues](https://github.com/jaykrishna316/Neo/issues)
- Discussions: [GitHub Discussions](https://github.com/jaykrishna316/Neo/discussions)
