# Enhanced Activity Log - Extended Value System

## Overview

The current activity log is minimal but effective. This document outlines significant value-adds that transform it from a simple conflict detector into a rich collaboration and learning platform.

---

## 🎯 Current Capabilities vs. Enhanced

### Current (MVP)
```json
{
  "developer_id": "DevA",
  "file_path": "src/auth.py",
  "intent": "Refactor login function",
  "region": "login_user (lines 20-40)",
  "timestamp": 1694358400.123
}
```

**Limitations:**
- No understanding of what's actually changing
- No risk scoring
- No coordination suggestions
- No learning from patterns
- No agent-specific context

### Enhanced (Production)
```json
{
  "developer_id": "DevA",
  "file_path": "src/auth.py",
  "timestamp": 1694358400.123,
  
  "intent": {
    "description": "Refactor login function",
    "category": "refactor",              // feature, bugfix, refactor, chore
    "scope": "single-function",           // single-function, multi-function, file, module
    "risk_level": "medium",               // low, medium, high
    "dependencies": ["session.py", "db.py"],
    "exported_symbols": ["authenticate_user"]
  },
  
  "region": {
    "start_line": 20,
    "end_line": 40,
    "functions": ["login_user"],
    "classes": [],
    "signature_changes": true
  },
  
  "context": {
    "branch": "feature/auth-refactor",
    "staged_changes": "45 insertions, 12 deletions",
    "file_size_before": "234KB",
    "file_size_after": "240KB",
    "complexity_score": 0.68
  },
  
  "agent_metadata": {
    "agent_id": "claude-agent-1",
    "model": "claude-opus-5",
    "prompt_tokens_used": 2048,
    "generation_status": "in-progress"
  },
  
  "collaboration": {
    "is_blocking": false,
    "estimated_completion": 1694359200,
    "communication_sent": ["email_to_DevB"],
    "coordination_needed": true
  },
  
  "patterns": {
    "author_touch_frequency": 0.8,      // How often author touches this file
    "conflict_history": 2,              // Times conflicted with others
    "avg_session_duration": 1800,       // seconds
    "time_of_day": "morning"            // When typically works
  }
}
```

---

## 📊 Valuable Additions

### 1. Intent Classification & Scoring

**What to track:**
```python
intent = {
    "description": str,
    "category": enum("feature", "bugfix", "refactor", "chore", "docs"),
    "scope": enum("single-function", "multi-function", "file", "module", "cross-file"),
    "risk_level": "auto-calculated",
    "breaking_changes": bool,
    "dependencies": list[str],
    "exported_symbols": list[str],
}
```

**Value:**
- Agents understand the nature of changes
- Better conflict classification ("refactor" vs "bugfix" have different rules)
- Risk scoring based on category
- Dependency tracking prevents cascading issues

**Implementation:**
```python
def classify_intent(description: str) -> IntentClassification:
    # Use keywords + heuristics or light LLM call
    keywords = {
        'refactor': ['refactor', 'reorganize', 'clean up'],
        'bugfix': ['fix', 'bug', 'issue', 'error'],
        'feature': ['add', 'implement', 'new'],
        'chore': ['update', 'upgrade', 'bump'],
    }
    # Returns category, risk level, etc.
```

### 2. Staged Changes Metadata

**What to track:**
```python
changes = {
    "staged_diff": str,              # Actual diff content
    "insertions": int,
    "deletions": int,
    "files_modified": list[str],
    "functions_added": list[str],
    "functions_modified": list[str],
    "functions_removed": list[str],
    "signature_changes": dict,       # Old → New signatures
    "imports_added": list[str],
    "imports_removed": list[str],
}
```

**Value:**
- Agents see actual changes being made
- Precise conflict detection (line-level accuracy)
- Understand API changes
- Track dependencies properly

**Integration:**
```python
def extract_staged_changes(file_path: str) -> ChangesMetadata:
    # Use git diff --staged
    # Parse AST for function/class definitions
    # Return structured metadata
    pass
```

### 3. File Complexity Scoring

**What to track:**
```python
complexity = {
    "cyclomatic_complexity": float,
    "cognitive_complexity": float,
    "size_before": int,
    "size_after": int,
    "change_intensity": float,      # % of file changed
    "churn_history": float,         # How often file changes
}
```

