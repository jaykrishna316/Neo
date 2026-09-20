# Agent vs Human Collaborative Workflow

The Neo system supports both **AI agents (Claude)** and **human developers** with different, optimized workflows.

## Registration

First, register each developer with their type:

```bash
# Register an AI agent (Claude)
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "claude_agent", "type": "agent"}'

# Register a human developer
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "jane_developer", "type": "human"}'
```

## Workflow Comparison

### AGENT (Claude) - Autonomous Workflow

When Dev1 finishes and creates a PR, if Dev2 is an agent:

```
Dev1 finishes PR #42
    ↓
Dev2 (agent) is notified
    ↓
System calls: /api/agent_auto_process
    ↓
Agent automatically:
  ✓ Pulls code from feature branch
  ✓ Reviews changes (no delay)
  ✓ Merges into working branch
  ✓ Acquires lock
  ✓ Ready to continue editing
    ↓
Dev2 makes own changes
    ↓
PR #43 created and merged
```

**Example:**
```bash
# Dev1 finishes
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "src/auth.py", "function_name": "validate_user", "branch": "feature/dev1-changes", "pr_link": "https://github.com/.../pull/42"}'

# Create PR
curl -X POST http://localhost:5000/api/create_pr \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "src/auth.py", "function_name": "validate_user", "pr_number": 42, "pr_link": "https://github.com/.../pull/42", "branch": "feature/dev1-changes"}'

# Agent automatically processes
curl -X POST http://localhost:5000/api/agent_auto_process \
  -H "Content-Type: application/json" \
  -d '{"developer": "claude_agent", "file_path": "src/auth.py", "function_name": "validate_user"}'

# Response:
# {
#   "success": true,
#   "workflow_steps": ["auto_pulled", "auto_reviewed", "auto_merged", "lock_acquired"],
#   "message": "Agent claude_agent: Auto-pulled → auto-reviewed → auto-merged → acquired lock. Ready to continue editing.",
#   "ready_to_edit": true
# }
```

### HUMAN (Developer) - Interactive Workflow

When Dev1 finishes and creates a PR, if Dev2 is a human:

```
Dev1 finishes PR #42
    ↓
Dev2 (human) is notified
    ↓
System calls: /api/review_options (returns human options)
    ↓
Developer sees interactive choices:
  [ pull  ] → Download and review code changes
  [ ignore] → Skip review and start editing
  [ review] → View detailed code diff
    ↓
Developer chooses an action
    ↓
System records choice
    ↓
Dev2 acquires lock (with or without merged changes)
    ↓
Dev2 makes own changes
    ↓
PR #43 created
```

**Example:**
```bash
# Dev1 finishes (same as above)

# Get review options for human
curl "http://localhost:5000/api/review_options?developer=jane_developer&file_path=src/auth.py&function_name=validate_user"

# Response for HUMAN:
# {
#   "success": true,
#   "developer_type": "human",
#   "options": {
#     "pull": {
#       "action": "pull",
#       "description": "Pull and review the code changes",
#       "next_step": "You can then decide to merge or discard"
#     },
#     "ignore": {
#       "action": "ignore",
#       "description": "Ignore these changes and skip review",
#       "next_step": "You acquire lock without merging"
#     },
#     "review": {
#       "action": "review",
#       "description": "View detailed code diff and changes",
#       "next_step": "Then decide to merge or discard"
#     }
#   }
# }

# Developer chooses to pull
curl -X POST http://localhost:5000/api/complete_review \
  -H "Content-Type: application/json" \
  -d '{"developer": "jane_developer", "file_path": "src/auth.py", "function_name": "validate_user", "action": "merge"}'
```

## API Response Differences

### For AGENTS: `/api/review_options`
```json
{
  "success": true,
  "developer_type": "agent",
  "action": "auto_process",
  "workflow": ["auto_pull", "auto_review", "auto_merge", "acquire_lock", "ready_to_edit"],
  "message": "Agent claude_agent: Auto-pulling, reviewing, and merging changes. Ready to continue editing."
}
```

### For HUMANS: `/api/review_options`
```json
{
  "success": true,
  "developer_type": "human",
  "action": "wait_for_choice",
  "options": {
    "pull": {...},
    "ignore": {...},
    "review": {...}
  },
  "message": "Waiting for jane_developer's action on PR #42"
}
```

## Workflow State Machine

Both types flow through the same state machine:

```
AVAILABLE
    ↓
EDITING (Agent or Human)
    ↓
CONFLICT_WAITING (if another dev tries to edit)
    ↓
PENDING_REVIEW
    ↓
BOTH_DONE
    ↓
IN_PR (PR created)
    ↓
APPROVED (all devs approved)
    ↓
MERGED (merged to main)
```

The difference is not in STATES but in HOW developers move through them:
- **AGENT**: Automatically transitions through review/merge states
- **HUMAN**: Waits for manual choice before transitioning

## Mixed Team Example

Team with both agents and humans:

```
Day 1:
  Dev1 (Agent Claude) → edits → PR #1
    ↓
  Dev2 (Human Sarah) is next
    ↓
  Sarah gets options: pull/ignore/review
  Sarah pulls and reviews
    ↓
  Sarah finishes → PR #2
    ↓
  Dev3 (Agent Claude) is next
    ↓
  Agent auto: pull → review → merge → ready
    ↓
  Agent edits → PR #3
    ↓
  Dev1 (Agent) reviews auto
  Dev2 (Human) reviews manually
    ↓
  PR #3 merged to main

Benefits:
✓ No wait times for agent-to-agent handoffs
✓ Humans maintain full control over their decisions
✓ Agents accelerate workflow where possible
✓ Same lock mechanism prevents conflicts
✓ Complete audit trail for all actions
```

## Auto-Approver Assignment

Regardless of agent or human, when merging to main:

```bash
curl -X POST http://localhost:5000/api/merge_to_main \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "src/auth.py", "function_name": "validate_user", "pr_number": 43, "merge_commit_sha": "abc123"}'

# Response includes all developers who touched the file:
# {
#   "success": true,
#   "all_approvers_required": ["dev1", "dev2"],
#   "message": "PR #43 merged to main"
# }
```

Auto-approvers are determined by:
- Who initiated editing
- Who reviewed/merged
- Who modified the code

All become required approvers on the final PR to main.

## Configuration

Register developers at startup or via API:

**Via API (shown above):**
```bash
curl -X POST http://localhost:5000/api/register_developer \
  -d '{"developer": "name", "type": "agent|human"}'
```

**Environment variable (future):**
```bash
export NEO_DEVELOPERS="claude_agent:agent,jane_dev:human"
```

## Benefits

### For AI Agents (Claude)
- ✓ No wait times on reviews
- ✓ Continuous workflow without interruption
- ✓ Can process multiple PRs in parallel
- ✓ Perfect for high-throughput scenarios
- ✓ Handles routine review/merge tasks

### For Human Developers
- ✓ Full control over code decisions
- ✓ Can ask questions and request changes
- ✓ Can review multiple approaches
- ✓ Maintains responsibility for quality
- ✓ Can provide feedback to agents

## Testing

Run the agent vs human workflow test:

```bash
# Terminal 1: Start server
python3 .claude/activity_log_server.py

# Terminal 2: Run test
python3 .claude/test_agent_vs_human.py
```

This demonstrates:
- Agent registration
- Human registration
- Agent auto-workflow
- Human interactive options
- Mixed team collaboration
