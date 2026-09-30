# Neo Parallel Test Runner

Automatically run all Phase 2 tests in parallel terminals without manual copy-paste.

## Quick Start

```bash
# Make sure you're in the Neo directory
cd /path/to/Neo

# Run the test runner
./run_parallel_tests.sh
```

That's it! The script will:
1. ✅ Clean the activity log
2. ✅ Create a tmux session with multiple windows
3. ✅ Run 3 test suites in parallel:
   - Phase 2 Unit Tests (9 tests)
   - Explicit Lock Tests (9 tests)
   - End-to-End Validation Test (7 checks)
4. ✅ Display all output in real-time

## What Happens

When you run `./run_parallel_tests.sh`, you'll see:

```
========================================
Neo Parallel Test Runner
========================================

Creating tmux session: neo-test-1696024800
This will run tests in parallel windows

✓ Activity log cleaned

Setting up Phase 2 Unit Tests
Setting up Explicit Lock Tests
Setting up End-to-End Validation Test

✓ All test windows created
Attaching to tmux session in 2 seconds...

Current window layout:
phase2-unit          (active)
explicit-locks       
e2e-validation       

Attaching to session: neo-test-1696024800

Navigation tips:
  • Use Ctrl-b n to go to next window
  • Use Ctrl-b p to go to previous window
  • Use Ctrl-b l to toggle last window
  • Use Ctrl-b :kill-session to exit all windows
  • Use Ctrl-b [ to scroll (q to exit scroll mode)
```

## Navigation Inside tmux

Once attached to the session, use these shortcuts:

| Shortcut | Action |
|----------|--------|
| `Ctrl-b n` | Next window |
| `Ctrl-b p` | Previous window |
| `Ctrl-b l` | Toggle to last window |
| `Ctrl-b 0` | Go to phase2-unit window |
| `Ctrl-b 1` | Go to explicit-locks window |
| `Ctrl-b 2` | Go to e2e-validation window |
| `Ctrl-b [` | Enter scroll mode (press `q` to exit) |
| `Ctrl-b :` | Command mode |
| `Ctrl-b :kill-session` | Exit all windows |

## Test Output

Each window shows:

**Window 1: Phase 2 Unit Tests**
```
======================================================================
PHASE 2 COMPREHENSIVE TEST SUITE
======================================================================

✅ PASS: Lock holder doesn't see waiting developers as conflicts
✅ PASS: Waiting developer still sees conflict with lock holder
✅ PASS: 3-dev scenario - lock holder sees LOW risk
...
TEST SUMMARY: 9/9 passed
```

**Window 2: Explicit Lock Tests**
```
======================================================================
NEO 4.0: EXPLICIT LOCK TESTS
======================================================================

✓ test_lock_acquisition_when_free PASSED
✓ test_lock_blocking_when_held PASSED
...
TEST RESULTS: 9 passed, 0 failed
```

**Window 3: End-to-End Validation**
```
======================================================================
PHASE 2 END-TO-END VALIDATION TEST
======================================================================

STEP 1: Alice declares intent on auth.py
STEP 2: Bob declares intent on same file
STEP 3: Charlie declares intent on same file
STEP 4: Alice checks conflicts (PHASE 2 FIX)
STEP 5: Verification Summary

✅ Alice first check returns LOW
✅ Bob declares with MEDIUM risk
✅ Charlie declares with MEDIUM risk
✅ Alice 2nd check returns LOW (PHASE 2 FIX WORKING)

RESULT: 7/7 checks passed
```

## Requirements

- **tmux** - Terminal multiplexer (required)
  - macOS: `brew install tmux`
  - Linux: `apt-get install tmux` or `yum install tmux`
  - Windows (WSL): `apt-get install tmux`

- **Python 3** - For running tests (usually already installed)

- **.venv** - Virtual environment with dependencies installed

## Troubleshooting

### "tmux: command not found"
Install tmux:
```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt-get install tmux

# CentOS/RHEL
sudo yum install tmux
```

### Tests don't run or show errors
Check that:
1. You're in the Neo directory: `pwd` should show `/path/to/Neo`
2. Virtual environment is set up: `.venv/bin/python3 --version`
3. Dependencies installed: `pip list | grep mcp`

### Want to stop everything
In any tmux window, press: `Ctrl-b :kill-session`

Or from outside tmux:
```bash
tmux kill-session -t neo-test-<timestamp>
```

## Creating New Tests

To add more tests to the runner, edit `run_parallel_tests.sh` and add a new `run_test` call:

```bash
run_test "my-test" \
    "python3 path/to/test.py" \
    "MY TEST: Description"
```

## Advanced Usage

### Run tests without attaching
```bash
./run_parallel_tests.sh -d  # Runs in background
tmux list-sessions          # See running sessions
```

### Watch a specific window
```bash
tmux send-keys -t neo-test-<timestamp>:0 "C-c"  # Stop current test
```

### Save test output to file
Inside tmux, enable logging:
```
Ctrl-b :capture-pane -p -S -30 > test-output.txt
```

## See Also

- `PHASE2_TEST_RESULTS.md` - Detailed test results and analysis
- `tests/test_phase2_waiting_agent_fix.py` - Unit test source code
- `tests/test_explicit_locks.py` - Lock mechanism tests

## Questions?

Run the tests and check the output. All three windows will show:
- ✅ Test counts and pass/fail status
- 📊 Detailed results for each scenario
- 🔧 Which Phase 2 fixes are working
