# Agent Integration Guide

Complete guide for integrating Claude, Devin, and other AI agents with the conflict warning system.

**Last Updated:** 2026-09-11  
**Status:** ✅ Ready for Integration

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Agent Integration Points](#agent-integration-points)
4. [Pre-Generation Hook](#pre-generation-hook)
5. [Prompt Injection](#prompt-injection)
6. [Intent Classification](#intent-classification)
7. [Conflict Reporting](#conflict-reporting)
8. [Real-World Examples](#real-world-examples)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)

---

## Quick Start

### For Agents (Claude/Devin)

Before generating code, check for conflicts and get guidance:

```python
from agent_integration import check_conflicts_for_agent, format_conflict_guidance_for_prompt

# Pre-generation check
report = check_conflicts_for_agent(
    agent_id="claude-opus-1",
    file_path="src/payment.py",
    intent="Add retry logic to payment processing",
    region="process_payment (lines 50-100)",
    model="claude-opus-5"
)

# Add guidance to prompt
if report.has_conflicts:
    prompt_context = format_conflict_guidance_for_prompt(report)
    # Inject into system prompt or generation context
    full_prompt = f"{system_prompt}\n\n{prompt_context}\n\n{user_prompt}"
```

### For Developers

Just like before, but now agents are aware of your work:

```python
from activity_log import log_activity

# Log your intent
log_activity(
    developer_id="alice@company.com",
    file_path="src/auth.py",
    intent="Refactor login to use OAuth2",
    region="login_user (lines 45-80)",
    intent_category="refactor",
    intent_scope="single-function",
    blocking_others=False
)
```

---

## Core Concepts

### Three-Layer Conflict Detection

```
Layer 1: Region Overlap
├─ Same file + overlapping code regions
├─ Simple line-based heuristic
└─ Risk: LOW → MEDIUM

Layer 2: Signature Changes
├─ Detects API/interface modifications
├─ Keywords: rename, remove, delete, change signature
└─ Risk: MEDIUM → HIGH

Layer 3: Intent Classification
├─ Analyzes change category and scope
├─ Feature/bugfix/refactor/chore/test/docs
└─ Enables ML-based prediction (future)
```

### Risk Levels

```
LOW (Green)     → Silent, auto-proceed
├─ Different files
├─ Non-overlapping regions
└─ Minor changes (docs, tests, chore)

MEDIUM (Orange) → Warn, non-blocking
├─ Overlapping regions
├─ Same file, different functions
└─ Low-risk modifications

HIGH (Red)      → Block, requires confirmation
├─ Signature changes
├─ API modifications
└─ Potential breaking changes
```

### Recommended Actions

```
proceed_silently       → No risk, no prompt needed
warn_and_proceed       → Mention conflict but allow generation
request_confirmation   → Show conflict details, ask user
wait_for_resolution    → Block generation, suggest waiting
coordinate_with_dev    → Suggest direct coordination
```

---

## Agent Integration Points

### 1. Pre-Generation Hook

**When:** Called before agent starts generating code  
**Who:** Claude Code runtime, Cursor agent, Devin workflow  
**Input:** Agent ID, file, intent, region  
**Output:** Conflict report with recommendation

```python
from agent_integration import check_conflicts_for_agent

report = check_conflicts_for_agent(
    agent_id="agent-session-123",
    file_path="src/utils.py",
    intent="Add logging to utility functions",
    region="utils module",
    model="claude-opus-5"
)

if not report.has_conflicts:
    # Generate code
    generate_code(...)
elif report.recommended_action == "warn_and_proceed":
    # Show warning but proceed
    print(report.agent_guidance)
    generate_code(...)
else:
    # Wait or coordinate
    wait_for_resolution(report.estimated_wait_time)
```

### 2. Prompt Injection

**What:** Add conflict context to agent's system prompt  
**When:** Before generation, if conflicts detected  
**Format:** Structured markdown with developer info

```python
prompt_context = format_conflict_guidance_for_prompt(report)

# Inject into prompt
system_prompt = f"""
You are Claude, an AI assistant helping with code generation.

{prompt_context}

Now proceed with the user's request...
"""
```

Example injected context:

```markdown
## ⚠️ Pre-Generation Conflict Check (MEDIUM Risk)

**Status:** Conflicts with 1 developer(s)  
**Recommendation:** Warn And Proceed

### Conflicting Developers:
- **alice@company.com** (2m ago): Refactor payment processing logic
  Region: `process_payment (lines 50-100)`

### Overlapping Regions:
- process_payment (lines 50-100)

**Agent Guidance:** MEDIUM risk: alice@company.com detected in 
overlapping region. Proceed with caution and consider coordinating changes.

**Confidence:** 85%
```

### 3. Post-Generation Logging

**When:** After code generation completes  
**Input:** Status, tokens used, outcome  
**Tracking:** For learning and metrics

```python
from agent_integration import log_agent_generation_outcome

log_agent_generation_outcome(
    agent_id="claude-opus-1",
    file_path="src/payment.py",
    status="success",
    tokens_used=1250,
    conflict_report=report,
    success=True
)
```

---

## Pre-Generation Hook

### Complete Flow

```python
# 1. Check for conflicts
report = check_conflicts_for_agent(
    agent_id="claude-1",
    file_path="src/auth.py",
    intent="Add type hints",
    region="auth module",
    model="claude-opus-5"
)

# 2. Decide based on risk
if report.risk_level == "LOW":
    action = "proceed_silently"
elif report.risk_level == "MEDIUM":
    action = "warn_and_proceed"
else:  # HIGH
    action = "wait_for_resolution"

# 3. Handle action
if action == "proceed_silently":
    generate_code(file_path, intent)
    
elif action == "warn_and_proceed":
    guidance = format_conflict_guidance_for_prompt(report)
    prompt_with_guidance = inject_guidance(prompt, guidance)
    generate_code_with_prompt(file_path, prompt_with_guidance)
    
elif action == "wait_for_resolution":
    wait_time = report.estimated_wait_time or 300
    print(f"Waiting ~{wait_time}s for conflict resolution...")
    time.sleep(wait_time)
    retry_generation(file_path, intent)
```

### In Claude Code

Pseudocode for Claude Code integration:

```python
# claude-code/generation.py

def generate_code_for_file(file_path: str, intent: str) -> str:
    # Pre-generation check
    report = check_conflicts_for_agent(
        agent_id=get_session_id(),
        file_path=file_path,
        intent=intent,
        region=detect_region(file_path),
        model=get_model_name()
    )
    
    # Inject conflict guidance into system prompt
    if report.has_conflicts:
        guidance = format_conflict_guidance_for_prompt(report)
        system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{guidance}"
    else:
        system_prompt = BASE_SYSTEM_PROMPT
    
    # Generate code with conflict awareness
    code = llm.generate(
        system=system_prompt,
        user=f"Generate code for: {intent}\nFile: {file_path}"
    )
    
    # Log outcome
    log_agent_generation_outcome(
        agent_id=get_session_id(),
        file_path=file_path,
        status="success",
        tokens_used=llm.tokens_used,
        conflict_report=report if report.has_conflicts else None,
        success=True
    )
    
    return code
```

---

## Prompt Injection

### Format Specification

The `format_conflict_guidance_for_prompt()` function returns markdown:

```
## ⚠️ Pre-Generation Conflict Check ({risk_level} Risk)

**Status:** {reason}
**Recommendation:** {recommended_action}

### Conflicting Developers:
- **{developer_id}** ({time_ago}): {intent}
  Region: `{region}`

### Overlapping Regions:
- {region1}
- {region2}

### Detected Signature Changes:
- {change1}
- {change2}

**Agent Guidance:** {agent_guidance}

**Estimated Wait Time:** ~{estimated_wait_time} minutes
**Confidence:** {confidence_score}%
```

### How to Use

**Option 1: System Prompt Injection**
```python
system_prompt = f"""
You are Claude, helping with code generation.

{conflict_context}

Follow the guidance provided above before generating.
"""
```

**Option 2: User Prompt Prefix**
```python
user_prompt = f"""
{conflict_context}

Now, generate code for: {user_request}
"""
```

**Option 3: Chain-of-Thought**
```python
prompt = f"""
Analyze this conflict context:

{conflict_context}

Based on this:
1. What are the risks?
2. How should you proceed?
3. What precautions should you take?

Then generate the requested code.
"""
```

---

## Intent Classification

### Automatic Classification

The `classify_intent()` function analyzes change descriptions:

```python
from intent_classifier import classify_intent, estimate_risk_from_intent

# Analyze intent
intent = "Add type hints to login function"
classified = classify_intent(intent)

print(f"Category: {classified.category.value}")    # "feature"
print(f"Scope: {classified.scope.value}")          # "single-function"
print(f"Risk: {estimate_risk_from_intent(classified)}")  # "LOW"
print(f"Confidence: {classified.confidence:.0%}")  # 65%
```

### Supported Categories

```python
class ChangeCategory(Enum):
    FEATURE = "feature"       # New functionality
    BUGFIX = "bugfix"         # Fixing issues
    REFACTOR = "refactor"     # Code cleanup
    CHORE = "chore"           # Maintenance
    TEST = "test"             # Test-related
    DOCS = "docs"             # Documentation
```

### Supported Scopes

```python
class ChangeScope(Enum):
    SINGLE_FUNCTION = "single-function"
    MULTI_FUNCTION = "multi-function"
    FILE = "file"
    MODULE = "module"
    UNKNOWN = "unknown"
```

### Classification Examples

```
Input: "Add type hints to login_user function"
→ Category: FEATURE, Scope: SINGLE_FUNCTION, Risk: LOW

Input: "Fix critical authentication bug"
→ Category: BUGFIX, Scope: UNKNOWN, Risk: MEDIUM

Input: "Refactor entire database layer"
→ Category: REFACTOR, Scope: MODULE, Risk: MEDIUM

Input: "Add unit tests for payment module"
→ Category: TEST, Scope: MODULE, Risk: LOW
```

### Risk Estimation

Risk is estimated based on:

```
category_risk × scope_multiplier × confidence_factor

Examples:
- Feature + single-function + high-confidence = LOW
- Bugfix + module + high-confidence = MEDIUM
- Refactor + multi-function + low-confidence = MEDIUM
- Chore + file + medium-confidence = LOW
```

---

## Conflict Reporting

### EnhancedConflictReport Structure

```python
@dataclass
class EnhancedConflictReport:
    risk_level: str                              # LOW/MEDIUM/HIGH
    reason: str                                  # Human-readable reason
    has_conflicts: bool                          # Any conflicts?
    conflicting_developers: List[ConflictingDeveloper]
    overlapping_regions: List[str]               # Conflicting regions
    dependency_conflicts: List[str]              # Future: cross-file deps
    signature_changes: List[str]                 # Detected API changes
    recommended_action: str                      # Action to take
    estimated_wait_time: Optional[int]           # Seconds to wait
    agent_guidance: str                          # What the agent should do
    confidence_score: float                      # 0.0-1.0
```

### ConflictingDeveloper Structure

```python
@dataclass
class ConflictingDeveloper:
    developer_id: str       # Human or agent ID
    file_path: str          # File they're working on
    intent: str             # What they're doing
    region: str             # Code region
    timestamp: float        # When they started
    time_ago: str           # "2m ago", "30s ago"
    risk_level: str         # LOW/MEDIUM/HIGH
```

### Reading Conflict Report

```python
report = check_conflicts_for_agent(...)

# Check if there are conflicts
if report.has_conflicts:
    print(f"Risk Level: {report.risk_level}")
    
    # See who's conflicting
    for dev in report.conflicting_developers:
        print(f"  {dev.developer_id}: {dev.intent} ({dev.time_ago})")
    
    # Get guidance
    print(f"Action: {report.recommended_action}")
    print(f"Guidance: {report.agent_guidance}")
    
    # Decide whether to wait
    if report.estimated_wait_time:
        print(f"Estimated wait: {report.estimated_wait_time}s")
else:
    print("✓ Safe to proceed")
```

---

## Real-World Examples

### Example 1: Agent Before Code Generation

```python
# Claude Code pre-generation hook
def claude_code_pre_generation():
    """Called before Claude generates code."""
    from agent_integration import check_conflicts_for_agent, format_conflict_guidance_for_prompt, should_proceed_with_generation
    
    # Get context
    file_path = get_selected_file()
    intent = get_user_prompt()
    
    # Check for conflicts
    report = check_conflicts_for_agent(
        agent_id=f"claude-{get_session_id()}",
        file_path=file_path,
        intent=intent,
        region=estimate_affected_region(file_path, intent),
        model="claude-opus-5"
    )
    
    # Show warning if needed
    if report.has_conflicts and report.risk_level == "MEDIUM":
        show_warning(format_conflict_guidance_for_prompt(report))
    
    # Block if HIGH risk
    if not should_proceed_with_generation(report):
        show_error(f"HIGH risk conflict. {report.agent_guidance}")
        return False
    
    return True
```

### Example 2: Devin Agent Coordination

```python
# Devin workflow integration
async def devin_generate_with_coordination(task: str):
    """Devin generates code while aware of conflicts."""
    from agent_integration import check_conflicts_for_agent
    
    # Devin checks for conflicts before each generation
    for file_path in get_files_to_modify(task):
        report = check_conflicts_for_agent(
            agent_id="devin-agent-1",
            file_path=file_path,
            intent=task,
            region=extract_region(file_path, task)
        )
        
        if report.risk_level == "HIGH":
            # High risk - coordinate with humans
            send_notification(
                f"Devin needs coordination: {report.agent_guidance}",
                to=get_team_lead()
            )
            await wait_for_approval()
        
        # Generate with awareness
        code = await devin.generate(
            file_path=file_path,
            context=format_conflict_guidance_for_prompt(report)
        )
```

### Example 3: Multi-Agent Coordination

```python
# Multiple agents coordinating on the same codebase
async def multi_agent_workflow():
    """Agents coordinate through shared activity log."""
    from activity_log import log_activity, get_active_entries
    from agent_integration import check_conflicts_for_agent
    
    # Agent 1: Adding authentication
    log_activity(
        "agent-auth",
        "src/auth.py",
        "Add OAuth2 integration",
        "auth module"
    )
    
    # Agent 2: Checks before modifying auth-related code
    report = check_conflicts_for_agent(
        "agent-api",
        "src/auth.py",
        "Refactor auth API endpoints",
        "endpoints (lines 100-200)"
    )
    
    # Agent 2 waits if Agent 1 is still working
    if report.has_conflicts:
        print(f"Waiting for Agent 1... {report.estimated_wait_time}s")
        await asyncio.sleep(report.estimated_wait_time)
    
    # Now safe to proceed
    await agent_api.generate()
```

---

## API Reference

### `check_conflicts_for_agent()`

```python
def check_conflicts_for_agent(
    agent_id: str,
    file_path: str,
    intent: str,
    region: str,
    model: Optional[str] = None
) -> EnhancedConflictReport:
    """
    Pre-generation conflict check for agents.
    
    Args:
        agent_id: Unique agent identifier
        file_path: File to check
        intent: What agent wants to do
        region: Affected code region
        model: Model name (optional)
    
    Returns:
        EnhancedConflictReport with risk assessment
    
    Example:
        report = check_conflicts_for_agent(
            "claude-1",
            "src/auth.py",
            "Add type hints",
            "auth module"
        )
    """
```

### `format_conflict_guidance_for_prompt()`

```python
def format_conflict_guidance_for_prompt(
    report: EnhancedConflictReport
) -> str:
    """
    Format conflict report as prompt injection.
    
    Args:
        report: The conflict report from check_conflicts_for_agent()
    
    Returns:
        Markdown-formatted guidance to inject into prompt
    
    Example:
        context = format_conflict_guidance_for_prompt(report)
        prompt = f"System: {context}\n\nUser: {user_request}"
    """
```

### `should_proceed_with_generation()`

```python
def should_proceed_with_generation(
    report: EnhancedConflictReport
) -> bool:
    """
    Determine if agent should proceed based on risk.
    
    Returns:
        True if should generate, False if should wait
    
    Example:
        if should_proceed_with_generation(report):
            generate_code()
        else:
            wait_for_resolution()
    """
```

### `classify_intent()`

```python
def classify_intent(
    description: str
) -> ClassifiedIntent:
    """
    Classify change intent automatically.
    
    Args:
        description: Developer or agent intent description
    
    Returns:
        ClassifiedIntent with category, scope, keywords, confidence
    
    Example:
        classified = classify_intent("Add type hints to login")
        print(classified.category)  # ChangeCategory.FEATURE
        print(classified.scope)     # ChangeScope.SINGLE_FUNCTION
    """
```

### `log_agent_generation_outcome()`

```python
def log_agent_generation_outcome(
    agent_id: str,
    file_path: str,
    status: str,
    tokens_used: int,
    conflict_report: Optional[EnhancedConflictReport] = None,
    success: bool = True
) -> None:
    """
    Log the outcome of agent generation.
    
    Args:
        agent_id: Agent identifier
        file_path: File that was generated
        status: Generation status (success/failed/cancelled)
        tokens_used: Tokens consumed
        conflict_report: Original conflict report (if any)
        success: Whether generation succeeded
    
    Example:
        log_agent_generation_outcome(
            "claude-1",
            "src/auth.py",
            "success",
            1250,
            report,
            success=True
        )
    """
```

---

## Best Practices

### 1. Always Check Before Generating

```python
# ❌ Bad: Generate without checking
generated_code = agent.generate(file_path, intent)

# ✅ Good: Check first
report = check_conflicts_for_agent(agent_id, file_path, intent, region)
if should_proceed_with_generation(report):
    generated_code = agent.generate(file_path, intent)
```

### 2. Inject Conflict Context into Prompts

```python
# ❌ Bad: No conflict awareness
prompt = f"Generate code for: {intent}"

# ✅ Good: Inject conflict context
if report.has_conflicts:
    guidance = format_conflict_guidance_for_prompt(report)
    prompt = f"{guidance}\n\nGenerate code for: {intent}"
else:
    prompt = f"Generate code for: {intent}"
```

### 3. Classify Intents for Better Prediction

```python
# ❌ Bad: Generic intent
log_activity("alice", "src/auth.py", "Fix stuff", "auth.py")

# ✅ Good: Classified intent
from intent_classifier import classify_intent
classified = classify_intent("Fix authentication timeout issue")
log_activity(
    "alice",
    "src/auth.py",
    "Fix authentication timeout issue",
    "auth module",
    intent_category=classified.category.value,
    intent_scope=classified.scope.value
)
```

### 4. Respect Wait Times

```python
# ❌ Bad: Ignore wait recommendation
if report.estimated_wait_time:
    pass  # Ignore and proceed anyway

# ✅ Good: Respect wait time
if report.estimated_wait_time:
    print(f"Waiting {report.estimated_wait_time}s for resolution...")
    time.sleep(report.estimated_wait_time)
```

### 5. Log All Generation Outcomes

```python
# ❌ Bad: No outcome logging
code = agent.generate(file_path, intent)
return code

# ✅ Good: Track outcomes for learning
code = agent.generate(file_path, intent)
log_agent_generation_outcome(
    agent_id,
    file_path,
    status="success",
    tokens_used=llm.tokens_used,
    conflict_report=report,
    success=True
)
return code
```

### 6. Use Rich Context for Developers

```python
# When logging human developer activity
log_activity(
    developer_id="alice@company.com",
    file_path="src/payment.py",
    intent="Refactor payment processing to support retries",
    region="process_payment (lines 50-100)",
    intent_category="refactor",
    intent_scope="single-function",
    blocking_others=False,
    estimated_completion=1800  # 30 minutes
)
```

---

## Integration Checklist

- [ ] Import `check_conflicts_for_agent` in pre-generation hook
- [ ] Call conflict check before code generation
- [ ] Handle MEDIUM risk with guidance injection
- [ ] Block HIGH risk with error message
- [ ] Format and inject conflict context to prompts
- [ ] Log generation outcomes post-completion
- [ ] Classify intents using `classify_intent()`
- [ ] Respect estimated wait times
- [ ] Test with real agents (Claude, Devin)
- [ ] Monitor conflict detection accuracy
- [ ] Gather feedback from developers/agents
- [ ] Document integration in your system

---

## Next Steps

### Immediate
- ✅ Agent integration layer complete
- ✅ Intent classification working
- ✅ Prompt injection format defined
- ⏳ Integrate with Claude Code (awaiting platform)
- ⏳ Integrate with Devin (awaiting API)

### Short Term (Recommended)
1. Deploy conflict detection to staging
2. Test with real developers and agents
3. Measure false positive/negative rates
4. Collect feedback on guidance quality
5. Iterate on prompt injection format

### Medium Term
1. Add ML-based conflict prediction
2. Build auto-merge safety checker
3. Implement distributed sync layer
4. Create IDE plugins (VS Code, Cursor)
5. Add real-time WebSocket updates

### Long Term
1. Conflict auto-resolution suggestions
2. Distributed transaction log
3. Full CI/CD pipeline integration
4. Advanced dependency tracking

---

## Troubleshooting

### Q: Agent ignores conflict guidance
**A:** Ensure prompt injection is happening before model call. Check that guidance text is properly formatted markdown.

### Q: False positives in overlap detection
**A:** This is expected for keyword-based heuristic. Recommend moving to AST-based detection for production. Confidence scores help prioritize true conflicts.

### Q: Intent classification is inaccurate
**A:** Classification uses keyword matching (simple but fast). For better accuracy, plan to integrate intent extraction from code diffs or git commit messages.

### Q: Waiting doesn't work as expected
**A:** Ensure entries are properly expired after 30 minutes. Check that `get_active_entries()` is filtering correctly.

---

## Support & Feedback

- **Questions?** See CONFLICT_WARNING_POC.md for technical deep dive
- **Integration help?** Check QUICKSTART.md for code examples
- **Design questions?** Read DESIGN_SYSTEM.md for UI details
- **Full overview?** Start with README.md

---

**Status:** ✅ Agent Integration Complete  
**Ready for:** Claude Code, Devin, Cursor, Custom Workflows  
**Testing:** All 7 scenarios passing, ready for production trials
