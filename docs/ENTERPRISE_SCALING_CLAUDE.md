# Enterprise Scaling: Claude Agent Coordination

## Overview

This guide shows how to integrate the coordination state machine with **Anthropic's Claude API** and **Claude Code** for enterprise deployments.

## Architecture

```
Enterprise Environment
├── Multiple Claude Agents (via API)
├── Coordination Service (your infrastructure)
├── Shared State Store (Cloud or Git-backed)
└── Event Bus (WebSocket or Polling)

Claude Agent 1 (Tool Use Loop)
├── Pre-Gen Hook → coordination_check()
├── Generate Code
└── Post-Gen Hook → coordination_complete()

Claude Agent 2 (Tool Use Loop)
├── Pre-Gen Hook → coordination_check()
├── Generate Code  
└── Post-Gen Hook → coordination_complete()
```

## Implementation

### 1. Setup: Claude SDK Integration

```python
from anthropic import Anthropic
from coordination_state_machine import CoordinationStateMachine

class CoordinatedClaudeAgent:
    def __init__(self, agent_id: str, model: str = "claude-opus-5"):
        self.agent_id = agent_id
        self.client = Anthropic(api_key="your-api-key")
        self.coordination = CoordinationStateMachine()
        self.model = model
        self.checkpoint = None
    
    async def generate_code(
        self,
        file_path: str,
        region: str,
        intent: str,
        system_prompt: str = None
    ):
        """
        Main entry point for code generation with coordination.
        """
        
        # STEP 1: Coordination Check (PRE-GENERATION)
        check_result = await self._coordination_check(
            file_path=file_path,
            region=region,
            intent=intent
        )
        
        if check_result['action'] == 'blocked':
            return {
                'status': 'blocked',
                'reason': check_result['reason'],
                'wait_until': check_result['wait_until']
            }
        
        elif check_result['action'] == 'decision_required':
            decision = await self._get_decision(check_result)
            
            if decision == 'wait':
                # Save checkpoint and sleep
                return await self._wait_for_availability(file_path, region)
            
            elif decision == 'collaborate':
                return await self._initiate_collaboration(file_path, check_result)
        
        # STEP 2: Generation (with coordination context)
        result = await self._generate_with_context(
            file_path=file_path,
            region=region,
            intent=intent,
            system_prompt=system_prompt,
            conflict_context=check_result.get('conflict_details')
        )
        
        # STEP 3: Completion (POST-GENERATION)
        await self._coordination_complete(file_path, result['status'])
        
        return result
    
    async def _coordination_check(self, file_path, region, intent):
        """PRE-GENERATION: Check for conflicts"""
        
        # Log this agent's intent
        self.coordination.log_intent(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region,
            intent=intent,
            duration_minutes=30
        )
        
        # Check for conflicts
        check = self.coordination.check_conflicts(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region
        )
        
        return {
            'action': 'proceed' if check['risk_score'] < 30 else \
                      'warning' if check['risk_score'] < 70 else \
                      'decision_required',
            'risk_score': check['risk_score'],
            'conflicting_agents': check['conflicting_agents'],
            'conflict_details': check.get('conflict_details'),
            'decision_options': check.get('decision_options', [])
        }
    
    async def _generate_with_context(
        self,
        file_path: str,
        region: str,
        intent: str,
        system_prompt: str = None,
        conflict_context: list = None
    ):
        """GENERATION: Call Claude API with coordination context"""
        
        # Build conflict awareness into prompt
        conflict_notice = ""
        if conflict_context:
            conflict_notice = f"""
Note: There are other agents working on this file:
{chr(10).join(f"- {c}" for c in conflict_context)}

Coordinate your changes to minimize merge conflicts.
"""
        
        messages = [
            {
                "role": "user",
                "content": f"""
File: {file_path}
Region: {region}
Intent: {intent}

{conflict_notice}

Generate the code. Focus on:
1. Clear, modular changes
2. Minimal line changes
3. Compatibility with other changes
"""
            }
        ]
        
        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt or "You are an expert code generator.",
            messages=messages
        )
        
        return {
            'status': 'completed',
            'code': response.content[0].text,
            'tokens_used': response.usage.output_tokens,
            'model': self.model
        }
    
    async def _coordination_complete(self, file_path: str, status: str):
        """POST-GENERATION: Mark work complete"""
        
        if status == 'completed':
            self.coordination.mark_completed(self.agent_id)
        else:
            self.coordination.mark_cancelled(self.agent_id)
    
    async def _get_decision(self, check_result):
        """
        Ask Claude to decide how to handle conflict.
        Or use a heuristic if you want.
        """
        
        # Option 1: Ask Claude
        prompt = f"""
Conflict detected:
Risk Score: {check_result['risk_score']}/100
Agents: {check_result['conflicting_agents']}
Details: {check_result['conflict_details']}

Options:
1. Wait for others to finish
2. Collaborate/coordinate
3. Request wrap-up

What should we do?
"""
        
        # For now, return 'wait' for high-risk
        return 'wait'
    
    async def _wait_for_availability(self, file_path: str, region: str):
        """
        Save checkpoint and wait for lock to clear.
        """
        
        checkpoint = self.coordination.GenerationCheckpoint(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region,
            intent=f"Working on {file_path}",
            tokens_generated=0,  # Haven't generated yet
            context_buffer="",   # Haven't started
            timestamp=datetime.now().isoformat()
        )
        
        self.coordination._enter_waiting_state(self.agent_id, checkpoint)
        
        # Wait for event (async, no polling)
        lock_cleared = await self.coordination.await_event('lock_removed')
        
        if lock_cleared:
            return {
                'status': 'resumed',
                'checkpoint': checkpoint,
                'message': f'Ready to work on {file_path}'
            }
        else:
            return {
                'status': 'timeout',
                'message': f'Lock on {file_path} not cleared within timeout'
            }
    
    async def _initiate_collaboration(self, file_path, check_result):
        """
        Notify other agent that we want to collaborate.
        """
        
        self.coordination._enter_collaboration_state(self.agent_id)
        
        return {
            'status': 'collaboration_proposed',
            'agents': check_result['conflicting_agents'],
            'message': f'Collaboration proposed with {check_result["conflicting_agents"]}'
        }
```

