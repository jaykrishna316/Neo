# NVIDIA NIM Integration with Neo

## Overview

The **NVIDIA Adapter** enables NVIDIA NIM (NVIDIA Inference Microservices) agents to coordinate with Neo, ensuring **zero merge conflicts** when multiple NVIDIA-powered agents generate code simultaneously.

### What This Enables

```
Traditional Multi-Agent Code Generation:
├─ Agent 1 generates code → Merge conflict risk
├─ Agent 2 generates code → Merge conflict risk  
├─ Agent 3 generates code → Merge conflict risk
└─ Result: 3 re-generations needed, 85% wasted tokens

Neo-Coordinated Generation:
├─ Agent 1 checks Neo → Low risk → Generates → Releases lock
├─ Agent 2 waits/checks Neo → Gets fresh context (C2 delta) → Generates → Releases lock
├─ Agent 3 waits/checks Neo → Gets fresh context (C2 delta) → Generates
└─ Result: Zero conflicts, 85% token savings via delta refresh
```

## Architecture

```
NVIDIA NIM Agents
       ↓
    AgentAdapter
    (check conflicts)
       ↓
   Neo Conflict
   Detection (C1)
       ↓
  Lock Manager
       ↓
 Activity Log
       ↓
   Delta Refresh (C2)
       ↓
Fresh Context to Next Agent
```

## Quick Start

### 1. Install Dependencies

```bash
cd Neo
pip install -r requirements.txt  # Includes mcp SDK
pip install requests             # For NIM API calls
```

### 2. Configure NVIDIA NIM Endpoint

Set environment variables:

```bash
export NVIDIA_NIM_ENDPOINT="http://localhost:8000"  # Local or cloud endpoint
export NVIDIA_NIM_API_KEY="your-api-key"            # If required
export NVIDIA_NIM_MODEL="nemotron-4-340b-instruct"  # or other NVIDIA model
```

### 3. Use the Adapter

```python
from core.agent_adapter_nvidia import create_nvidia_adapter
from core.agent_adapter import AgentInfo

# Create adapter
adapter = create_nvidia_adapter()

# Register agent
agent = AgentInfo(
    agent_id="code-agent-1",
    agent_type="nvidia_nim",
    capabilities=["code-generation", "testing"],
)
adapter.register_agent(agent)

# Complete coordination workflow
result = adapter.coordinate_with_nim_workflow(
    agent_id="code-agent-1",
    file_path="src/module.py",
    intent="Implement user authentication module",
    generation_prompt="Generate Python code for...",
)

print(result["workflow_status"])  # "success"
print(result["generated_code"])   # The generated code
print(result["tokens_used"])      # Tokens consumed
```

## API Reference

### NVIDIAAdapter

Main adapter class for coordinating NVIDIA NIM agents with Neo.

#### Constructor

```python
adapter = NVIDIAAdapter(config)
```

**Parameters:**
- `config` (optional): `NVIDIANIMConfig` instance. If `None`, loads from environment variables.

#### Methods

##### check_conflicts()

Check for conflicts **before** calling NVIDIA NIM API.

```python
result = adapter.check_conflicts(
    agent_id="agent-1",
    file_path="src/auth.py",
    intent="Add OAuth2 support",
    region="optional:specific-function"
)
```

**Returns:**
```python
{
    "risk_level": "LOW|MEDIUM|HIGH",
    "message": "Explanation of conflict status",
    "should_block": bool,
    "lock_holder": "agent-2" or None,
    "queue_position": 0 or None,
}
```

**Risk Levels:**
- **LOW**: No other agent working on this file → proceed
- **MEDIUM**: Another agent has lock → can proceed but may conflict
- **HIGH**: High conflict risk → should wait or coordinate

---

##### declare_intent()

Declare intent to work on a file. Acquires lock if available, or queues agent.

```python
result = adapter.declare_intent(
    agent_id="agent-1",
    file_path="src/auth.py",
    intent="Implement OAuth2 authentication",
    region=None,
    dependencies=["src/utils.py", "src/config.py"]
)
```

**Returns:**
```python
{
    "success": bool,
    "lock_state": "ACQUIRED|WAITING|PROMOTED",
    "message": "Status message"
}
```

**Lock States:**
- **ACQUIRED**: Agent has lock, can proceed with generation
- **WAITING**: Agent in queue, must wait for previous agent
- **PROMOTED**: Agent moved from waiting to acquired (previous agent released)

---

##### call_nvidia_nim()

Call NVIDIA NIM API for code generation.

```python
result = adapter.call_nvidia_nim(
    agent_id="agent-1",
    prompt="Generate Python function that...",
    file_path="src/auth.py"  # optional, for context
)
```