**Value:**
- High-risk files flagged automatically
- Agents understand change magnitude
- Better risk prediction

### 4. Developer Patterns & Learning

**What to track:**
```python
patterns = {
    "touch_frequency": float,        # How often touches this file
    "avg_session_duration": int,     # seconds
    "avg_conflict_rate": float,      # % of sessions with conflicts
    "conflict_history": list[dict],  # Past conflicts with others
    "timezone": str,
    "typical_hours": list[int],      # Hours when usually working
    "expertise_level": enum("junior", "mid", "senior"),
    "recovery_time": int,            # How long to resolve conflicts
}
```

**Value:**
- Machine learning for conflict prediction
- Smarter timing of warnings
- Personalized recommendations
- Learning from patterns

### 5. Blocking Status & Coordination

**What to track:**
```python
coordination = {
    "is_blocking_others": bool,
    "blocked_by": list[str],         # Other developer IDs
    "estimated_completion": timestamp,
    "communication_sent": list[str], # email, slack, etc.
    "coordination_needed": bool,
    "suggested_actions": list[str],  # ["wait", "coordinate", "merge-first"]
}
```

**Value:**
- Agents know if work is blocking
- Automatic coordination suggestions
- Better planning

### 6. Agent-Specific Metadata

**What to track:**
```python
agent = {
    "agent_id": str,
    "model": str,
    "temperature": float,
    "max_tokens": int,
    "prompt_tokens_used": int,
    "completion_tokens_used": int,
    "generation_status": enum("queued", "in-progress", "completed", "failed"),
    "confidence_score": float,       # Agent's own confidence in changes
    "rollback_suggested": bool,
}
```

**Value:**
- Agents track their own generation quality
- Can alert if confidence is low
- Enables better agent coordination

### 7. Dependency Graph

**What to track:**
```python
dependencies = {
    "imports_this_file": list[str],       # Files this imports
    "imported_by": list[str],             # Files that import this
    "direct_dependencies": list[str],
    "transitive_dependencies": list[str],
    "exported_symbols": dict[str, list],  # symbol → files using it
    "called_by": list[dict],              # Who calls our functions
}
```

**Value:**
- Detect transitive conflicts (A changes X, B uses X)
- Smarter risk classification
- Understand impact radius
- Prevent silent breakage

---

## 🔌 Agent Integration Points

### 1. Pre-Generation Hook

**What agents do:**
```python
# Before generating code:
from activity_log import check_conflicts_enhanced

conflict_report = check_conflicts_enhanced(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    intent="Add email validation",
    region="User.validate_email",
    model="claude-opus-5"
)

if conflict_report.risk_level == "HIGH":
    # Agent can decide to:
    # - Wait for the other developer
    # - Coordinate with them
    # - Proceed with caution (log it)
    handle_conflict(conflict_report)

# Otherwise, proceed with generation
generate_code()

# Log the generation
log_activity_enhanced(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    intent="...",
    agent_metadata={
        "status": "in-progress",
        "tokens_used": 2048,
        "confidence": 0.92,
    }
)
```

### 2. Conflict Report Structure (For Agents)

```python
@dataclass
class ConflictReport:
    """What agents receive before generating"""
    
    risk_level: RiskLevel  # LOW, MEDIUM, HIGH
    reason: str
    
    # Who's conflicting
    other_developer: str
    other_agent: Optional[str]
    other_intent: str
    
    # Specific conflict details
    overlapping_regions: list[str]
    dependency_conflicts: list[str]
    signature_changes: list[dict]
    
    # What the agent should do
    recommended_action: str  # "proceed", "wait", "coordinate"
    estimated_wait_time: Optional[int]  # seconds
    
    # Agent-specific guidance
    agent_guidance: dict  # Model-specific recommendations
    
    # Historical context
    similar_past_conflicts: list[dict]
    success_rate_for_similar: float
```

### 3. Agent Notification Channels

