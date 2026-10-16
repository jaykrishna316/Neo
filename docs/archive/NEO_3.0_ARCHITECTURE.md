# Neo 3.0: Conflict Prevention Engine - Architecture Guide

**Version**: 3.0  
**Branch**: `neo-3.0`  
**Status**: 🚀 Core Implementation Complete  
**Date**: 2026-09-18

---

## Executive Summary

Neo 3.0 adds a **Conflict Prevention Engine** on top of Neo 2.0's foundation. It shifts from "fix conflicts after they happen" to "prevent conflicts before they happen" through three integrated layers:

- **Layer 1: Prevention (70% value)** - Stop conflicts before they start
- **Layer 2: Understanding (20% value)** - Learn from conflicts that do occur
- **Layer 3: Resolution (10% value)** - Handle conflicts efficiently when they happen

**Key Achievement**: All 11 features (1A-1E, 2A-2C, 3A-3C) fully implemented with Neo 2.0 integration points identified.

---

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│              Conflict Prevention Engine                  │
│  (conflict_prevention_engine.py - Main Orchestrator)    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Prevention      Understanding   Resolution
   Layer (1A-1E)   Layer (2A-2C)   Layer (3A-3C)
        │              │              │
        └──────┬───────┴────┬────────┘
               ▼            ▼
         Alert System  Conflict Models
               │            │
               └────┬───────┘
                    ▼
         Neo 2.0 Integration Layer
```

### Module Organization

```
.claude/
├── conflict_prevention_engine.py       [Main orchestrator]
├── conflict_models.py                  [11 data models]
├── alert_system.py                     [Alert management]
│
├── prevention/                         [Layer 1: Prevention]
│   ├── intent_detection.py            [1A: Intent overlap detection]
│   ├── working_set_tracker.py         [1B: Real-time work tracking]
│   ├── temporal_predictor.py          [1C: Conflict prediction]
│   ├── semantic_checker.py            [1D: Invariant violations]
│   └── knowledge_gap_detector.py      [1E: Knowledge silos]
│
├── understanding/                      [Layer 2: Understanding]
│   ├── conflict_archaeology.py        [2A: Conflict story analysis]
│   ├── pattern_analyzer.py            [2B: Systemic pattern detection]
│   └── causality_tracker.py           [2C: Root cause analysis]
│
└── resolution/                         [Layer 3: Resolution]
    ├── expertise_resolver.py          [3A: Expertise-based resolution]
    ├── intent_merger.py               [3B: Auto-merge orthogonal changes]
    └── agent_negotiator.py            [3C: Agent negotiation]
```

---

## Layer 1: Prevention (1A-1E)

### 1A: Intent-Aware Path Detection

**Purpose**: Detect when developers have overlapping work intents before they conflict

**Class**: `IntentDetector`

**Key Methods**:
- `extract_intent_from_event()` - Parse intent from commits/PRs
- `detect_overlaps()` - Find overlapping developer intents
- `get_intent_compatibility()` - Check if intents are compatible

**Integration with Neo 2.0**:
- Reads from Phase 1 (Event Model) activity log
- Extracts intent descriptions and commit messages
- Feeds into conflict prediction

**Example Output**:
```
Intent: dev1 = "Add email validation to auth module"
Intent: dev2 = "Refactor email validation"
→ Overlap detected: ['auth', 'email', 'validation']
→ Alert: Coordinate work on email validation module
```

---

### 1B: Concurrent Work Detection

**Purpose**: Track developers' current working sets in real-time

**Class**: `WorkingSetTracker`

**Key Methods**:
- `update_working_set()` - Track what developer is working on
- `detect_overlaps()` - Find overlapping work zones
- `get_developers_on_resource()` - Who's touching this file?

**Integration with Neo 2.0**:
- Reads from State Machine v2 (who's editing what)
- Tracks file and function-level granularity
- Feeds into temporal predictor

**Example Output**:
```
Active Developers: 3
  dev1: [auth.py::login, auth.py::validate]
  dev2: [auth.py::validate, email.py::send]  ← Overlap!
  dev3: [cache.py::invalidate]

Overlapping Work:
  dev1 ↔ dev2: auth.py::validate