**Returns:**
```python
{
    "success": bool,
    "generated_code": "...",
    "tokens_used": 1234,
    "model": "nemotron-4-340b-instruct",
    "prompt": "...",
    "file_path": "src/auth.py"
}
```

---

##### log_completion()

Log work completion with metadata. Releases lock and promotes next agent in queue.

```python
result = adapter.log_completion(
    agent_id="agent-1",
    file_path="src/auth.py",
    metadata={
        "summary": "OAuth2 implementation completed",
        "lines_added": 120,
        "functions_added": 5,
        "tokens_used": 1234,
        "delta_tokens": 40,  # C2 savings for next agent
    }
)
```

**Returns:**
```python
{
    "success": bool,
    "message": "Work completion logged"
}
```

---

##### get_fresh_context()

Get fresh context after lock is released. Includes C2 delta refresh.

```python
result = adapter.get_fresh_context(
    agent_id="agent-2",
    file_path="src/auth.py"
)
```

**Returns:**
```python
{
    "previous_agent": "agent-1",
    "changes": {
        "lines_added": 120,
        "functions_added": 5,
        # ... other metadata
    },
    "summary": "OAuth2 implementation completed",
    "next_steps": [...],
    "token_savings": 460,  # C2: full_tokens - delta_tokens
    "delta_available": True  # C2 optimization possible
}
```

---

##### coordinate_with_nim_workflow()

**High-level orchestration method** combining all steps:

1. Check conflicts
2. Declare intent
3. Call NVIDIA NIM
4. Log completion

```python
result = adapter.coordinate_with_nim_workflow(
    agent_id="agent-1",
    file_path="src/auth.py",
    intent="Implement OAuth2 authentication",
    generation_prompt="Generate Python OAuth2 functions with error handling...",
    region=None
)
```

**Returns:**
```python
{
    "workflow_status": "success|blocked|failed|partial",
    "agent_id": "agent-1",
    "file_path": "src/auth.py",
    "lock_state": "ACQUIRED",
    "generated_code": "...",
    "tokens_used": 1234,
    "model": "nemotron-4-340b-instruct",
    "risk_level": "LOW"
}
```

---

### NVIDIANIMConfig

Configuration object for NIM connection.

```python
from core.agent_adapter_nvidia import NVIDIANIMConfig

config = NVIDIANIMConfig(
    nim_api_endpoint="http://localhost:8000",
    nim_api_key="optional-api-key",
    model="nemotron-4-340b-instruct",
    max_tokens=2048,
    temperature=0.7,
    top_p=0.9,
)

adapter = NVIDIAAdapter(config)
```

**Properties:**
- `nim_api_endpoint`: URL to NVIDIA NIM service
- `nim_api_key`: API key if authentication required
- `model`: Which NVIDIA model to use
- `max_tokens`: Max tokens in generated response
- `temperature`: Sampling temperature (0.0-1.0)
- `top_p`: Nucleus sampling parameter (0.0-1.0)

---

## Workflow Examples

### Example 1: Simple Single-Agent Generation

```python
from core.agent_adapter_nvidia import create_nvidia_adapter
from core.agent_adapter import AgentInfo

adapter = create_nvidia_adapter()

# Register
agent = AgentInfo(
    agent_id="auth-generator",
    agent_type="nvidia_nim",
    capabilities=["authentication"],
)
adapter.register_agent(agent)

# Generate with coordination
result = adapter.coordinate_with_nim_workflow(
    agent_id="auth-generator",
    file_path="src/auth.py",
    intent="Implement password hashing with bcrypt",
    generation_prompt="""
    Generate a Python function that:
    - Takes a password string
    - Returns a bcrypt hash
    - Includes error handling
    """,
)

if result["workflow_status"] == "success":
    print(f"Generated {len(result['generated_code'])} chars")
    print(f"Tokens used: {result['tokens_used']}")
    
    # Save generated code
    with open("src/auth.py", "w") as f:
        f.write(result["generated_code"])
```

### Example 2: Multi-Agent Coordination