```python
def notify_agent_of_conflict(
    agent_id: str,
    conflict_report: ConflictReport,
):
    """Notify incoming agents of conflicts"""
    
    # Multiple notification methods:
    
    # Method 1: Prompt Injection (best for immediate attention)
    injected_prompt = f"""
    ⚠️ CONFLICT WARNING: {conflict_report.reason}
    
    Another developer is editing the same file:
    - Developer: {conflict_report.other_developer}
    - Intent: {conflict_report.other_intent}
    - Region: {conflict_report.overlapping_regions}
    - Risk Level: {conflict_report.risk_level}
    
    Recommended Action: {conflict_report.recommended_action}
    
    Proceed? (You can override with explicit confirmation in your next message)
    """
    return injected_prompt
    
    # Method 2: API Response (polling)
    return {
        "has_conflicts": True,
        "conflict_report": conflict_report,
    }
    
    # Method 3: Webhook Notification (reactive)
    webhook_payload = {
        "event": "conflict_detected",
        "timestamp": time.time(),
        "conflict_report": conflict_report,
        "callback_url": "..."  # Agent can acknowledge
    }
    trigger_webhook(agent_id, webhook_payload)
    
    # Method 4: Structured Context (for Claude's system prompt)
    return {
        "type": "collaboration_context",
        "active_conflicts": [conflict_report],
        "coordination_status": "active",
    }
```

---

## 🚀 New Capabilities Enabled

### 1. Smart Conflict Prediction
```python
def predict_conflicts(planned_changes: dict) -> float:
    """ML model predicts conflict likelihood"""
    # Uses:
    # - File change history
    # - Developer patterns
    # - Time of day
    # - Complexity scoring
    # Returns: 0-1 confidence of conflict
    pass
```

### 2. Automatic Coordination
```python
def suggest_coordination(developer_a: str, developer_b: str) -> str:
    """Suggest how developers should coordinate"""
    # Returns: "merge-first", "wait", "parallel-safe", "coordinate"
    # Based on:
    # - Dependency analysis
    # - File modification patterns
    # - Past collaboration success
    pass
```

### 3. Conflict Prevention
```python
def check_merge_safety(branch: str, base: str) -> MergeSafetyReport:
    """Check if merge is safe before committing"""
    # Analyzes:
    # - Staged changes
    # - In-flight work in activity log
    # - Dependency graph
    # - Recent conflicts
    pass
```

### 4. Agent Learning
```python
def log_agent_outcome(
    agent_id: str,
    file_path: str,
    conflict_handled: bool,
    outcome: str,  # "success", "failed", "reverted"
    metadata: dict
):
    """Track how agents handle conflicts"""
    # Used for:
    # - Training better models
    # - Improving recommendations
    # - Measuring agent reliability
    pass
```

### 5. Impact Analysis
```python
def analyze_impact(changes: dict) -> ImpactReport:
    """Analyze what a change affects"""
    # Returns:
    # - Files affected
    # - Functions affected
    # - Tests that might break
    # - Downstream dependencies
    # - Estimated risk
    pass
```

---

## 📈 Data Schema Enhancement

### Extended Activity Log Entry

```json
{
  "_id": "activity_20260911_devA_auth",
  "timestamp": 1694358400.123,
  "expires_at": 1694364600,  // 30 min expiry
  
  "developer": {
    "id": "DevA",
    "agent_id": "claude-opus-1",
    "model": "claude-opus-5"
  },
  
  "work": {
    "file_path": "src/auth.py",
    "intent": {
      "description": "Refactor login function for better error handling",
      "category": "refactor",
      "scope": "single-function",
      "risk_assessment": {
        "level": "medium",
        "reasons": ["signature_change", "shared_dependency"],
        "score": 0.68
      }
    },
    
    "region": {
      "start_line": 20,
      "end_line": 40,
      "functions": ["login_user"],
      "changed_signatures": {
        "login_user": {
          "old": "(username: str, password: str) -> User",
          "new": "(username: str, password: str, timeout: int = 300) -> User"
        }
      }
    }
  },
  
  "changes": {
    "staged_diff": "...",
    "stats": {
      "insertions": 45,
      "deletions": 12,
      "complexity_delta": 0.05
    },
    "dependencies_affected": ["session.py", "db.py", "models.py"],
    "exported_changes": ["authenticate_user"]
  },
  
  "status": {
    "activity_stage": "in-progress",
    "estimated_completion": 1694359200,
    "blocking_others": false,
    "coordination_needed": true
  },
  
  "agent_metadata": {
    "generation_status": "in-progress",
    "tokens_used": 2048,
    "confidence": 0.92,
    "prompt_hash": "abc123..."
  },
  
  "patterns": {
    "session_duration_so_far": 1200,
    "author_frequency_this_file": 0.8,
    "time_cluster": "morning",
    "expertise_level": "senior"
  },
  
  "notifications": {
    "conflicts_detected": [
      {
        "conflicting_developer": "DevB",
        "conflicting_region": "lines 25-35",
        "risk": "MEDIUM",
        "notification_sent": true,
        "notification_method": "prompt_injection"
      }
    ]
  }
}
```

