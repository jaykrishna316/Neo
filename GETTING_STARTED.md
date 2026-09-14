# Getting Started with Neo

## Quick Start (30 seconds)

After cloning, run:

```bash
python3 run.py
```

You'll see an interactive menu with options:

```
Choose an option:

1 - View Interactive Dashboard (Browser)
2 - Run CLI Demo (All 5 Scenarios)
3 - Simulate 2 Agents (Choose Conflict Level)
4 - View Documentation
5 - Run Tests (if available)
6 - Exit
```

## Option Descriptions

### 1️⃣ Interactive Dashboard
Opens Neo's visual dashboard in your browser showing:
- Real-time conflict detection
- Risk scoring visualization
- Three-tier enforcement gates
- Developer/Agent activity tracking

**Best for:** Visual learners, stakeholder demos, understanding flow

---

### 2️⃣ CLI Demo (All 5 Scenarios)
Runs all conflict scenarios in terminal:
1. **Overlapping Regions** - MEDIUM risk (non-blocking warning)
2. **Non-Overlapping Regions** - LOW risk (silent pass)
3. **Signature Changes** - HIGH risk (blocking)
4. **Entry Expiry** - Stale entries ignored
5. **Multiple Developers** - 3+ agents on same file

Shows:
- Intent declarations
- Risk scoring with evidence
- Enforcement gate responses

**Best for:** Understanding the algorithm, integration testing

---

### 3️⃣ Simulate 2 Agents
Spawn two simulated agents and watch them interact:

Choose conflict level:
- **LOW** - Different functions in same file
- **MEDIUM** - Overlapping line ranges
- **HIGH** - Signature/API changes

Shows real-time coordination and decision-making.

**Best for:** Testing with your own coding agents, seeing coordination in action

---

### 4️⃣ View Documentation
Access all guides:
- **README.md** - Main overview
- **QUICKSTART.md** - Quick reference + examples
- **docs/ARCHITECTURE.md** - How Neo works
- **docs/IMPLEMENTATION.md** - Integration guide
- **POC_REPORT.md** - Detailed findings

**Best for:** Deep dives, understanding design decisions

---

### 5️⃣ Run Tests
Execute test suite (if pytest installed):

```bash
pip install -r requirements.txt
python3 run.py
# Select option 5
```

**Best for:** Verifying Neo works correctly on your system

---

## Common Workflows

### I want to understand Neo in 5 minutes
```bash
python3 run.py
# Select option 2 (CLI Demo)
# Read output to understand conflict detection
```

### I want to see a visual demo
```bash
python3 run.py
# Select option 1 (Dashboard)
# Click scenario buttons in browser
```

### I want to test with my own agents
```bash
python3 run.py
# Select option 3 (Multi-Agent)
# Choose conflict level to see coordination
```

### I want to integrate Neo into my IDE/Agent
```bash
python3 run.py
# Select option 4 (Docs)
# Read docs/IMPLEMENTATION.md
```

### I want to verify everything works
```bash
pip install -r requirements.txt
python3 run.py
# Select option 5 (Tests)
```

---

## What Happens After You Choose?

### Dashboard (Option 1)
- Browser opens automatically
- 6 interactive scenario buttons
- Real-time activity timeline
- Risk visualization with colors

**No typing required** - just click scenarios

---

### CLI Demo (Option 2)
- Terminal shows all 5 scenarios
- Each scenario has:
  - ```
    [DevA Intent] → "Refactoring login_user (lines 20-40)"
    [DevB Check] → "Adding validation to login_user (lines 25-35)"
    [Neo Analysis] → MEDIUM risk - overlapping region
    [Response] → Non-blocking warning shown
    ```

**Watch in real-time** - see conflict detection work

---

### Multi-Agent (Option 3)
- Choose LOW / MEDIUM / HIGH conflict
- Neo spawns two simulated agents
- They attempt work on overlapping regions
- Coordination layer intervenes

**Interactive** - see agents respond to conflicts

---

## Troubleshooting

### "No dashboard found"
```bash
# Dashboard is in examples/
ls examples/neo_*.html
# Run with explicit path
python3 run.py
# Select option 1 (auto-finds it)
```

### "cli_simulation.py not found"
```bash
# Make sure you're in repo root
cd Neo
python3 run.py
```

### "pytest not installed"
```bash
pip install -r requirements.txt
python3 run.py
# Select option 5
```

### "Permission denied" on run.py
```bash
chmod +x run.py
python3 run.py
```

---

## Next Steps

After exploring:

1. **Read QUICKSTART.md** for integration examples
2. **Check docs/** for architecture & implementation
3. **Review examples/** for code patterns
4. **Integrate into your IDE/Agent** using `pre_gen_check.py`

---

## For Agents/IDE Integration

If you're Claude Code, Cursor, Devin, or another agent:

```python
# Import Neo's core
from core.pre_gen_check import check_for_conflicts
from core.activity_log import log_activity

# Before generating code
log_activity(
    agent_id="claude-opus-1",
    file_path="src/auth.py",
    intent="Add OAuth2 support",
    region="authenticate_user function"
)

# Check for conflicts
risk, message = check_for_conflicts(
    "claude-opus-2",
    "src/auth.py",
    "login_user function"
)

if risk == "HIGH":
    print(f"⚠️ Conflict detected: {message}")
    # Ask for confirmation or wait
elif risk == "MEDIUM":
    print(f"⚠️ Warning: {message}")
    # Show warning but proceed
else:
    print("✓ Safe to generate")
    # Proceed with generation
```

See **docs/IMPLEMENTATION.md** for full integration guide.

---

## Questions?

See the documentation:
- Technical details: **CONFLICT_WARNING_POC.md**
- Architecture: **docs/ARCHITECTURE.md**
- Deployment: **docs/IMPLEMENTATION.md**
- Scenarios: **DEMO_SCENARIOS.md**

Or check the source:
- Core logic: `core/` directory
- Agent integrations: `agents/` directory
- Examples: `examples/` directory

---

**Ready to explore? Run: `python3 run.py`** 🚀
