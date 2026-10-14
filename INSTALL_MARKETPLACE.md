# Installing Neo MCP Server

Choose your installation method below.

---

## Option 1: Claude Marketplace (Easiest) ⭐ RECOMMENDED

### Requirements
- Claude Code (Claude AI IDE)
- Claude Code version 0.4.0 or later

### Steps

1. **Open Claude Code**
   - Go to Settings (⚙️) in the sidebar

2. **Navigate to MCP Servers**
   - Click Settings → "MCP Servers"
   - Or search for "MCP" in settings

3. **Find Neo**
   - Search for "neo-mcp-server" or "Neo Coordination"
   - Or browse "Development Tools" category

4. **Install**
   - Click **Install** button
   - Claude Code downloads and configures automatically

5. **Restart Claude Code**
   - Close and reopen Claude Code IDE
   - MCP server starts automatically

6. **Verify Installation**
   - In Claude Code terminal, run: `neo_get_status`
   - Should see: `status: ok, version: 1.0`

### You're Ready!
Start using Neo's tools in Claude Code.

---

## Option 2: Manual Installation (Complete Control)

### Requirements
- Python 3.8+
- Git
- ~500MB disk space for Neo + dependencies

### Steps

**1. Clone Neo Repository**
```bash
git clone https://github.com/jaykrishna316/Neo.git
cd Neo
```

**2. Create Virtual Environment**
```bash
# On macOS/Linux:
python3 -m venv .venv
source .venv/bin/activate

# On Windows:
python -m venv .venv
.venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**4. Configure Claude Code**

Create or edit `.claude/mcpjson/neo.mcpjson`:

**macOS/Linux** (use absolute paths):
```json
{
  "neo-mcp-server": {
    "command": "/Users/yourname/Neo/.venv/bin/python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "PYTHONPATH": "/Users/yourname/Neo",
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```

**Windows** (use absolute paths with backslashes):
```json
{
  "neo-mcp-server": {
    "command": "C:\\Users\\yourname\\Neo\\.venv\\Scripts\\python.exe",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "PYTHONPATH": "C:\\Users\\yourname\\Neo",
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```

**⚠️ CRITICAL**: Use absolute paths, not relative paths.

**5. Restart Claude Code**
```bash
# Kill Claude Code completely, then reopen
```

**6. Verify Installation**
In Claude Code terminal:
```bash
# Should see neo_* tools available
```

---

## Option 3: Docker (Cloud/Enterprise)

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY Neo .

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install -r requirements.txt

CMD ["python", "-m", "ide.mcp_neo_server"]
```

### Run Container
```bash
docker build -t neo-mcp-server .
docker run -it neo-mcp-server
```

### Configure Claude Code to Use Container
```json
{
  "neo-mcp-server": {
    "command": "docker",
    "args": ["run", "--rm", "-i", "neo-mcp-server"],
    "env": {
      "NEO_MULTITENANCY": "false"
    }
  }
}
```

---

## Verification

### Test 1: Tools Available
In Claude Code, type any of these tool names (autocomplete should show them):
- `neo_check_conflicts`
- `neo_log_activity`
- `neo_check_source_staleness`
- `neo_get_active_work`
- `neo_get_status`

### Test 2: Run Quick Test
```bash
cd /path/to/Neo
python demo/mcp_local_2dev_test.py
```

**Expected**: Complete 2-developer coordination test, activity log with 10+ entries, no errors.

### Test 3: Check Activity Log
```bash
cat .devsync/activity-log.json | jq '.'
```

**Expected**: Valid JSON with developer coordination history.

---

## Troubleshooting

### Issue: "MCP server not found"

**Cause**: Claude Code hasn't loaded the configuration yet.

**Solution**:
1. Close Claude Code completely
2. Reopen Claude Code
3. Try again

If still not found:
```bash
# Check if Neo directory exists
ls -la /path/to/Neo/.venv/bin/python3

# Verify mcpjson file
cat ~/.claude/mcpjson/neo.mcpjson
```

### Issue: "ENOENT: no such file or directory"

**Cause**: Path is relative or incorrect.

**Solution**: Use absolute path in mcpjson:
```bash
# Get absolute path
pwd  # Copy this
# Use in mcpjson configuration
```

### Issue: "ModuleNotFoundError: No module named 'mcp'"

**Cause**: MCP SDK not installed.

**Solution**:
```bash
source /path/to/Neo/.venv/bin/activate
pip install mcp
```

### Issue: "Permission denied" running python

**Cause**: .venv not executable.

**Solution**:
```bash
cd /path/to/Neo
chmod +x .venv/bin/python3
```

### Issue: Tools show but calls fail

**Cause**: Server started but connection lost.

**Solution**:
1. Check PYTHONPATH in mcpjson
2. Verify `requirements.txt` installed
3. Check for Python errors: `python -m ide.mcp_neo_server` in terminal

---

## Configuration Options

### Environment Variables

Edit `.claude/mcpjson/neo.mcpjson` → `env` section:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEO_MULTITENANCY` | `false` | Enable tenant isolation (teams) |
| `CLAUDE_TENANT_ID` | `default` | Tenant identifier |
| `NEO_DEBUG` | `false` | Enable verbose logging |
| `NEO_RATE_LIMIT` | `100` | Requests per minute |

### Example: Enable Multitenancy
```json
{
  "neo-mcp-server": {
    "env": {
      "NEO_MULTITENANCY": "true",
      "CLAUDE_TENANT_ID": "team-acme"
    }
  }
}
```

---

## Getting Help

### Documentation
- **Full README**: https://github.com/jaykrishna316/Neo
- **MCP Integration**: [MCP_LOCAL_2DEV_TEST.md](docs/MCP_LOCAL_2DEV_TEST.md)
- **Troubleshooting**: [MCP_TROUBLESHOOTING.md](docs/MCP_TROUBLESHOOTING.md)

### Issues
- **GitHub Issues**: https://github.com/jaykrishna316/Neo/issues
- **Include**: Error message, OS, Python version, installation method

### Quick Test
```bash
python -c "import sys; print(f'Python {sys.version}')"
echo $PYTHONPATH  # Or %PYTHONPATH% on Windows
```

---

**Ready to eliminate merge conflicts?** Start with [MARKETPLACE.md](MARKETPLACE.md) to learn what Neo does.