---

## 🔄 Integration Flow

```
┌─────────────────────────────────────────────────────┐
│ Developer/Agent Starts Work                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 1. Log Activity (Enhanced)                          │
│    - Classify intent                                │
│    - Extract staged changes                         │
│    - Calculate complexity                           │
│    - Store in activity log                          │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 2. Before Generation (Pre-hook)                     │
│    - Check for conflicts                            │
│    - Analyze dependencies                           │
│    - Generate conflict report                       │
│    - Inject guidance into prompt                    │
└────────────────┬────────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
         ▼                ▼
   ┌─────────────┐  ┌──────────────┐
   │ No Conflict │  │ Conflict     │
   │ → Generate  │  │ → Notify     │
   └──────┬──────┘  │ → Await ACK  │
          │         │ → Coordinate │
          │         └──────┬───────┘
          │                │
          └────────┬───────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ 3. During Generation (Activity Log Update)          │
│    - Track tokens used                              │
│    - Update status to "in-progress"                 │
│    - Monitor for new conflicts                      │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 4. After Generation (Post-hook)                     │
│    - Log outcome (success/failed)                   │
│    - Update activity status to "completed"          │
│    - Record metrics (tokens, confidence)            │
│    - Trigger follow-up checks                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 5. Learning & Analysis                              │
│    - Record conflict outcomes                       │
│    - Update developer patterns                      │
│    - Refine risk models                             │
│    - Suggest future optimizations                   │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Priority

### Phase 1 (MVP) - Current
- ✅ Basic activity logging
- ✅ Risk classification
- ✅ Pre-generation check

### Phase 2 (High Value)
- Intent classification
- Staged changes extraction
- Dependency tracking
- Conflict reporting for agents

### Phase 3 (Advanced)
- Developer pattern learning
- ML-based conflict prediction
- Automatic coordination
- Agent metadata tracking

### Phase 4 (Intelligence)
- Transitive dependency analysis
- Smart merge conflict resolution
- Agent learning & adaptation
- Predictive recommendations

---

## 💡 Use Cases Enabled

### Use Case 1: Agent Coordination
```
Agent A starts generating in file X
Activity log updated with intent + metadata

Agent B arrives to work on same file
Pre-check detects Agent A's work
Agent B receives structured conflict report:
  - What Agent A is changing
  - Why (intent)
  - Risk assessment
  - Suggested action (wait/coordinate/proceed)

Agent B decides based on guidance
Either waits, coordinates, or proceeds
Outcome is logged for learning
```

### Use Case 2: Conflict Prevention
```
Developer schedules automated generation
System checks activity log for in-flight changes
If conflicts likely (>80% confidence):
  - Delays generation
  - Notifies developer
  - Suggests timing

If safe:
  - Proceeds immediately
  - Logs preventive check result
```

### Use Case 3: Smart Merge
```
Before merging PR:
- Check activity log for active work
- Analyze dependency graph
- Simulate merge impact
- Predict conflicts
- Suggest resolution strategy

If high risk:
- Require manual review
- Suggest coordination first
If safe:
- Auto-merge approved
```

### Use Case 4: Agent Learning
```
Each time agent handles conflict:
- Log the situation
- Log the decision
- Log the outcome
- Track success rate

Over time:
- Better conflict predictions
- Better recommendations
- Agent adaptation
```

---

## 🔐 Data Privacy & Safety

### Stored Information
- Development intent (no sensitive data)
- File paths (no credentials)
- Change metadata (no actual secrets)
- Timestamps (no personal data)

### Access Control
```python
# Only authorized agents can read:
agent.can_read_activity_log = verified_agent_id

# Only current developer can modify:
activity.can_modify = activity.developer_id

# System can aggregate (anonymized):
stats = aggregate_anonymous_patterns()
```

---

This enhanced system transforms the activity log from a simple conflict detector into a comprehensive collaboration, learning, and intelligence platform for coordinated agent development.