### 2. Tool Use Integration

Add coordination as a tool in Claude's tool use loop:

```python
class CoordinationTool:
    """Tool for Claude to check/manage coordination state"""
    
    def __init__(self, coordination: CoordinationStateMachine):
        self.coordination = coordination
    
    def get_schema(self):
        return {
            "name": "check_coordination",
            "description": "Check for conflicts before generating code",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "region": {"type": "string"},
                    "intent": {"type": "string"}
                },
                "required": ["file_path", "region", "intent"]
            }
        }
    
    async def execute(self, file_path: str, region: str, intent: str):
        """Claude calls this before generating code"""
        
        check = self.coordination.check_conflicts(
            agent_id="claude",
            file_path=file_path,
            region=region
        )
        
        if check['risk_score'] > 70:
            return {
                "action": "high_risk_lock",
                "risk_score": check['risk_score'],
                "message": f"High risk on {file_path}. Another agent is working here.",
                "options": ["wait", "collaborate", "wrap_up_request"]
            }
        else:
            return {
                "action": "proceed",
                "message": "Safe to generate code"
            }
```

### 3. Multi-Agent Orchestration

```python
class ClaudeAgentOrchestrator:
    """
    Manages multiple Claude agents coordinating on same repo.
    """
    
    def __init__(self, num_agents: int = 3):
        self.agents = [
            CoordinatedClaudeAgent(agent_id=f"claude-agent-{i}")
            for i in range(num_agents)
        ]
        self.coordination = CoordinationStateMachine()
    
    async def distribute_tasks(self, tasks: List[Task]):
        """
        Assign tasks to agents with conflict awareness.
        """
        
        results = []
        for task in tasks:
            # Find available agent
            agent = await self._find_available_agent(task)
            
            # Generate code
            result = await agent.generate_code(
                file_path=task.file,
                region=task.region,
                intent=task.description
            )
            
            results.append({
                'task': task,
                'agent': agent.agent_id,
                'result': result
            })
        
        return results
    
    async def _find_available_agent(self, task: Task):
        """
        Find agent that isn't blocked on this file.
        """
        
        for agent in self.agents:
            check = self.coordination.check_conflicts(
                agent_id=agent.agent_id,
                file_path=task.file,
                region=task.region
            )
            
            if check['risk_score'] < 50:
                return agent
        
        # All blocked, wait for one to free up
        return self.agents[0]
```

### 4. Monitoring & Observability