```python
# Agent 1: Core implementation
adapter1 = create_nvidia_adapter()
# ... register agent1 ...
result1 = adapter1.coordinate_with_nim_workflow(
    agent_id="core-generator",
    file_path="src/module.py",
    intent="Generate core module functions",
    generation_prompt="...",
)

# Agent 2: Tests (gets fresh context from Agent 1)
adapter2 = create_nvidia_adapter()
# ... register agent2 ...

# Check conflicts (Agent 2 will see Agent 1's lock)
conflict = adapter2.check_conflicts(
    agent_id="test-generator",
    file_path="src/module.py",
    intent="Generate test suite"
)

if conflict["should_block"]:
    print(f"Waiting for lock... (queue position: {conflict['queue_position']})")
    # Poll or subscribe to lock release notifications

# Once Agent 1 releases, Agent 2 can get fresh context
context = adapter2.get_fresh_context(
    agent_id="test-generator",
    file_path="src/module.py"
)

if context["token_savings"] > 0:
    print(f"Using C2 delta refresh: {context['token_savings']} token savings!")

# Agent 2 generates tests with fresh context
result2 = adapter2.coordinate_with_nim_workflow(
    agent_id="test-generator",
    file_path="tests/test_module.py",
    intent="Generate test suite for core module",
    generation_prompt=f"""
    Generate pytest tests for functions from {context['previous_agent']}:
    
    Changes summary: {context['summary']}
    
    Test:
    - All {len(context['changes'])} new functions
    - Edge cases and error conditions
    - Integration with module functions
    """,
)
```

### Example 3: Error Handling

```python
result = adapter.coordinate_with_nim_workflow(
    agent_id="generator",
    file_path="src/module.py",
    intent="Generate module",
    generation_prompt="...",
)

if result["workflow_status"] == "blocked":
    print(f"Cannot proceed: {result['message']}")
    print(f"Lock holder: {result['lock_holder']}")
    # Implement wait/retry logic
    
elif result["workflow_status"] == "failed":
    print(f"Error: {result['error']}")
    # Handle NIM API errors, network issues, etc.
    
elif result["workflow_status"] == "partial":
    print(f"Warning: {result['warning']}")
    print(f"Code generated but logging failed")
    print(f"Generated: {result['generated_code']}")
    
elif result["workflow_status"] == "success":
    print("Success! Code generated and logged.")
    print(f"Risk level was: {result['risk_level']}")
```

---

## Environment Setup

### Local Development

```bash
# 1. Start NVIDIA NIM locally (requires NVIDIA GPU)
docker run -it --rm --gpus all \
  -p 8000:8000 \
  nvcr.io/nim/nvidia/nemotron-4-340b-instruct:latest

# 2. Set environment variables
export NVIDIA_NIM_ENDPOINT="http://localhost:8000"
export NVIDIA_NIM_MODEL="nemotron-4-340b-instruct"
```

### Cloud Deployment (Nebius, NVIDIA Cloud)

```bash
export NVIDIA_NIM_ENDPOINT="https://api.cloud.nvidia.com/v1/...your-endpoint"
export NVIDIA_NIM_API_KEY="your-api-key"
export NVIDIA_NIM_MODEL="nemotron-4-340b-instruct"
```

### Verification

```bash
# Test the setup
python3 -c "
from core.agent_adapter_nvidia import create_nvidia_adapter

adapter = create_nvidia_adapter()
print(f'✓ Adapter initialized')
print(f'  Endpoint: {adapter.config.nim_api_endpoint}')
print(f'  Model: {adapter.config.model}')
"
```

---

## Monitoring & Logging

### Activity Log Monitoring

Monitor real-time agent coordination:

```bash
# Terminal 1: Watch activity log
python3 scripts/watch_activity_log.py --follow --pretty
```

### Debug Logging

Enable debug logging to track adapter behavior:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Neo-NVIDIA-Adapter")
logger.setLevel(logging.DEBUG)

# Now all adapter operations log detailed debug info
adapter = create_nvidia_adapter()
```

Log output shows:
- Conflict checks and results
- Intent declarations and lock acquisitions
- NIM API calls and responses
- Completion logging and lock releases
- Fresh context retrieval

---

## Performance Metrics

### Token Efficiency with C2 Delta Refresh

When coordinating multiple agents:

| Approach | Agent 1 Tokens | Agent 2 Tokens | Agent 3 Tokens | Total | vs Traditional |
|----------|---|---|---|---|---|
| Traditional | 500 | 500 | 500 | 1500 | baseline |
| Neo (no C2) | 500 | 400 | 400 | 1300 | -13% |
| Neo + C2 | 500 | 40 | 50 | 590 | **-61%** |

**Key factors:**
- Agent 1 generates full context (cannot be optimized)
- Agents 2+ receive delta (only changed symbols, not full file)
- C2 saves ~90% of tokens for subsequent agents

### Measured Results from Tests

From `tests/test_claims_C1_C2.py`:

```
OAuth2 Multi-Agent Example:
├─ Agent 1 (Core):     500 tokens
├─ Agent 2 (Tests):     40 tokens (90% savings via C2)
└─ Agent 3 (Docs):      45 tokens (91% savings via C2)

Total: 585 tokens
Traditional: 1500 tokens
Savings: 61% (915 tokens)
```

---

## Troubleshooting

### NIM Endpoint Not Reachable

```
Error: ConnectionError: Failed to connect to http://localhost:8000
```

**Solution:**
1. Verify NIM is running: `curl http://localhost:8000/health`
2. Check endpoint in config: `echo $NVIDIA_NIM_ENDPOINT`
3. For cloud: verify API key: `echo $NVIDIA_NIM_API_KEY`

