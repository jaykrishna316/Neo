# Neo 3.0: Conflict Prevention Engine - Implementation Plan

**Branch**: `neo-3.0` (cut from `neo-2.0`)  
**Status**: 🚀 Active Development  
**Last Updated**: 2026-09-18

---

## Executive Summary

Neo 3.0 adds a **Conflict Prevention Engine** on top of Neo 2.0's 5 phases and State Machine v2.

**Architecture**: Builds on existing Neo 2.0 foundation:
- Uses Phase 1 (Event Model) for intent data
- Uses Phase 2 (Handoffs) for context
- Uses Phase 3 (Context Invalidation) for predictions
- Uses Phase 4 (Provenance) for expertise
- Uses Phase 5 (Autonomy) for agent negotiation
- Uses State Machine v2 for developer queuing

**Value**: Shifts from "fix conflicts after they happen" → "prevent conflicts before they happen"

---

## Implementation Layers

### Layer 1: PREVENTION (70% value) - 5 Features
```
1A. Intent-Aware Path Detection      [Detects overlapping work intent]
1B. Concurrent Work Detection        [Tracks working sets in real-time]
1C. Temporal Conflict Prediction      [Predicts conflicts before merge]
1D. Semantic Invariant Checking       [Catches logical conflicts]
1E. Knowledge Gap Detection           [Prevents silent knowledge silos]
```

### Layer 2: UNDERSTANDING (20% value) - 3 Features
```
2A. Conflict Archaeology              [Shows full conflict story]
2B. Conflict Pattern Analysis         [Learn from conflicts]
2C. Conflict Causality Tracking       [Root cause analysis]
```

### Layer 3: RESOLUTION (10% value) - 3 Features
```
3A. Expertise-Based Resolution        [Resolve by authority]
3B. Intent-Based Conflict Merging     [Auto-merge orthogonal changes]
3C. Multi-Agent Negotiation           [Agents negotiate transparently]
```

---

## Module Structure

```
.claude/
├── conflict_prevention_engine.py     [Core engine orchestrator]
├── prevention/
│   ├── __init__.py
│   ├── intent_detection.py           [1A: Intent-Aware Path Detection]
│   ├── working_set_tracker.py        [1B: Concurrent Work Detection]
│   ├── temporal_predictor.py         [1C: Temporal Conflict Prediction]
│   ├── semantic_checker.py           [1D: Semantic Invariant Checking]
│   └── knowledge_gap_detector.py     [1E: Knowledge Gap Detection]
├── understanding/
│   ├── __init__.py
│   ├── conflict_archaeology.py       [2A: Conflict Archaeology]
│   ├── pattern_analyzer.py           [2B: Conflict Pattern Analysis]
│   └── causality_tracker.py          [2C: Conflict Causality Tracking]
├── resolution/
│   ├── __init__.py
│   ├── expertise_resolver.py         [3A: Expertise-Based Resolution]
│   ├── intent_merger.py              [3B: Intent-Based Merging]
│   └── agent_negotiator.py           [3C: Multi-Agent Negotiation]
└── utils/
    ├── __init__.py
    ├── alert_system.py               [Real-time alerting]
    ├── conflict_models.py            [Data structures]
    └── integration_helpers.py        [Neo 2.0 integration]

tests/
├── test_neo3_prevention.py           [Layer 1 tests]
├── test_neo3_understanding.py        [Layer 2 tests]
├── test_neo3_resolution.py           [Layer 3 tests]
└── test_neo3_integration.py          [End-to-end tests]

docs/
├── NEO_3.0_ARCHITECTURE.md
├── NEO_3.0_DEPLOYMENT.md
└── NEO_3.0_EXAMPLES.md
```

---

## Implementation Roadmap

### Phase 1: Foundation & Infrastructure (Days 1-2)
- ✅ Create neo-3.0 branch
- [ ] Create core conflict prevention engine orchestrator
- [ ] Create conflict models (data structures)
- [ ] Create alert system
- [ ] Create Neo 2.0 integration helpers
- [ ] Establish test framework

### Phase 2: Prevention Layer (Days 3-6)
- [ ] 1A: Intent-Aware Path Detection
- [ ] 1B: Concurrent Work Detection  
- [ ] 1C: Temporal Conflict Prediction
- [ ] 1D: Semantic Invariant Checking
- [ ] 1E: Knowledge Gap Detection
- [ ] Integration tests for all 5 features

### Phase 3: Understanding Layer (Days 7-8)
- [ ] 2A: Conflict Archaeology
- [ ] 2B: Conflict Pattern Analysis
- [ ] 2C: Conflict Causality Tracking
- [ ] Integration tests

### Phase 4: Resolution Layer (Days 9-10)
- [ ] 3A: Expertise-Based Resolution
- [ ] 3B: Intent-Based Conflict Merging
- [ ] 3C: Multi-Agent Negotiation
- [ ] Integration tests