```python
class CoordinationMonitor:
    """Monitor coordination state for observability"""
    
    def __init__(self, coordination: CoordinationStateMachine):
        self.coordination = coordination
    
    def get_metrics(self):
        """Return coordination metrics"""
        
        status = self.coordination.get_status()
        
        return {
            'active_agents': len([s for s in status if s['state'] == 'active']),
            'waiting_agents': len([s for s in status if s['state'] == 'waiting']),
            'locked_files': len(set(s['file'] for s in status if s['state'] == 'locked')),
            'total_conflicts': sum(1 for s in status if s['risk_score'] and s['risk_score'] > 0)
        }
    
    def get_agent_status(self, agent_id: str):
        """Get specific agent status"""
        return self.coordination.get_status(agent_id=agent_id)
    
    def log_metrics(self):
        """Log metrics to monitoring system (DataDog, New Relic, etc.)"""
        
        metrics = self.get_metrics()
        
        # Example: Send to DataDog
        # datadog_client.gauge('claude.agents.active', metrics['active_agents'])
        # datadog_client.gauge('claude.agents.waiting', metrics['waiting_agents'])
```

## Deployment Scenarios

### Scenario 1: Claude API (Stateless)

```
Multiple Claude Instances
    ↓
Coordination Service (Managed)
    ↓
Cloud Database (Firestore, DynamoDB)
```

**Setup:**
1. Deploy Coordination Service to Cloud Run / Lambda
2. Set up Firestore / DynamoDB for state
3. Each Claude instance calls Coordination Service REST API
4. Subscribe to WebSocket for events

### Scenario 2: Claude Code (With IDE Integration)

```
VS Code with Claude Plugin
    ↓
Claude Agent (in plugin)
    ↓
Coordination Service
    ↓
Shared State Store
```

**Setup:**
1. Add coordination check in Claude Code's pre-generation hook
2. Show lock status in IDE UI
3. Offer "Wait", "Collaborate", "Force" buttons
4. Stream coordination events to IDE

### Scenario 3: Multi-Repo Coordination

```
Repo 1 (Auth Service)  ─┐
Repo 2 (Payment Service)├─→ Central Coordination Service
Repo 3 (API Gateway)   ─┘
                         ↓
                   Shared State
```

**Setup:**
1. Coordination Service spans all repos
2. Agents from different repos can detect cross-repo conflicts
3. Coordinate changes across service boundaries

## Scaling Considerations

| Scale | Approach | Challenges |
|-------|----------|------------|
| 1-3 agents | Git-backed | No real scaling needed |
| 5-10 agents | Cloud + Polling | Polling latency acceptable |
| 10-50 agents | Cloud + WebSocket | Need real-time events |
| 50+ agents | Multi-region + Cache | Distributed consistency |
| 100+ agents | Sharding by repo | Regional coordination services |

## Cost Estimation (AWS Example)

```
Coordination Service (EC2 t3.medium):     $30/month
Database (DynamoDB on-demand):            $0-100/month (usage-based)
WebSocket/API Gateway:                    $0-50/month (usage-based)
CloudWatch Monitoring:                    $10/month

Total: $40-190/month for small enterprise
```

## Security

```python
# All Claude agents authenticate
class CoordinationClient:
    def __init__(self, api_key: str, agent_id: str):
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'X-Agent-ID': agent_id,
            'X-API-Version': 'v1'
        }
    
    # All requests signed and encrypted
    async def request(self, endpoint: str, data: dict):
        response = await self.session.post(
            endpoint,
            json=data,
            headers=self.headers,
            ssl=ssl_context  # TLS 1.3
        )
        return response.json()
```

## Getting Started Checklist

- [ ] Set up Coordination Service (Cloud Run / Lambda)
- [ ] Configure state store (Firestore / DynamoDB)
- [ ] Add CoordinatedClaudeAgent wrapper
- [ ] Implement pre-generation hook
- [ ] Add checkpoint save/load
- [ ] Set up WebSocket subscriptions
- [ ] Configure monitoring
- [ ] Test with 2-3 Claude agents
- [ ] Load test
- [ ] Deploy to production
- [ ] Document for team

## Next Steps

- See `ENTERPRISE_SCALING_OPENAI.md` for OpenAI integration
- See `ENTERPRISE_SCALING_DEVIN.md` for Devin integration
- See `INTEGRATION_ARCHITECTURE.md` for deployment patterns
