# Preventing Merge Conflicts Before They're Written: Building Automatic Agent Coordination

*A side project exploring how developers and AI agents can coordinate without chaos*

## The 3 AM Realization

It was midnight. I had Claude Agent refactoring authentication, Devin fixing payment logic, and I was optimizing the database layer. All parallel. All fast.

Then I pulled everyone's changes. The merge was a nightmare. Claude had rewritten function signatures Devin was calling. I'd modified a database schema Claude assumed was immutable. Nobody *knew* what anyone else was doing until git told us it was too late.

I thought: **There has to be a better way than waiting for merge conflicts.**

And then it hit me: *What if every agent automatically announced what it was about to do?* Not in Slack or tickets—directly in a shared log that every agent could check before generating code. Claude could say "I'm about to refactor authentication (lines 20-40)." Devin could check that log before touching payment logic and know "Hey, I depend on auth, I should wait." The human developer's IDE could log work too.

That was the insight that changed everything.

---

## The Architecture: A State Machine, Not Just a Log

The shared activity log is the foundation. But on top of it is a **state machine** that orchestrates everything.

```json
{
  "agent": "claude-agent",
  "file": "src/auth.py",
  "intent": "refactor login_user",
  "region": "lines 20-40",
  "state": "ACTIVE",
  "timestamp": "2026-09-11T15:30:00Z",
  "expires_at": "2026-09-11T16:00:00Z"
}
```

That `state` field is the key. It tracks **where in the coordination lifecycle** this work is:

- **ACTIVE** — Agent is generating code right now
- **LOCKED** — High risk conflict detected. Awaiting decision from other agent.
- **WAITING** — Agent chose to pause. Checkpoint saved. Sleeping until event.
- **COLLABORATE** — Agents reached out to work together
- **COMPLETED** — Agent finished. Work is done.
- **LOCK_REMOVED** (event) — Fires when it's safe to wake up
- **RESUMED** — Agent woke up and is continuing

This isn't just a log—it's a **distributed state machine** for multi-agent coordination.

---

## Why This Changes Everything

### Before: The Git Way
```
15:30:00 Claude Agent starts generating auth refactor
15:30:15 Devin agent independently starts working on payment logic
15:30:20 Human developer starts updating models (connected via IDE)
15:45:00 Claude pushes changes (rewrites auth function signatures)
15:50:00 Devin pushes (breaks because auth signatures changed!)
15:55:00 Human developer pushes (conflicts in models!)
16:00:00 Merge nightmare begins
```

### After: The State Machine Way
```
15:30:00 Claude logs: state=ACTIVE, intent="refactor auth"
15:30:05 Devin checks before generating → sees Claude in auth (state=ACTIVE)
15:30:06 System detects HIGH RISK (80/100) → Devin gets options
15:30:07 Devin chooses: WAIT (saves checkpoint, enters WAITING state)
15:30:08 Devin's Claude: saves context → sleeps → subscribes to event
        (no polling, no token waste, just sleeping)

15:45:00 Claude finishes → logs state=COMPLETED
15:45:01 System fires: lock_removed event
15:45:02 Devin's Claude: WAKES UP automatically (event-driven!)
15:45:03 Devin resumes from EXACT CHECKPOINT
        (context preserved, no lost work, just continues)

15:50:00 Devin finishes, logs state=COMPLETED
16:00:00 Everything merged cleanly. Zero conflicts. No wasted tokens.
```

**The conflict was prevented before code was generated. Agents never blocked each other. Everything was automatic.**

---

## How It Works: The State Machine + Event System

This is where it gets elegant. Instead of just detecting conflicts and blocking, the system uses **state transitions** + **event-driven wake-ups**.

### States

**Developer A (Actively Working)**
- `ACTIVE`: Agent is generating code. Intent logged with this state.
- `COMPLETED`: Agent finished. Work is done. Logs completion.

**Developer B (When Encountering HIGH Risk)**
- `LOCKED`: System detects conflict. Developer B gets decision options.
- `WAITING`: Developer B chose to wait. Saves checkpoint, enters sleep.
- `COLLABORATE`: Developer B reached out. Both devs notified to sync.
- `RESUMED`: Lock removed event fired. Developer B wakes up.

### The Checkpoint System

When Developer B chooses to WAIT, the system saves:
```python
checkpoint = {
    "agent_id": "devin-agent",
    "intent": "add validation to login_user",
    "region": "lines 25-50",
    "tokens_generated": 150,
    "context_buffer": "Devin's full prompt/context so far",
    "timestamp": "2026-09-11T15:30:15Z"
}
```

This is crucial: when Developer B's Claude wakes up, it has **full context**. No lost work. No lost intent. Just resume.

### The Event System

No polling. No "wait 20 minutes and hope."

Instead:
1. Developer B subscribes to `lock_removed` event
2. Developer B's Claude enters sleep (no token waste)
3. When Developer A finishes → system fires `lock_removed` event
4. Developer B's Claude wakes **immediately** and resumes

