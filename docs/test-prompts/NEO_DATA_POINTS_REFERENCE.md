# Neo Complete Data Points Reference

This document lists **EVERY data point Neo can measure and display** across conflict detection, impact analysis, context staleness, and all other capabilities.

---

## Quick Start: Running the Complete Test

```bash
# Terminal 1: Run the comprehensive 2-developer test
python3 test-complete-2dev.py

# Terminal 2: Monitor activity in real-time  
python3 monitor-complete-activity.py --duration 120 --interval 2
```

---

## 1. CONFLICT DETECTION METRICS

### Risk Assessment
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Risk Level | `risk_classifier.py` | LOW / MEDIUM / HIGH | Overall conflict risk assessment |
| Conflict Reason | `risk_classifier.py` | string | Specific reason for conflict classification |
| Risk Score | `conflict_scorer.py` | 0-100 | Numerical conflict score |
| Confidence | `risk_classifier.py` | 0.0-1.0 | How confident the assessment is |

### Symbol Analysis
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Direct Overlap | `semantic_conflict_detector.py` | symbol list | Functions/classes both developers changed |
| Symbol Count | `semantic_conflict_detector.py` | integer | Total symbols in file |
| Symbol Names | `semantic_conflict_detector.py` | string list | Fully qualified symbol names |
| Overlapping Symbols | `semantic_conflict_detector.py` | symbol list | Which symbols conflict |

### Region Analysis
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Region Overlap | `risk_classifier.py` | boolean | Do the line ranges overlap? |
| Region Type | `risk_classifier.py` | "lines N-M" or "symbol_name" | How region is specified |
| Other Region | `activity_log.py` | string | The other developer's region |
| Region Scope | activity entry | "file" / "function" / "region" | Scope of the region |

### Intent Analysis
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Intent | `activity_log.py` | string | What developer intends to do |
| Other Intent | `risk_classifier.py` | string | What other developer is doing |
| Signature Change | `risk_classifier.py` | boolean | Is API being modified? |
| Signature Details | string | "rename" / "delete" / "remove" | Type of signature change |

### Conflicting Developer Info
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Developer ID | `activity_log.py` | string | Developer creating conflict |
| Other Developer | `risk_classifier.py` | string | Developer being conflicted with |
| Conflict Count | derived | integer | How many conflicts in this file |
| Multiple Conflicts | boolean | True if 2+ developers on same file |

---

## 2. LOCK MANAGEMENT METRICS

### Lock State
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Lock State | `activity_log.py` | ACQUIRED / WAITING / RELEASED | Current lock status |
| Lock Holder | `activity_log.py` | developer_id | Who has the lock |
| Lock Holder ID | `activity_log.py` | string | Developer ID holding lock |
| Lock Reason | `activity_log.py` | MEDIUM_CONFLICT / HIGH_CONFLICT | Why lock was acquired |
| Lock Scope | `activity_log.py` | "file" / "function" / "region" | What's being locked |

### Lock Timing
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Lock Acquired At | `activity_log.py` | unix timestamp | When lock was obtained |
| Lock Expires At | `activity_log.py` | unix timestamp | When lock expires |
| Lock Timeout Seconds | `activity_log.py` | integer (default 1800) | Lock duration in seconds |
| Time Until Expiry | derived | "Xm Ys" | How long lock valid |
| Lock Age | derived | "Xs ago" | How long lock held |

### Queue Management
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Queue Position | `activity_log.py` | 0, 1, 2, ... | Position in waiting queue (0=next) |
| Waiting For | `activity_log.py` | developer_id | Developer this one is blocked on |
| Queue Length | derived | integer | Total developers waiting |
| Is Waiting | derived | boolean | True if queue_position set |

---

## 3. CONTEXT STALENESS METRICS

### Freshness Status
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Freshness Status | `freshness.py` | CURRENT / STALE_SOURCE / UNVERIFIABLE | Is developer context up-to-date? |
| Is Stale | derived | boolean | True if STALE_SOURCE |
| Content Hash | `freshness.py` | hash string | SHA of file content |
| Baseline Hash | `freshness.py` | hash string | Previous snapshot hash |
| Hash Match | derived | boolean | True if content unchanged |

