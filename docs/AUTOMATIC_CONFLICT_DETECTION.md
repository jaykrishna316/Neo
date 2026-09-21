# Automatic Pre-Generation Conflict Detection

Neo now automatically checks for conflicts **before** Claude Code generates any files.

## How It Works

```
You ask Claude to generate code
         ↓
Neo checks for conflicts (automatically!)
         ↓
✅ LOW risk → Code generates normally
⚠️ MEDIUM risk → Warning shown, you can still proceed
🚫 HIGH risk → Generation blocked, requires coordination
```

## Setup

The automatic hook is configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /home/user/Neo/scripts/check_conflict_hook.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**What this does:**
- Triggers **before** any file write/edit operation
- Calls the conflict detection script
- Evaluates the risk level
- Blocks (HIGH) or warns (MEDIUM) as appropriate

## Risk Levels

### ✅ LOW Risk (Proceed Normally)
- No other developers working on this file
- No conflicts detected
- **Action:** Generation proceeds automatically

### ⚠️ MEDIUM Risk (Proceed with Caution)
- Another developer is working on the same file
- But in a different section
- **Action:** Warning shown; you can confirm and proceed

**Message:** `⚠️ MEDIUM CONFLICT WARNING: Another agent is working on <file> - Proceed with caution.`

### 🚫 HIGH Risk (Blocked)
- Another developer is making critical changes
- Same function signature, imports, or data structure
- **Action:** Generation is blocked; you must coordinate

**Message:** `🚫 HIGH CONFLICT DETECTED: Developer X changing signature of func() - Coordinate with other developers first.`

## Testing the Hook

To test the hook manually:

```bash
cd /home/user/Neo

# Test with a file that has no conflicts
echo '{"tool_name":"Edit","tool_input":{"file_path":"src/auth.py"}}' | python3 scripts/check_conflict_hook.py

# Expected output: {"continue": true}
```

## The Hook Script

**File:** `scripts/check_conflict_hook.py`

**What it does:**
1. Reads hook input JSON from stdin (tool_input with file_path)
2. Calls `check_for_conflicts()` from Neo core
3. Evaluates risk level:
   - **HIGH:** Blocks generation with stopReason
   - **MEDIUM:** Allows generation but shows warning
   - **LOW:** Allows generation silently
4. Outputs JSON response to stdout

**Response format:**
```json
{
  "continue": true/false,
  "stopReason": "Message shown when blocking",
  "systemMessage": "Warning shown when allowing"
}
```

## Integration with Claude Code

Claude Code IDE reads the hook response and:
1. If `"continue": false` → Blocks the operation, shows stopReason
2. If `"continue": true` + `systemMessage` → Shows warning but allows to proceed
3. If `"continue": true` → Proceeds silently (LOW risk)

## When Conflicts Are Detected

### How Neo Knows About Conflicts

Neo maintains an activity log at `.devsync/activity-log.json`:

```json
{
  "entries": [
    {
      "developer_id": "developer-1",
      "file_path": "src/auth.py",
      "intent": "Add OAuth2 support",
      "timestamp": 1234567890.5,
      "status": "in_progress"
    }
  ]
}
```

When you (or another developer) ask Claude to generate code:
1. The hook extracts the file path
2. Neo checks the activity log for other developers on that file
3. Risk classification determines if there's a conflict:
   - Same file + different regions = MEDIUM
   - Same function/signature = HIGH
   - No overlap = LOW

### How Developers Coordinate

1. **You generate code** → Hook checks conflicts
2. **If MEDIUM/HIGH** → You see the warning
3. **You coordinate** with the other developer (chat, sync, etc.)
4. **After coordination:**
   - The other developer finishes their work first
   - They push changes
   - You pull latest code
   - You generate on top of their changes → Conflicts resolved

## Disabling the Hook

If you need to disable conflict checking temporarily:

**Temporarily (this session):**
```bash
# Remove the hook from .claude/settings.json
# Or create .claude/settings.local.json with empty hooks
```

**Permanently:**
```bash
# Delete or comment out the "hooks" section in .claude/settings.json
```

## Customizing Risk Thresholds

Edit `.claude/settings.json`:

```json
{
  "conflict_detection": {
    "low_threshold": 0.1,      # Overlap ratio for LOW risk
    "medium_threshold": 0.5,   # Overlap ratio for MEDIUM risk
    "high_threshold": 0.5      # Overlap ratio for HIGH risk
  }
}
```

## Troubleshooting

### "Hook not running"

**Check:** The hook runs when Claude Code IDE is open and you ask it to generate code.

1. Verify `.claude/settings.json` is valid JSON:
   ```bash
   python3 -m json.tool .claude/settings.json
   ```

2. Check that Claude Code loaded the settings:
   - Restart Claude Code IDE
   - Try generating code again

### "False positives (HIGH conflicts when there shouldn't be)"

**Cause:** Activity log has stale entries from old sessions

**Solution:**
```bash
# Clear old entries from activity log
rm -f .devsync/activity-log.json

# Restart Claude Code and try again
```

### "Hook is too slow"

**Cause:** Check conflict operation is taking > 5 seconds

**Solution:** Increase timeout in `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 /home/user/Neo/scripts/check_conflict_hook.py",
        "timeout": 10
      }]
    }]
  }
}
```

## Next Steps

1. **Restart Claude Code IDE** - Settings reload on restart
2. **Try generating code** - You'll see the pre-generation conflict check
3. **Monitor the activity log** - Check `.devsync/activity-log.json` to see what Neo detects
4. **Test with multiple developers** - Run the test suite to see coordinated workflow:
   ```bash
   python3 tests/test_two_developer_coordination.py
   ```

## Architecture

```
Claude Code IDE
    ↓ (before Write/Edit)
    ↓
PreToolUse Hook
    ↓
check_conflict_hook.py
    ↓
check_for_conflicts() (Neo core)
    ↓
Activity Log (.devsync/activity-log.json)
    ↓
Risk Classifier (HIGH/MEDIUM/LOW)
    ↓
Hook Response (continue: true/false)
    ↓
Claude Code IDE (allow/warn/block)
```

---

**Status:** ✅ Automatic pre-generation conflict detection is now active

See `ide/README.md` for MCP server setup and `core/README.md` for conflict detection details.
