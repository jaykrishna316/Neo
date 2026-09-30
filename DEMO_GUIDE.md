# Neo Demo Guide

Quick links to Neo demonstration approaches:

## Choose Your Demo

### 🚀 **Automatic Demo** (Fastest - 2-3 minutes)
Multi-terminal demo that runs on a fixed timeline. Perfect for quick verification and CI/CD automation.

```bash
./scripts/launch_2dev_demo.sh      # 5 terminals, 2-developer scenario
./scripts/launch_3dev_demo.sh      # 7 terminals, 3-developer scenario
```

**What you'll see:**
- Multiple terminals open automatically
- Developers declaring intent sequentially
- Real-time activity log monitoring
- Lock states and queue positions
- Watchers showing conflict prevention
- Fresh context flowing between developers

See: [README - Automatic Demo](README.md#-automatic-demo-fastest---2-3-minutes)

---

### 📖 **Guided Interactive Demo** (Learning - 10-15 minutes)
Step-by-step demo with explanations. User controls pacing by pressing Enter.

```bash
./scripts/launch_guided_2dev_demo.sh      # 2-dev, step-by-step
./scripts/launch_guided_3dev_demo.sh      # 3-dev, with queue progression
```

**What you'll learn:**
- Numbered terminals for easy reference
- Explanations at each step
- "What's happening" → "What to look for" → "Key insights"
- Why Neo prevents conflicts
- How queue promotion works
- Context refresh behavior

See: [GUIDED_DEMO_README.md](GUIDED_DEMO_README.md)

---

### 🛠️ **Manual Terminal Test** (Thorough - 20-30 minutes)
Run Neo server with file watchers. Test at your own pace with real file editing.

```bash
# Terminal 1: Neo server
python -m cli.neo_server --clear

# Terminal 2+: File watchers and developers
export NEO_DEVELOPER=alice
python -m cli.file_watcher alice
```

**What you can test:**
- Real file watcher detection
- Intent declaration flows
- Lock behavior with actual file operations
- Context aggregation between developers
- Production-readiness validation

See: [`docs/LOCAL_TWO_DEVELOPER_TEST.md`](docs/LOCAL_TWO_DEVELOPER_TEST.md)

---

## Comparison

| Feature | Automatic | Guided | Manual |
|---------|-----------|--------|--------|
| **Setup** | 1 min | 1 min | 5-10 min |
| **Duration** | 2-3 min | 10-15 min | 20-30 min |
| **Automation** | ✅ Full | ✅ Partial | Manual |
| **Learning** | Quick view | Step-by-step | Deep understanding |
| **Best for** | Demos, CI/CD | Learning Neo | Testing production |

---

## Recommended Path

1. **Start here**: `./scripts/launch_2dev_demo.sh` (3 minutes)
   - See Neo in action
   - Understand the flow
   - Get excited

2. **Learn more**: `./scripts/launch_guided_2dev_demo.sh` (10 minutes)
   - Understand each step
   - See why Neo prevents conflicts
   - Learn queue behavior

3. **Test deeper**: `docs/LOCAL_TWO_DEVELOPER_TEST.md` (20 minutes)
   - Run Neo server yourself
   - Test with real file operations
   - Verify production-readiness

---

For full details, see [README.md](README.md#-neo-demonstrations)