This is async/await for distributed agents.

### Decision Options When Locked

When Developer B hits a HIGH RISK lock, it gets three choices:

1. **COLLABORATE**: "Developer A is here. Want to sync up and work together?"
   - Both devs notified. Can pair program, divide work, or coordinate.

2. **WAIT**: "I'll pause and resume when you're done."
   - Saves checkpoint, sleeps, wakes automatically on event.

3. **WRAP_UP_REQUEST**: "Can you finish soon? I have parallel work."
   - Developer A sees someone is waiting. May expedite.

---

## The 5-Stage Detection Pipeline

Once you have the activity log + state machine, you can build higher-level capabilities:

### Stage 1: Real-Time Detection

The moment a new intent is logged, the system asks: **"Does this overlap with anything active?"**

```python
def detect_overlaps(new_entry):
    overlaps = []
    for existing in activity_log:
        if existing["file"] == new_entry["file"]:
            if regions_overlap(existing["region"], new_entry["region"]):
                overlaps.append(existing)
    return overlaps
```

This runs in milliseconds. Alice logs. Claude checks. Instant answer.

**Why this is better than git:** Git only knows about committed code. The activity log knows about intent *before* any code is written.

### Stage 2: Smart Scoring

Not all overlaps are equal. Alice refactoring authentication while Claude adds type hints is one thing. But if Bob is *renaming* the function Alice is refactoring? That's a blocker.

The system scores conflicts 0-100:

```python
score = (
    conflict_count * 30 +           # How many are conflicting?
    conflict_type_severity * 25 +   # Are they renaming? Deleting?
    git_confidence * 15 +            # Is this a real overlap?
    code_overlap * 15 +              # How much overlaps?
    time_pressure * 10 +             # How long has it been active?
    velocity_impact * 5              # Are fast devs blocked?
) / 100
```

Result: A 0-100 score that says **exactly how bad** the conflict is. Not just "HIGH" or "MEDIUM."

### Stage 3: Resolution Strategies

Once we know there's a conflict, the system recommends how to resolve it:

**Sequential:** "Alice finishes (15m), then Claude (10m), then Bob" → 35m total, LOW risk
**Parallel:** "All three go at once, coordinate merges" → 15m total, HIGH risk
**Cherry-Pick:** "Bob's non-overlapping work first (5m), then coordinate the overlap" → 20m total, MEDIUM risk
**Manual:** "This needs human judgment" → 45m total, LOW risk

Each strategy comes with effort/time/risk estimates.

### Stage 4: Pattern Learning

Here's where it gets interesting. I track how long each developer actually takes:

```python
alice_patterns = {
    "refactoring": {
        "median": 900,           # 15 minutes
        "stdev": 150,            # consistent
        "samples": 45
    },
    "feature_work": {
        "median": 1200,          # 20 minutes
        "stdev": 300,            # less consistent
        "samples": 32
    }
}
```

When Alice logs "refactor auth.py," the system knows: **She'll probably finish in 15-17 minutes.** Not a guess. Based on her actual history.

Claude can wait 20 minutes (confidence interval) instead of "I dunno, 5 minutes?" or "I'll wait forever."

### Stage 5: Expertise Matching

The system learns who's best at what:

```python
alice_profile = {
    "speed": 85,              # Fast median completion
    "consistency": 90,        # Predictable
    "expertise_level": "specialist",
    "skills": ["auth", "payment", "api"],
    "confidence": 95          # Based on 50+ completed tasks
}

claude_profile = {
    "speed": 88,
    "consistency": 92,
    "expertise_level": "expert",
    "skills": ["types", "refactoring", "tests"],
    "confidence": 95
}
```

When recommending who should handle the next change: **Match it to the right person.** Alice for auth? Claude for refactoring? Devin for infrastructure?

---

## The Real Value: Prevention, Not Cure

Here's the thing that excites me most:

**Most conflict resolution tools are firefighting:** Git detects the conflict after it happens. Then you spend 2 hours fixing it.

**This is preventive:** The conflict never happens. Code is never written that breaks other code. Because coordination happened *before* anyone typed anything.

Think about the implications:
- ✅ Agents never block each other (except when they absolutely must)
- ✅ Humans never deal with merge nightmares
- ✅ Teams can run N agents + N developers in parallel **safely**
- ✅ Everything happens in real-time (no "wait for CI," no "hope this works")

The activity log is the linchpin. It's the single source of truth that makes everything else possible.

---

## What Surprised Me

### Surprise 1: Simplicity Works
I expected I'd need a database, a backend API, complex state management. Instead? A JSON file on disk works great. Append-only. Easy to reason about. Easy to sync.

### Surprise 2: Pattern Learning is Powerful
I thought "developer patterns" would be a nice-to-have. Turns out it's essential. When you know Alice finishes authentication in 15±2 minutes, waiting 20 minutes isn't a guess—it's data-driven.