### Changed Symbols
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Changed Symbols | `freshness.py` | symbol list | Functions/classes that changed |
| Changed Count | derived | integer | Number of symbols changed |
| Symbols List | `freshness.py` | "Changed: func_name" | List of changed items |
| Symbol Signatures | `freshness.py` | string | Parameter/return type changes |
| Body Hashes | `freshness.py` | hash list | Hash of each symbol's body |

### Staleness Details
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Needs Refresh | derived | boolean | True if stale, false if current |
| Refresh Required | boolean | Action needed? |
| Delta Summary | `freshness.py` | string | Summary of changes since baseline |
| Delta Details | `freshness.py` | string list | Detailed change list |
| Staleness Reason | string | Why context is stale |

---

## 4. IMPACT ANALYSIS METRICS

### Impact Status
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Has Impacts | `impact_alerts.py` | boolean | Are there unresolved impacts? |
| Impact Count | `impact_alerts.py` | integer | Number of unresolved alerts |
| Alert Count | `impact_alerts.py` | integer | Count of impact alerts |
| Alert Status | `impact_alerts.py` | "resolved" / "unresolved" | Status of each alert |

### Upstream Impacts
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Upstream Impacts | `impact_alerts.py` | file list | Files that depend on this code |
| Upstream Count | derived | integer | Number of upstream impacts |
| Upstream Sources | `impact_alerts.py` | string list | Source files of impacts |
| Changed By | `impact_alerts.py` | developer_id | Who made upstream changes |

### Downstream Impacts
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Downstream Impacts | `cross_file_impact.py` | file list | What this code depends on |
| Downstream Count | derived | integer | Number of downstream deps |
| Consumed Symbols | `cross_file_impact.py` | symbol list | What downstream uses |
| Dependency Chain | `cross_file_impact.py` | path string | Full dependency path |

### Cross-Service Impacts
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Cross-Service | `cross_file_impact.py` | boolean | Impacts across services? |
| Service Coupling | `cross_file_impact.py` | LOW / MEDIUM / HIGH | Coupling strength |
| Service List | string list | Services affected |
| Blast Radius | `conflict_scorer.py` | 0-100 % | % of codebase affected |
| Blast Radius Estimate | string | "25% of codebase" | Human-readable impact |
| Impact Severity | derived | LOW / MEDIUM / HIGH | Overall severity |

### Impact Metadata
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Change Summary | `impact_alerts.py` | string | What was changed upstream |
| Impact Reason | `impact_alerts.py` | string | Why downstream is affected |
| PR Number | `impact_alerts.py` | integer | Associated PR if any |
| Created At | `impact_alerts.py` | timestamp | When impact was detected |
| Resolved At | `impact_alerts.py` | timestamp | When impact was resolved |
| Resolved By | `impact_alerts.py` | developer_id | Who resolved impact |

---

## 5. SEMANTIC ANALYSIS METRICS

### Symbol Extraction
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Symbol Count | `semantic_conflict_detector.py` | integer | Total functions/classes/methods |
| Symbols | `semantic_conflict_detector.py` | symbol list | All extracted symbols |
| Symbol Names | `semantic_conflict_detector.py` | string list | Just the names |
| Fully Qualified Names | `semantic_conflict_detector.py` | string list | Class.method notation |

### Symbol Details
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Symbol Type | `semantic_conflict_detector.py` | "function" / "class" / "method" / "async_function" | Type of symbol |
| Symbol Start Line | `semantic_conflict_detector.py` | integer | Where symbol starts |
| Symbol End Line | `semantic_conflict_detector.py` | integer | Where symbol ends |
| Parent Class | `semantic_conflict_detector.py` | string | Class if method |
| Is Async | `semantic_conflict_detector.py` | boolean | Is async function? |

### Dependencies
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Dependency Count | `semantic_conflict_detector.py` | integer | Total tracked dependencies |
| Dependencies | `semantic_conflict_detector.py` | dependency list | All dependencies |
| Dependency Types | `semantic_conflict_detector.py` | "imports" / "calls" / "inherits" / "uses" | Types of deps |
| Call Dependencies | `semantic_conflict_detector.py` | string list | Functions called |
| Import Dependencies | `semantic_conflict_detector.py` | string list | Modules imported |
| Inheritance | `semantic_conflict_detector.py` | string list | Parent classes |