→ Alert: Both developers in same neighborhood
```

---

### 1C: Temporal Conflict Prediction

**Purpose**: Predict conflicts before they happen

**Class**: `TemporalPredictor`

**Key Methods**:
- `predict_conflict()` - Calculate conflict probability
- `record_context_invalidation()` - Track stale context
- `record_developer_activity()` - Log access patterns

**Integration with Neo 2.0**:
- Reads from Phase 3 (Context Invalidation)
- Detects when context becomes invalidated
- Predicts conflicts at merge time

**Prediction Factors**:
- Context invalidation (40% weight)
- Recent concurrent activity (40% weight)
- Historical conflict frequency (20% weight)

**Example Output**:
```
Predicting: dev1 ↔ dev2 on auth.py::validate
Risk Score: 0.78 (78% probability)
Time Until Conflict: ~120 minutes

Factors:
- Context invalidated 15 mins ago (recent)
- 3 activities in last 2 hours
- High-conflict resource (5 past conflicts)

Suggestion: Coordinate merge strategy before 2 hours
```

---

### 1D: Semantic Invariant Checking

**Purpose**: Detect logical conflicts that git can't see

**Class**: `SemanticChecker`

**Key Methods**:
- `register_invariant()` - Define code contracts
- `check_change()` - Verify change doesn't violate invariants

**Example Invariants**:
- `user_id must never be null`
- `API must maintain backward compatibility`
- `Cache invalidation must happen before update`

**Integration with Neo 2.0**:
- Extracts invariants from code and documentation
- Validates changes against invariants
- Prevents semantic violations

**Example Output**:
```
Violation Detected!
Change: Remove null check for user_id
Resource: auth.py
Invariant: user_id must never be null (CRITICAL)
Severity: CRITICAL

Suggestion: Restore null check or refactor to handle null
```

---

### 1E: Knowledge Gap Detection

**Purpose**: Prevent siloed expertise from causing conflicts

**Class**: `KnowledgeGapDetector`

**Key Methods**:
- `register_expert()` - Mark who's the expert
- `detect_gap()` - Find non-experts working without expert input
- `suggest_pairing()` - Recommend mentor/expert pairing

**Integration with Neo 2.0**:
- Reads from Phase 4 (Provenance) expertise scores
- Identifies experts for each module
- Suggests knowledge transfer

**Example Output**:
```
Knowledge Gap Detected!
Developer: bob
Expert: alice
Resource: crypto.py

Alice's Expertise Score: 95%
Alice's Modifications: 47

Risk Level: CRITICAL
Suggestion: Consider pairing with @alice for better code quality
Learning Opportunity: Learn from alice's 47 modifications to crypto.py
```

---

## Layer 2: Understanding (2A-2C)

### 2A: Conflict Archaeology

**Purpose**: Show the full story of a conflict

**Class**: `ConflictArchaeologist`

**Reconstructs**:
- Original state (before both changes)
- Dev1's version (what changed and why)
- Dev2's version (what changed and why)
- Conflicting vs independent sections

**Example Output**:
```
📖 Conflict Story: conflict_2026_09_18_001

Resource: auth.py::validate_email
Developers: dev1 ↔ dev2

👤 dev1's Work:
   Intent: Add email validation with regex pattern
   Change: Add 15 lines of email validation logic
   Lines Affected: 42-57

👤 dev2's Work:
   Intent: Optimize email validation performance
   Change: Replace with compiled regex cache
   Lines Affected: 42-50

⚔️ Conflict Analysis:
   Conflicting Lines: 8 (42-50)
   Independent Changes: 7 (51-57)
   Intents Compatible: Yes (both improve validation)
   
Resolution: Could have been auto-merged (intents orthogonal)
```

---

### 2B: Conflict Pattern Analysis

**Purpose**: Identify systemic conflict patterns

**Class**: `PatternAnalyzer`

**Pattern Types**:
- `high_conflict_module` - Module with 3+ conflicts
- `team_silo` - Same developers repeatedly conflicting
- `architectural_violation` - Design pattern violations

**Example Output**:
```
🔍 Conflict Pattern Analysis

Total Patterns: 3
Average Frequency: 3.7

🔴 High-Frequency Patterns:

Pattern: high_conflict_module
Frequency: 5 occurrences
Resource: auth.py