### Surprise 3: Git Analysis Eliminates False Positives
I was skeptical about parsing function signatures. But being able to say "Alice is refactoring login_user at lines 20-40" and Claude is adding type hints at lines 25-35, so there's a **real function-level overlap"** vs "they're in the same file so maybe?" reduces false positives by 60%.

### Surprise 4: Agents Get It
I thought coordinating AI agents would be hard. Turns out they understand "wait until this person is done" immediately. No complex negotiation. No game theory. Just: "Is anyone else here? → Yes → Wait or coordinate."

---

## Real Scenario: Cascading Conflicts (All Automatic)

This is where the activity log + prediction shines:

**15:30** Claude Agent announces (auto-logs): "Refactor payment.py (process_payment, lines 20-60)"
**15:30** System learns: Claude will finish in ~18 minutes (pattern: 900s median on refactors)

**15:32** Devin Agent checks before generating, sees Claude in payment
**15:32** Devin knows: "My payment flow changes depend on Claude's refactor"
**15:32** Devin decides: "I'll wait 20 minutes, then proceed"

**15:35** Human developer (via IDE) starts: "Add audit logging to payment processing"
**15:35** System logs this automatically via their agent ID
**15:35** System detects: Human dev depends on Claude's refactor AND Devin's auth updates
**15:35** Recommendation: "Claude first → Devin second → You last"

**16:15** All done. Zero conflicts. Perfect merge. Everything coordinated automatically before any code was written.

---

## The Implementation

Here's how agents integrate this. It's automatic:

```python
# 1. Agent (Claude, Devin, etc.) logs intent BEFORE generating code
activity_log.append({
    "agent": "claude-agent",
    "file": "src/auth.py",
    "intent": "refactor login_user",
    "region": "login_user (lines 20-40)",
    "timestamp": datetime.now().isoformat(),
    "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat()
})

# 2. Other agents check the log before generating their code
conflicts = detector.check(
    file="src/auth.py",
    region="lines 15-50",
    agent="devin-agent"  # Devin checks if it should wait
)

if conflicts:
    print(f"Risk: {conflicts['score']}/100")
    print(f"Wait: {conflicts['recommended_wait']}s")
    print(f"Strategy: {conflicts['strategy']}")
    # Devin waits. Or coordinates.
    
# 3. Agent logs completion when done
activity_log.mark_complete("claude-agent")
# Now Devin can proceed
```

Human developers? Their IDE/editor logs their work too, using their connected agent ID. Same system. Same log. All participants visible to each other.

---

## What I Learned Building This

1. **Coordination beats speed.** A slower sequential execution with zero conflicts beats a chaotic parallel with merge nightmares.

2. **Intent is more valuable than code.** Knowing what someone is *about to do* is more useful than seeing what they *already did.*

3. **Simple models work.** Pattern learning with median + stdev is surprisingly effective. No ML needed.

4. **Real-time beats eventual consistency.** By the time git told me about the conflict, 2 hours of work was already wasted. Activity log prevents that same 2 hours from happening.

5. **Agents are eager to coordinate.** I expected adversarial behavior or competition for resources. Instead, agents immediately understood: "If Alice is here, I wait." Done.

---

## Conclusion: A Different Approach to Concurrency

The whole premise of modern development is: **Multiple people touching the same codebase is hard.**

It is. But what if we changed the question?

Instead of: *"How do we resolve conflicts after they happen?"*

Ask: *"How do we prevent conflicts before they happen?"*

The shared activity log is the answer. It's so simple, it feels like it should have always existed. And once you have it, everything else—scoring, strategies, expertise matching, pattern learning—becomes just engineering details on top.

This side project started as a way to keep my AI agents from killing each other's code. It turned into something deeper: a new model for how developers (human and AI) can safely work in parallel.

That's the real value.

---

## See It In Action: Real Agents, Real API Calls

Theory is great. But here's what matters: **it actually works.**

Stop reading. Pull the repo and run this:

```bash
export ANTHROPIC_API_KEY="sk-..."
python3 examples/claude_coordination_demo.py
```

Watch it happen:
1. Agent A logs: "Refactoring auth.py (lines 40-80)"
2. Agent B checks: "Is it safe to work here?"
3. Neo detects: "HIGH RISK - risk score 82/100"
4. Agent B decides: "I'll wait"
5. Agent B saves checkpoint, sleeps (no polling, no tokens wasted)
6. Agent A generates code (real Claude API call)
7. Agent A completes → event fires
8. Agent B wakes automatically, loads checkpoint, resumes
9. Agent B generates code (real Claude API call)
10. Result: **Zero merge conflicts.** Clean, sequential commits.

No theory. No promises. Just working coordination with two real Claude agents making actual API calls.

That's the proof.

---

*Have you run into coordination problems with multiple agents? I'd love to hear what you tried and what worked.*

*Code: https://github.com/yourusername/Neo (main branch: open-source-ready)*
*Demo: `python3 examples/claude_coordination_demo.py` (requires ANTHROPIC_API_KEY)*