### Dependency Analysis
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Transitive Dependencies | `semantic_conflict_detector.py` | dependency list | Indirect dependencies |
| Circular Dependencies | `semantic_conflict_detector.py` | boolean | Are there cycles? |
| Circular Deps List | dependency list | Which deps form cycles |
| Missing Dependencies | `semantic_conflict_detector.py` | string list | Called but not imported |
| Dependency Confidence | `semantic_conflict_detector.py` | 0.0-1.0 | Confidence in dependency |

---

## 6. ACTIVITY LOG METRICS

### Developer Information
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Developer ID | `activity_log.py` | string | Agent/developer identifier |
| Tenant ID | `activity_log.py` | string | Multitenancy tenant |
| Is Multitenancy | `activity_log.py` | boolean | Using tenant isolation? |

### File Information
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| File Path | `activity_log.py` | string | File being worked on |
| Same File | derived | boolean | Multiple devs on same file? |
| File Change Count | derived | integer | How many devs touched file |

### Intent Information
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Intent | `activity_log.py` | string | Human-readable intent |
| Intent Category | `activity_log.py` | "feature" / "bugfix" / "refactor" / "chore" | Type of work |
| Intent Scope | `activity_log.py` | "single-function" / "file" / "module" | Scope of change |
| Region | `activity_log.py` | string | Code region affected |
| Blocking Others | `activity_log.py` | boolean | Does this block teammates? |

### Completion Metrics
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Estimated Completion | `activity_log.py` | seconds | ETA for work |
| Time Remaining | derived | "XmYs remaining" | Human-readable ETA |
| Is Complete | derived | boolean | Is work done? |

### Temporal Data
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Timestamp | `activity_log.py` | unix timestamp | When entry logged |
| Entry Age | derived | "Xs ago" / "Xm ago" | How old is entry |
| Expiry Time | `activity_log.py` | 30 minutes default | When entry expires |
| Is Expired | derived | boolean | Has 30min passed? |
| Last Activity | derived | timestamp | When developer was last active |

---

## 7. AGENT METADATA METRICS

### Model Information
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Model | `activity_log.py` | string | LLM model used (e.g., claude-opus-5-5) |
| Model Version | string | version string | Specific model version |
| Is Fast Mode | boolean | True if fast mode enabled |

### Token Usage
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Tokens Used | `activity_log.py` | integer | Tokens consumed |
| Token Count | integer | Total tokens in request |
| Input Tokens | integer | Tokens in input |
| Output Tokens | integer | Tokens in output |
| Token Savings | derived | integer | Tokens saved by Neo |

### Execution Metrics
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Confidence | `activity_log.py` | 0.0-1.0 | Agent confidence in decision |
| Execution Time | `activity_log.py` | seconds | How long agent ran |
| Performance Score | derived | 0-100 | Overall performance rating |

---

## 8. PERFORMANCE & OPTIMIZATION METRICS

### Parsing & Analysis
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Parse Time | `semantic_conflict_detector.py` | milliseconds | AST parse duration |
| Analysis Time | `risk_classifier.py` | milliseconds | Conflict analysis time |
| Symbol Extract Time | `semantic_conflict_detector.py` | milliseconds | Symbol extraction time |

### Group-Commit Optimization
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Batch Size | `activity_log.py` | integer | Items in commit batch |
| Coalescing Rate | `activity_log.py` | percentage | % concurrent writes batched |
| Write Latency | `activity_log.py` | milliseconds | Time to write entry |
| Throughput | derived | entries/sec | Writes per second |

### Locking Overhead
| Metric | Source | Values | Description |
|--------|--------|--------|-------------|
| Lock Acquisition Time | milliseconds | Time to acquire lock |
| Queue Wait Time | `activity_log.py` | seconds | Time waiting for lock |
| Lock Contention | derived | integer | Number of waiters |

---

## 9. COMPLETE DATA STRUCTURE