Pattern: team_silo
Frequency: 3 occurrences
Developers: dev1, dev2 (keep conflicting on email module)

Prevention Strategy: Improve communication between dev1 and dev2
```

---

### 2C: Conflict Causality Tracking

**Purpose**: Analyze root causes to prevent recurrence

**Class**: `CausalityAnalyzer`

**Root Cause Categories**:
- Insufficient Communication
- Misaligned Requirements
- Unclear Module Boundaries
- Concurrent Modifications

**Example Analysis**:
```
🔬 Conflict Causality Analysis

Root Cause: Misaligned Requirements
Contributing Factors:
  • Lack of Developer Synchronization
  • Poor Documentation of Module
  • No Code Review Before Merge

Prevention Opportunities:
  ✓ Document requirements more clearly
  ✓ Conduct design review before implementation
  ✓ Require code review before merge

Similar Past Conflicts:
  • conflict_2026_09_10_003
  • conflict_2026_09_05_007
```

---

## Layer 3: Resolution (3A-3C)

### 3A: Expertise-Based Resolution

**Purpose**: Resolve conflicts based on developer expertise

**Class**: `ExpertiseResolver`

**Resolution Logic**:
- If expertise difference > 0.2: Expert wins (high confidence)
- If expertise similar: Need manual review or other criteria
- Establishes clear hierarchy for each resource

**Integration with Neo 2.0**:
- Reads from Phase 4 (Provenance) expertise scores
- Uses modification history as expertise indicator

**Example Output**:
```
Resolving conflict between dev1 and dev2 on crypto.py

Expertise Scores:
  dev1: 0.65 (15 modifications)
  dev2: 0.92 (47 modifications)

Resolution: dev2 wins
Confidence: 0.92
Reasoning: dev2 is significantly more experienced with crypto.py
```

---

### 3B: Intent-Based Conflict Merging

**Purpose**: Auto-merge when intents are orthogonal

**Class**: `IntentMerger`

**Auto-Merge Strategy**:
1. Analyze intent compatibility
2. Check change overlap
3. Auto-merge if intents don't conflict

**Merge Results**:
- `auto_merged` - Changes are orthogonal, safe to merge
- `manual_required` - Intents conflict, need human review
- `expert_decision` - Likely orthogonal but needs expert validation

**Example Output**:
```
Intent Analysis:

dev1 Intent: "Add logging to auth flow"
dev2 Intent: "Optimize cache logic"

Compatibility: ✓ Compatible (no keyword overlap)
Change Overlap: 8% (very little)

Result: auto_merged
Confidence: 0.92

Why: Intents are orthogonal, changes don't overlap,
     can safely merge both changes together
```

---

### 3C: Multi-Agent Negotiation

**Purpose**: Have autonomous agents negotiate when they disagree

**Class**: `AgentNegotiator`

**Negotiation Policies**:
1. Confidence-based (higher confidence wins)
2. Priority-based (per-resource priorities)
3. Seniority-based (expert has authority)

**Example Output**:
```
Agent Negotiation: agent_validator vs agent_optimizer

agent_validator:
  Decision: Reject change (violates validation invariant)
  Confidence: 0.95
  Reasoning: Change removes required null check

agent_optimizer:
  Decision: Apply change (performance critical)
  Confidence: 0.75
  Reasoning: Optimization improves P99 latency

Negotiation Policy: confidence_based
Winner: agent_validator
Confidence: 0.95
Reasoning: Higher confidence and correctness > performance
```

---

## Neo 2.0 Integration Points

### Phase 1: Event Model & Development Memory
```
Neo 3.0 Integration:
  ↓ Reads from
  - activity_log.get_developer_events(dev, time_window)
  - Extract intent from event descriptions
  - Feed to: Intent Detection (1A)
```

### Phase 2: Temporal Handoff Engine
```
Neo 3.0 Integration:
  ↓ Reads from
  - handoff.get_context(dev)
  - handoff.get_known_risks()
  ↓ Feeds to
  - Intent-Based Merging (3B)
  - Conflict Archaeology (2A)
```

### Phase 3: Context Invalidation Engine
```
Neo 3.0 Integration:
  ↓ Reads from
  - context_engine.get_invalidated_contexts(resource)
  ↓ Feeds to
  - Temporal Conflict Prediction (1C)
  - Causality Tracking (2C)