### Phase 5: Integration & Validation (Days 11-12)
- [ ] End-to-end workflow tests
- [ ] Performance benchmarks
- [ ] Neo 2.0 compatibility verification
- [ ] Documentation

---

## Core Data Structures

### ConflictAlert
```python
{
  'alert_type': 'INTENT_OVERLAP' | 'CONCURRENT_WORK' | 'TEMPORAL_PREDICT' | 'SEMANTIC_VIOLATION' | 'KNOWLEDGE_GAP',
  'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
  'developer_1': str,
  'developer_2': str,
  'resource': str,  # file.py::function
  'reason': str,
  'timestamp': datetime,
  'suggested_action': str,
  'metadata': dict
}
```

### ConflictPattern
```python
{
  'pattern_id': str,
  'conflict_type': str,
  'frequency': int,
  'affected_resources': List[str],
  'involved_developers': List[str],
  'root_cause': str,
  'prevention_strategy': str,
  'last_occurrence': datetime
}
```

### IntentModel
```python
{
  'developer': str,
  'resource': str,
  'intent': str,  # "email validation fix", "performance optimization", etc.
  'timestamp': datetime,
  'scope': List[str],  # affected functions/modules
  'related_commits': List[str]
}
```

---

## Integration Points with Neo 2.0

### Phase 1 Integration (Event Model)
- Read from: `activity_log.get_developer_events(dev, time_window)`
- Extract: Intent from event descriptions and commit messages
- Feed to: Intent-Aware Path Detection (1A)

### Phase 2 Integration (Handoffs)
- Read from: `handoff.get_context(dev)`, `handoff.get_known_risks()`
- Extract: Developer intent, known work areas
- Feed to: Intent-Based Conflict Merging (3B)

### Phase 3 Integration (Context Invalidation)
- Read from: `context_engine.get_invalidated_contexts(resource)`
- Extract: Stale context signals
- Feed to: Temporal Conflict Prediction (1C)

### Phase 4 Integration (Provenance)
- Read from: `provenance.get_developer_expertise(dev)`, `provenance.get_expert_for_resource(resource)`
- Extract: Expertise scores, authority rankings
- Feed to: Expertise-Based Resolution (3A), Knowledge Gap Detection (1E)

### Phase 5 Integration (Autonomy)
- Read from: `autonomy_engine.get_active_policies()`, `autonomy_engine.get_agent_decision()`
- Feed to: Multi-Agent Negotiation (3C)

### State Machine v2 Integration
- Read from: `state_machine.get_resource_state(resource)`, `state_machine.get_queue(resource)`
- Extract: Developer queue position, lock holder
- Feed to: Concurrent Work Detection (1B)

---

## Success Criteria

### By Feature
- [ ] Each feature has unit tests (>90% coverage)
- [ ] Each feature integrates with Neo 2.0 without breaking changes
- [ ] Each feature has documentation with examples

### By Layer
- [ ] Prevention layer: Real-time alerts function correctly
- [ ] Understanding layer: Conflict analysis provides actionable insights
- [ ] Resolution layer: Smart resolution matches expected outcomes

### System-Level
- [ ] No impact on Neo 2.0 existing tests
- [ ] 50%+ reduction in conflict surprises (in test scenarios)
- [ ] Performance overhead <5% on Neo 2.0 operations
- [ ] End-to-end workflow with all 11 features working together

---

## File Tracking

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| NEO_3.0_IMPLEMENTATION_PLAN.md | ✅ CREATED | - | This roadmap |
| conflict_prevention_engine.py | 🚧 IN PROGRESS | - | Core orchestrator |
| prevention/*.py | 📋 PENDING | ~1000 | Layer 1 (1A-1E) |
| understanding/*.py | 📋 PENDING | ~500 | Layer 2 (2A-2C) |
| resolution/*.py | 📋 PENDING | ~500 | Layer 3 (3A-3C) |
| utils/*.py | 📋 PENDING | ~300 | Infrastructure |
| tests/test_neo3_*.py | 📋 PENDING | ~1500 | Test suite |
| docs/*.md | 📋 PENDING | ~2000 | Documentation |

**Total Expected**: ~6,300 lines of code + documentation

---

## Next Steps

1. ✅ Branch created: `neo-3.0`
2. 🚧 Create core orchestrator
3. 🚧 Build prevention layer (1A-1E)
4. 🚧 Build understanding layer (2A-2C)
5. 🚧 Build resolution layer (3A-3C)
6. 🚧 Comprehensive testing
7. 🚧 Documentation & examples

---

**Current Branch**: `neo-3.0`  
**Lock**: ACTIVE - All work on neo-3.0 only until user says otherwise