### ActivityEntry Full Schema
```python
@dataclass
class ActivityEntry:
    # Identity
    developer_id: str
    tenant_id: str
    
    # Work Description
    file_path: str
    intent: str
    region: Optional[str]
    
    # Intent Metadata
    intent_category: Optional[str]  # feature/bugfix/refactor/chore
    intent_scope: Optional[str]     # single-function/file/module
    blocking_others: bool
    estimated_completion: Optional[int]
    
    # Timestamps
    timestamp: float                # When logged
    
    # Agent Metadata
    agent_metadata: Optional[Dict]  # model, tokens, confidence
    
    # Lock Fields
    lock_state: Optional[str]       # ACQUIRED/WAITING/RELEASED
    lock_holder: Optional[str]      # developer_id holding lock
    lock_acquired_at: Optional[float]
    lock_expires_at: Optional[float]
    lock_timeout_seconds: int
    lock_reason: Optional[str]      # MEDIUM_CONFLICT/HIGH_CONFLICT
    lock_scope: Optional[str]       # file/function/region
    
    # Queue Fields
    queue_position: Optional[int]   # 0=next
    waiting_for: Optional[str]      # developer_id blocking this
```

---

## 10. NEO MEASUREMENT COVERAGE

### What Neo Measures
✅ **Conflict Detection**
- Semantic symbol-level conflicts (not just line ranges)
- Risk classification (LOW/MEDIUM/HIGH)
- Conflicting developer identification
- Intent analysis and signature change detection

✅ **Context Staleness**
- File content freshness (CURRENT vs STALE_SOURCE)
- Symbol-level change tracking
- Baseline snapshot management
- Delta reporting (what changed)

✅ **Impact Analysis**
- Upstream impact detection (what depends on this)
- Downstream impact detection (what this depends on)
- Cross-service impact analysis
- Blast radius estimation (% of codebase affected)

✅ **Lock Management**
- Lock state tracking (ACQUIRED/WAITING/RELEASED)
- Queue position management
- Lock expiration timing
- Lock reason classification

✅ **Semantic Analysis**
- AST-based symbol extraction
- Function/class/method identification
- Dependency graph building
- Circular dependency detection

✅ **Agent Execution**
- Model identification and version tracking
- Token usage accounting
- Execution time measurement
- Confidence scoring

✅ **Performance**
- Parse and analysis timing
- Group-commit batch optimization
- Lock acquisition performance
- Throughput measurement

---

## How to Display All Metrics

### In Claude Terminal (test-complete-2dev.py)
The test shows checks being performed with status indicators:
```
✅ Checking for conflicts        [PASS      ] Pre-generation check
✅ Analyzing semantic symbols    [PASS      ] Found 4 functions in auth.py
⚠️  Risk classification         [MEDIUM    ] Signature change affects downstream
❌ Checking context staleness   [WARN      ] Code is STALE
```

### In Real-Time Monitor (monitor-complete-activity.py)
Shows all data points per developer:
```
👤 DEVELOPER: agent-dev-a
📄 FILE: src/auth.py
💭 INTENT: Rename authenticate_user...
🎯 REGION: authenticate_user (lines 2-6)

  ⚠️  CONFLICT DETECTION:
    • Conflicts with agent-dev-b
      Risk Level: MEDIUM 🟡
      Reason: Overlapping region detected

  🔒 LOCK STATUS:
    • State: ACQUIRED
    • Holder: agent-dev-a
    • Expires In: 30m 0s

  🔄 CONTEXT STALENESS:
    • Status: CURRENT
    ...
```

---

## Running the Complete Test

```bash
# Terminal 1: Run test (shows diagnostic output)
python3 test-complete-2dev.py

# Terminal 2: Monitor all activities (shows all metrics)
python3 monitor-complete-activity.py --duration 120

# View activity log directly
cat .devsync/activity-log.json | python3 -m json.tool
```

---

## Summary: 100+ Data Points Tracked

Neo tracks **100+ distinct data points** across:
- **10 categories** (conflict, lock, staleness, impact, semantic, agent, performance, temporal, intent, multitenancy)
- **4 primary activities** (conflict detection, impact analysis, lock management, context staleness)
- **Complete semantic analysis** (symbol extraction, dependency tracking, AST parsing)
- **Rich metadata** (timestamps, confidence scores, agent execution info)
- **Performance metrics** (execution time, batch size, token usage)

All metrics are available for display in Claude terminals, activity monitors, dashboards, and IDE integrations.