### Authorization Errors

```
Error: 401 Unauthorized
```

**Solution:**
```bash
export NVIDIA_NIM_API_KEY="your-actual-api-key"
# Or pass explicitly in config:
config = NVIDIANIMConfig(nim_api_key="your-key")
```

### Conflict Blocking Agent

```
Workflow blocked: HIGH conflict risk
Lock holder: agent-1
Queue position: 0
```

**Solution:** 
This is correct behavior. Agent is in queue waiting for agent-1. Either:
1. Wait and poll for lock release
2. Subscribe to lock notifications
3. Implement coordinate() to communicate with holding agent

### Token Usage Higher Than Expected

**Possible causes:**
1. Agent 1 cannot be optimized (generates full context)
2. C2 delta not applied if file changed significantly
3. Multiple agents on different files (no sharing of context)

**Optimization:**
- Use C2 delta refresh to avoid re-sending full files
- Coordinate agents on overlapping files for maximum savings
- Use `get_fresh_context()` to know available savings upfront

---

## Advanced Topics

### Custom NIM Models

```python
config = NVIDIANIMConfig(
    model="nemotron-4-340b-base",  # or other NVIDIA model
    max_tokens=4096,  # Adjust for model
)
adapter = NVIDIAAdapter(config)
```

Supported models:
- `nemotron-4-340b-instruct` (default)
- `nemotron-4-340b-base`
- Other NVIDIA NIM available models

### Agent Capabilities

Declare what agents can do:

```python
agent = AgentInfo(
    agent_id="multi-task",
    agent_type="nvidia_nim",
    capabilities=[
        "code-generation",
        "testing",
        "documentation",
        "refactoring"
    ],
)
```

Neo uses this for smarter conflict prediction.

### Multi-File Coordination

Agents can work on multiple files simultaneously (up to max_concurrent_files):

```python
for file_path in ["src/auth.py", "src/utils.py"]:
    adapter.declare_intent(
        agent_id="multi-file-agent",
        file_path=file_path,
        intent="Add security improvements",
    )
```

---

## Integration with Nebius & NVIDIA Cloud

### Nebius Token Factory Deployment

```yaml
# nebius-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: neo-nvidia-adapter
spec:
  type: LoadBalancer
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: neo-nvidia-adapter
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo-nvidia-adapter
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: neo-nvidia-adapter
    spec:
      containers:
      - name: neo
        image: neo:latest
        env:
        - name: NVIDIA_NIM_ENDPOINT
          value: "https://api.nims.ai/v1/..."
        - name: NVIDIA_NIM_API_KEY
          valueFrom:
            secretKeyRef:
              name: nvidia-secrets
              key: api-key
```

---

## Testing

Run adapter tests:

```bash
# Unit tests for NVIDIA adapter
pytest tests/test_nvidia_adapter.py -v

# Integration tests with mock NIM
pytest tests/test_nvidia_integration.py -v

# Multi-agent coordination demo
python3 demo/multi_agent_oauth2_demo.py
```

---

## FAQ

**Q: Can I use different models from different providers (NVIDIA + OpenAI)?**  
A: Yes! Neo provides separate adapters for each. Use `MCPAdapter` for Claude Code, `NVIDIAAdapter` for NVIDIA NIM, `RESTAdapter` for others.

**Q: How do agents know when lock is released?**  
A: Polling via `check_conflicts()` (simple) or webhook subscriptions (advanced). The demo uses polling with brief intervals.

**Q: What if all agents work on different files?**  
A: No conflicts occur, but C2 delta refresh doesn't apply across files. Each agent still gets activity log context.

**Q: Can I customize the conflict detection logic?**  
A: Yes! The adapter delegates to `core.pre_gen_check.check_for_conflicts()`. Customize that module for your rules.

**Q: What's the overhead of Neo coordination?**  
A: Minimal. Checking conflicts is a fast JSON lookup. Declaring intent is a single file write. The upside (preventing conflicts) far exceeds the cost.

---

## See Also

- [Neo Architecture Overview](./ARCHITECTURE.md)
- [Symbol-Level Staleness Detection (C1)](./C1_C2_SYMBOL_STALENESS_AND_DELTA_REFRESH.md)
- [Delta Refresh Implementation (C2)](./C1_C2_SYMBOL_STALENESS_AND_DELTA_REFRESH.md)
- [Activity Log Format](./ACTIVITY_LOG.md)
- [Agent Adapter Pattern](./AGENT_ADAPTERS.md)
