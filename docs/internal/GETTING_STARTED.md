# Neo Collaborative Workflow - Getting Started

**You have successfully built a complete collaborative development system. Here's how to test it.**

## 30-Second Quick Start

```bash
# Terminal 1: Start the server
python3 .claude/activity_log_server.py

# Terminal 2: Run a test (wait 2 seconds after server starts)
python3 .claude/test_complete_end_to_end.py
```

You'll see Dev1 and Dev2 collaborating: Dev1 edits → creates PR → Dev2 reviews → merges → Dev2 edits → auto-approvers assigned → merged.

## What You've Built

A **lock-based collaborative development system** that prevents merge conflicts by ensuring only one developer can edit a file:function at a time.

### Key Features

| Feature | Benefit |
|---------|---------|
| **Lock-Based Conflicts Prevention** | Only one dev editing per file:function, others queued |
| **Activity Log** | Complete audit trail of all changes and transitions |
| **Auto-Approver Assignment** | Contributors automatically become required approvers |
| **Multi-Dev Notifications** | Devs notified when they can proceed or must wait |
| **Agent + Human Support** | Agents auto-process, humans get interactive options |
| **REST API** | Integrates with IDEs, CI/CD, and tools |

## Testing Paths

### Path 1: Automated Tests (5-10 minutes)

**For a quick demo of the complete system:**

```bash
# Terminal 1
python3 .claude/activity_log_server.py

# Terminal 2 (after 2 second delay)
python3 .claude/test_complete_end_to_end.py
```

Shows: Dev1 → PR → Dev2 reviews → merges → Dev2 edits → auto-approvers → merged

**To test just the lock mechanism:**

```bash
python3 .claude/test_actual_file_editing.py
```

Shows: Dev1 acquires lock → Dev2 blocked → Dev1 releases → Dev2 acquires

**To test agent vs human workflows:**

```bash
python3 .claude/test_agent_vs_human.py
```

Shows: Agent auto-processes vs human getting interactive options

### Path 2: Manual Testing with curl (10-15 minutes)

```bash
# Terminal 1
python3 .claude/activity_log_server.py

# Terminal 2
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "type": "human"}'

curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "test.py", "function_name": "main"}'
```

See detailed API examples in `.claude/TEST_WITH_CLAUDE.md`

### Path 3: Real 2-Developer Testing (30-45 minutes)

For testing with actual git branches and code changes:

```bash
# Read the 14-step guide
cat .claude/REAL_2DEV_TESTING_GUIDE.md
```

This walks through:
- Dev1 creates feature branch, locks file, makes changes, creates PR
- Dev2 waits, gets notification, reviews and merges Dev1's changes
- Dev2 acquires lock, makes their changes, creates PR
- Both developers automatically assigned as required approvers
- All changes tracked in activity log

## File Structure

```
Neo/
├── .claude/
│   ├── activity_log_server.py          (900+ lines, REST API)
│   ├── workflow_state_machine.py        (9-state machine)
│   ├── notification_manager.py          (multi-channel notifications)
│   ├── activity_log_client.py           (client library)
│   │
│   ├── test_actual_file_editing.py      (lock mechanism demo)
│   ├── test_complete_end_to_end.py      (full workflow demo)
│   ├── test_agent_vs_human.py           (agent vs human demo)
│   ├── test_complete_workflow.py        (complete workflow test)
│   ├── validate_system.py               (validation script)
│   │
│   ├── README.md                        (system overview)
│   ├── SYSTEM_SUMMARY.md                (architecture details)
│   ├── COMPLETE_WORKFLOW_GUIDE.md       (700+ line detailed guide)
│   ├── AGENT_VS_HUMAN_GUIDE.md          (agent vs human workflows)
│   ├── TEST_WITH_CLAUDE.md              (testing guide with curl examples)
│   ├── REAL_2DEV_TESTING_GUIDE.md       (14-step real dev testing)
│   └── GETTING_STARTED.md               (this file)
│
└── test2devs.py                         (shared test file for 2 devs)
```

## System Validation

To verify all components are in place:

```bash
python3 .claude/validate_system.py
```

This checks:
- ✓ All core files present
- ✓ All test scripts available
- ✓ All documentation complete
- ✓ All key features implemented

## Architecture at a Glance

```
Developer 1                Developer 2
    ↓                          ↓
start_editing (acquire)    [BLOCKED - wait]
    ↓                          ↓
[EDITING - lock held]      poll for notifications
    ↓                          ↓
finish_editing             [lock_released notification]
    ↓                          ↓
[lock released]            start_editing (acquire)
    ↓
[Activity Log Updated]     [EDITING - lock held]
[Auto-approvers: dev1, dev2]
```

## Next Steps

### To Test
1. Run `python3 .claude/validate_system.py` to confirm everything is ready
2. Choose a testing path (automated/manual/real)
3. Follow the steps for that path

### To Understand
- **Quick Overview**: Read `.claude/README.md` (5 min)
- **Deep Dive**: Read `.claude/SYSTEM_SUMMARY.md` (10 min)
- **Real Workflow**: Read `.claude/REAL_2DEV_TESTING_GUIDE.md` (15 min)
- **Agent Support**: Read `.claude/AGENT_VS_HUMAN_GUIDE.md` (10 min)

### To Deploy
1. Deploy the activity log server to a persistent location (AWS, Heroku, etc.)
2. Distribute the REST API endpoint to developers
3. Install VS Code extension (located in `.vscode/neo-activity-monitor/`)
4. Register developers via `/api/register_developer` endpoint
5. Scale to your team

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/start_editing` | Acquire lock for file:function |
| `POST /api/finish_editing` | Release lock and notify next dev |
| `POST /api/create_pr` | Record PR creation |
| `POST /api/complete_review` | Human makes decision on PR |
| `POST /api/merge_to_main` | Merge and assign auto-approvers |
| `GET /api/notifications` | Poll for notifications (for IDE integration) |
| `GET /api/workflow/state` | View current state and history |

## Troubleshooting

**Q: "Connection refused" when running tests?**
- Make sure `activity_log_server.py` is running in another terminal
- Ensure 2+ second delay after server starts before running tests

**Q: "No notifications" when polling?**
- This is expected - notifications are delivered to subscribed developers
- Check the test script for subscription examples

**Q: Want to reset everything?**
- Stop the server (Ctrl+C)
- Start it again (state stored in memory)

## Support & Documentation

| Need | File |
|------|------|
| System overview | `.claude/README.md` |
| Architecture details | `.claude/SYSTEM_SUMMARY.md` |
| Detailed workflow | `.claude/COMPLETE_WORKFLOW_GUIDE.md` |
| Agent workflows | `.claude/AGENT_VS_HUMAN_GUIDE.md` |
| Manual testing | `.claude/TEST_WITH_CLAUDE.md` |
| Real 2-dev testing | `.claude/REAL_2DEV_TESTING_GUIDE.md` |
| This guide | `.claude/GETTING_STARTED.md` |

---

**Start testing now:**

```bash
python3 .claude/validate_system.py  # Verify all components
python3 .claude/activity_log_server.py  # In Terminal 1
python3 .claude/test_complete_end_to_end.py  # In Terminal 2
```

**Neo: Collaborative development, simplified.**
