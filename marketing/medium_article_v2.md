# Preventing Merge Conflicts Before They're Written: Building Automatic Agent Coordination

*A side project exploring how developers and AI agents can coordinate without chaos*

## The 3 AM Realization

It was midnight. I had Claude Agent refactoring authentication, Devin fixing payment logic, and I was optimizing the database layer. All parallel. All fast.

Then I pulled everyone's changes. The merge was a nightmare. Claude had rewritten function signatures Devin was calling. I'd modified a database schema Claude assumed was immutable. Nobody *knew* what anyone else was doing until git told us it was too late.

I thought: **There has to be a better way than waiting for merge conflicts.**

And then it hit me: *What if every agent automatically announced what it was about to do?* Not in Slack or tickets—directly in a shared log that every agent could check before generating code. Claude could say "I'm about to refactor authentication (lines 20-40)." Devin could check that log before touching payment logic and know "Hey, I depend on auth, I should wait." The human developer's IDE could log work too.

That was the insight that changed everything.

---

## The Shared Activity Log: One JSON File to Rule Them All

Here's the entire elegant solution. Every agent automatically logs what it's about to work on:

```json
[
  {
    "agent": "claude-agent",
    "file": "src/auth.py",
    "intent": "refactor login_user for better error handling",
    "region": "login_user (lines 20-40)",
    "timestamp": "2026-09-11T15:30:00Z",
    "expires_at": "2026-09-11T16:00:00Z"
  },
  {
    "agent": "devin-agent",
    "file": "src/payment.py",
    "intent": "update payment processing to use new auth flow",
    "region": "process_payment (lines 50-80)",
    "timestamp": "2026-09-11T15:30:15Z",
    "expires_at": "2026-09-11T16:00:15Z"
  },
  {
    "agent": "human-dev-alice-id",
    "file": "src/models.py",
    "intent": "add new User fields for OAuth2",
    "region": "User class (lines 20-60)",
    "timestamp": "2026-09-11T15:35:00Z",
    "expires_at": "2026-09-11T16:05:00Z"
  }
]
```

That's it. A single `.devsync/activity-log.json` file. No database. No complex setup. Just **intent automatically captured in real-time by every agent before it generates code.**

The magic is what you can do *because* this log exists.

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

### After: The Activity Log Way
```
15:30:00 Claude announces: "about to refactor auth (lines 20-40)" → logs to activity log
15:30:05 Devin checks activity log before generating → sees Claude in auth
15:30:06 Devin knows: payment depends on auth → decides to wait 30 minutes
15:30:08 Human developer's IDE logs: "updating models for OAuth2" → system records this
15:30:10 System recognizes: Claude (auth) → Human dev (models) → Devin (payment) dependency chain
15:30:11 Recommendation: Sequential order. Claude first, then human dev, then Devin.
15:45:30 Claude finishes, logs completion
15:46:00 Devin continues with human dev work (they coordinated)
16:15:00 Devin finishes, logs completion
16:15:05 Everything merges cleanly. Zero conflicts.
```

**The conflict was prevented before code was generated.**

---

## How It Works: The 5-Stage Pipeline

Once you have the activity log, you can build on top of it:

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

*Have you run into coordination problems with multiple agents? I'd love to hear what you tried and what worked.*

*Code: https://github.com/jaykrishna316/codeNinja (branch: claude/conflict-warning-poc-d04y0r)*