```

### Phase 4: Reviewer Provenance Engine
```
Neo 3.0 Integration:
  ↓ Reads from
  - provenance.get_developer_expertise(dev)
  - provenance.get_expert_for_resource(resource)
  ↓ Feeds to
  - Knowledge Gap Detection (1E)
  - Expertise-Based Resolution (3A)
```

### Phase 5: Agent Autonomy Engine
```
Neo 3.0 Integration:
  ↓ Reads from
  - autonomy_engine.get_active_policies()
  - autonomy_engine.get_agent_decision()
  ↓ Feeds to
  - Multi-Agent Negotiation (3C)
```

### State Machine v2
```
Neo 3.0 Integration:
  ↓ Reads from
  - state_machine.get_resource_state(resource)
  - state_machine.get_queue(resource)
  ↓ Feeds to
  - Concurrent Work Detection (1B)
```

---

## Data Flow Example: End-to-End Conflict Prevention

```
1. Developer Activity
   └─ dev1 & dev2 start working on auth.py::validate

2. Working Set Detection (1B)
   └─ tracker.update_working_set('dev1', ['auth.py::validate'])
   └─ tracker.update_working_set('dev2', ['auth.py::validate'])
   └─ Detects overlap!

3. Intent Detection (1A)
   └─ dev1 intent: "Add email validation"
   └─ dev2 intent: "Optimize validation performance"
   └─ Intents analyzed

4. Temporal Prediction (1C)
   └─ Context invalidation detected on auth.py
   └─ 2 developers active + context invalid
   └─ Risk: 0.75 (high)
   └─ Alert: "Coordinate merge strategy in next 2 hours"

5. Knowledge Gap Check (1E)
   └─ alice is expert on auth (0.95 score)
   └─ dev2 hasn't paired with alice
   └─ Alert: "Consider pairing with @alice"

6. If conflict occurs...

7. Conflict Archaeology (2A)
   └─ Reconstruct both versions
   └─ Analyze intent compatibility

8. Intent-Based Merging (3B)
   └─ Intents orthogonal? Yes!
   └─ Change overlap? 5%
   └─ Result: Auto-merge with 0.92 confidence

9. Pattern Analysis (2B)
   └─ Same pair conflicting on auth multiple times?
   └─ Pattern: team_silo on auth.py
   └─ Suggestion: Improve communication

10. Causality Tracking (2C)
    └─ Root cause: Misaligned requirements
    └─ Prevention: Conduct design review before implementation
    └─ Lesson: Define validation strategy upfront
```

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~3,500+ |
| Modules Created | 13 |
| Data Models | 11 |
| Prevention Features | 5 (1A-1E) |
| Understanding Features | 3 (2A-2C) |
| Resolution Features | 3 (3A-3C) |
| Neo 2.0 Integration Points | 6 (Phases 1-5 + SM v2) |

---

## Usage Example

```python
from conflict_prevention_engine import ConflictPreventionEngine
from prevention.intent_detection import IntentDetector
from prevention.working_set_tracker import WorkingSetTracker

# Initialize engine
engine = ConflictPreventionEngine()

# Register developers' work
detector = IntentDetector()
intent1 = detector.extract_intent_from_event('dev1', {
    'commit_message': 'Add email validation'
})
detector.register_intent(intent1)

tracker = WorkingSetTracker()
tracker.update_working_set('dev1', ['auth.py::validate'])
tracker.update_working_set('dev2', ['auth.py::validate'])

# Detect overlaps
overlaps = tracker.detect_overlaps()
if overlaps:
    for dev1, dev2, resources in overlaps:
        engine.detect_concurrent_work(dev1, dev2)
        engine.predict_conflict(dev1, dev2, resources[0])

# Print status
engine.print_status()
```

---

## Next Steps

1. ✅ Core infrastructure implemented
2. ✅ All 11 features implemented
3. ✅ Neo 2.0 integration points identified
4. 🚧 Comprehensive test suite (in progress)
5. 🚧 End-to-end integration tests
6. 🚧 Performance benchmarking
7. 🚧 Documentation and examples

---

**Current Branch**: `neo-3.0`  
**Status**: 🚀 Core Implementation Complete - Ready for Testing  
**Lock**: All work on neo-3.0 only
