# LinkedIn Post v2: Shared Activity Logs

## Main Post:

I built something while procrastinating on actual work, and it just clicked.

**The Problem:** When Claude Agent, Devin, and I work in parallel on the same codebase, conflicts happen *after* code is checked in. Git catches them. But by then it's too late—merge hell.

**The Insight:** What if every agent (Claude, Devin, Codex, etc.) automatically announced what it was about to work on *before* actually generating code? Not through Slack or tickets—directly in a shared log that's accessible to all agents in real-time.

**The Solution:** A **shared activity log** automatically maintained by agents:
```
{
  "agent": "claude-agent",
  "file": "src/auth.py",
  "intent": "refactor login_user",
  "region": "lines 20-40",
  "timestamp": "2026-09-11T15:30:00Z"
}
```

The moment Claude Agent logs this intent (before generating), Devin can check: *"Is anyone already here? Should I wait or coordinate?"* 

No manual logging. No git checks. **Just real-time awareness built into the agent workflow.**

## Why This Matters:

❌ **Old way:** Code → Commit → Push → Conflict detected → Merge nightmare
✅ **New way:** Agent announces intent → Logs to shared activity → Checks for overlaps → Coordinates → Zero conflicts

It's the difference between **fixing fires vs preventing them.**

From this single log that agents automatically maintain, everything else became possible:
- Detect overlaps *before* any agent generates code
- Score conflict risk in milliseconds
- Recommend resolution strategies (sequential, parallel, cherry-pick)
- Predict how long each agent/developer will be working (pattern learning)
- Route work to the right agent for the job

But the *log itself* is the magic. It's so simple. One JSON file that agents auto-update. Real-time coordination without human intervention.

## What I Built:

A system that watches this activity log and:
1. **Detects conflicts in <100ms** — faster than you can type
2. **Scores them 0-100** — not just "HIGH/MEDIUM/LOW" 
3. **Recommends strategies** — sequential, parallel, cherry-pick, manual
4. **Learns developer patterns** — predicts who finishes when
5. **Matches expertise** — Alice knows auth, Claude knows refactoring

All from a shared activity log.

## The Kicker:

Conflicts are **prevented before code is generated.** Claude waits for Devin. Devin waits for human developers. No messy merges. No git nightmares. No manual coordination.

Everything is automatic. Everything is real-time. Agents work in parallel safely because they actually know what each other is doing.

---

**Try it:** https://github.com/jaykrishna316/codeNinja (branch: claude/conflict-warning-poc-d04y0r)

Built this for fun while exploring how AI agents could actually work *with* humans, not around them.

#AI #SoftwareDevelopment #BuildInPublic #ConflictDetection

---

### Optional Closing Lines:
- "Would love to hear if anyone else has run into this problem"
- "Drop a 🔍 if you want to play with the dashboard"
- "Built with Claude. Still amazed at how much you can do with simple ideas"
