# Enterprise Scaling: OpenAI Agent Coordination

## Overview

Integrate coordination state machine with **OpenAI API** (GPT-4, Code Interpreter, Assistants API) for enterprise deployments with multiple AI agents.

## Architecture

```
OpenAI GPT-4 / Assistants API
├── Multiple Assistant Instances
├── Function Calling for Coordination
└── Custom Coordination Service

OpenAI Agent 1 (Assistant + Function Calls)
├── Pre-Gen: check_coordination() function call
├── Generate Code
└── Post-Gen: mark_complete() function call

OpenAI Agent 2 (Assistant + Function Calls)
├── Pre-Gen: check_coordination() function call
├── Generate Code
└── Post-Gen: mark_complete() function call
```

## Implementation

### 1. Setup: OpenAI API Integration

```python
import openai
from typing import Optional, Dict, List
from coordination_state_machine import CoordinationStateMachine

class CoordinatedOpenAIAgent:
    def __init__(
        self,
        agent_id: str,
        model: str = "gpt-4",
        api_key: str = None
    ):
        self.agent_id = agent_id
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.coordination = CoordinationStateMachine()
        self.checkpoint = None
    
    async def generate_code(
        self,
        file_path: str,
        region: str,
        intent: str,
        system_prompt: str = None
    ) -> Dict:
        """
        Main entry point for coordinated code generation with OpenAI.
        """
        
        # STEP 1: PRE-GENERATION - Check coordination
        check_result = await self._check_coordination(
            file_path=file_path,
            region=region,
            intent=intent
        )
        
        if check_result['action'] == 'blocked':
            # Wait for availability
            return await self._wait_for_lock_release(file_path, region)
        
        elif check_result['action'] == 'decision_required':
            # Get agent decision
            decision = await self._get_agent_decision(check_result)
            
            if decision == 'wait':
                return await self._wait_for_lock_release(file_path, region)
            elif decision == 'collaborate':
                return await self._collaborate(check_result)
        
        # STEP 2: GENERATION - Call OpenAI with coordination context
        tools = self._get_coordination_tools()
        messages = self._build_coordinated_prompt(
            file_path=file_path,
            region=region,
            intent=intent,
            conflict_context=check_result.get('conflict_details')
        )
        
        response = await self._call_openai_with_tools(
            messages=messages,
            tools=tools,
            system_prompt=system_prompt
        )
        
        # STEP 3: POST-GENERATION - Mark completion
        await self._mark_completion(file_path, 'completed')
        
        return {
            'status': 'completed',
            'code': response['content'],
            'model': self.model
        }
    
    def _get_coordination_tools(self) -> List[Dict]:
        """
        Define OpenAI function tools for coordination.
        These are called during the agent's agentic loop.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_coordination_status",
                    "description": "Check if there are any conflicts on the file we're about to edit",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file"
                            },
                            "region": {
                                "type": "string",
                                "description": "Code region (e.g., 'lines 20-40' or 'function_name')"
                            },
                            "intent": {
                                "type": "string",
                                "description": "What we're planning to do"
                            }
                        },
                        "required": ["file_path", "region", "intent"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "request_collaboration",
                    "description": "Request to collaborate with another agent on a high-risk conflict",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["file_path", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wait_for_other_agent",
                    "description": "Wait for another agent to finish working on this file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "max_wait_seconds": {
                                "type": "integer",
                                "description": "Maximum time to wait"
                            }
                        },
                        "required": ["file_path", "max_wait_seconds"]
                    }
                }
            }
        ]
    
    async def _call_openai_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        system_prompt: str = None
    ) -> Dict:
        """
        Call OpenAI's ChatGPT API with function calling.
        Handle tool calls in a loop (agentic pattern).
        """
        
        system = system_prompt or "You are an expert code generator."
        
        while True:
            # Call OpenAI
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2
            )
            
            # Check what the model returned
            if response.choices[0].message.get("content"):
                # Model generated code
                return {
                    'content': response.choices[0].message.content,
                    'tokens': response.usage.total_tokens
                }
            
            # Model called a tool
            if response.choices[0].message.get("tool_calls"):
                for tool_call in response.choices[0].message.tool_calls:
                    tool_result = await self._execute_tool(tool_call)
                    
                    # Add to messages for next iteration
                    messages.append({
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                        "tool_calls": response.choices[0].message.tool_calls
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
    
    async def _execute_tool(self, tool_call) -> Dict:
        """Execute coordination tool call from OpenAI"""
        
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        if func_name == "check_coordination_status":
            return await self._check_coordination(**args)
        
        elif func_name == "request_collaboration":
            return await self._collaborate(**args)
        
        elif func_name == "wait_for_other_agent":
            return await self._wait_for_lock_release(
                file_path=args['file_path'],
                max_wait=args['max_wait_seconds']
            )
        
        else:
            return {"error": f"Unknown tool: {func_name}"}
    
    async def _check_coordination(self, file_path: str, region: str, intent: str):
        """Tool implementation: Check for conflicts"""
        
        self.coordination.log_intent(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region,
            intent=intent
        )
        
        check = self.coordination.check_conflicts(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region
        )
        
        if check['risk_score'] < 30:
            return {
                'status': 'safe',
                'message': 'No conflicts detected. Safe to proceed.'
            }
        
        elif check['risk_score'] < 70:
            return {
                'status': 'warning',
                'risk_score': check['risk_score'],
                'message': f"Low conflict risk with {check['conflicting_agents']}",
                'recommendation': 'Proceed with caution, coordinate with agents'
            }
        
        else:
            return {
                'status': 'high_risk',
                'risk_score': check['risk_score'],
                'conflicting_agents': check['conflicting_agents'],
                'conflict_details': check['conflict_details'],
                'message': 'High risk conflict detected',
                'options': ['wait', 'collaborate', 'wrap_up_request']
            }
    
    async def _wait_for_lock_release(
        self,
        file_path: str,
        region: str,
        max_wait: int = 3600
    ) -> Dict:
        """
        Wait for another agent to finish.
        Uses event subscription (no polling).
        """
        
        # Save checkpoint
        checkpoint = self.coordination.GenerationCheckpoint(
            agent_id=self.agent_id,
            file_path=file_path,
            region=region,
            intent="Waiting for other agent",
            tokens_generated=0,
            context_buffer="",
            timestamp=datetime.now().isoformat()
        )
        
        self.coordination._enter_waiting_state(self.agent_id, checkpoint)
        
        # Wait for event
        lock_cleared = await self.coordination.await_event(
            'lock_removed',
            timeout_seconds=max_wait
        )
        
        if lock_cleared:
            return {
                'status': 'lock_released',
                'message': f'Lock on {file_path} released. Ready to proceed.'
            }
        else:
            return {
                'status': 'timeout',
                'message': f'Timeout waiting for lock on {file_path}'
            }
    
    async def _collaborate(self, file_path: str, reason: str = "") -> Dict:
        """Request collaboration with other agent"""
        
        self.coordination._enter_collaboration_state(self.agent_id)
        
        return {
            'status': 'collaboration_proposed',
            'message': f'Collaboration request sent for {file_path}',
            'reason': reason
        }
    
    async def _mark_completion(self, file_path: str, status: str):
        """Mark work complete"""
        
        if status == 'completed':
            self.coordination.mark_completed(self.agent_id)
        else:
            self.coordination.mark_cancelled(self.agent_id)
    
    def _build_coordinated_prompt(
        self,
        file_path: str,
        region: str,
        intent: str,
        conflict_context: list = None
    ) -> List[Dict]:
        """Build messages for OpenAI with coordination context"""
        
        conflict_notice = ""
        if conflict_context:
            conflict_notice = f"""
Other agents working on this file:
{chr(10).join(f"- {c}" for c in conflict_context)}

Please coordinate with them. Use the check_coordination_status tool to understand conflicts.
"""
        
        return [
            {
                "role": "user",
                "content": f"""
Task: Edit {file_path}
Region: {region}
Intent: {intent}

{conflict_notice}

Before you start, use the check_coordination_status tool.
If there's a conflict, decide whether to wait, collaborate, or proceed carefully.
"""
            }
        ]
```

### 2. Assistants API Integration (Higher-Level)

```python
class CoordinatedOpenAIAssistant:
    """
    Use OpenAI Assistants API with code coordination.
    Simpler than ChatCompletion but less flexible.
    """
    
    def __init__(self, agent_id: str, assistant_id: str = None):
        self.agent_id = agent_id
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.coordination = CoordinationStateMachine()
        
        # Create or use existing assistant
        self.assistant_id = assistant_id or self._create_assistant()
        self.thread = None
    
    def _create_assistant(self) -> str:
        """Create a coordination-aware assistant"""
        
        assistant = self.client.beta.assistants.create(
            name=f"Coordinated Code Generator {self.agent_id}",
            instructions="""
You are a code generator that works as part of a multi-agent team.

Before making changes:
1. Use check_coordination_status to understand if anyone else is working on this file
2. If there's a high-risk conflict, decide: wait, collaborate, or proceed
3. Generate minimal, clear changes
4. After completion, call mark_complete

Tools available:
- check_coordination_status: Check for conflicts
- request_collaboration: Ask to work together
- wait_for_agent: Pause and resume later
- mark_complete: Signal that you're done
""",
            model="gpt-4",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "check_coordination_status",
                        "description": "Check for conflicts before editing",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "region": {"type": "string"},
                                "intent": {"type": "string"}
                            },
                            "required": ["file_path", "region", "intent"]
                        }
                    }
                }
            ]
        )
        
        return assistant.id
    
    async def generate_code(self, file_path: str, intent: str) -> str:
        """Generate coordinated code"""
        
        # Create thread
        self.thread = self.client.beta.threads.create()
        
        # Send message
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=f"Edit {file_path}: {intent}"
        )
        
        # Run assistant
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_id
        )
        
        # Wait for completion/tool calls
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )
            
            if run.status == "completed":
                # Get final response
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread.id
                )
                return messages.data[0].content[0].text
            
            elif run.status == "requires_action":
                # Handle tool calls
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    output = await self._handle_tool_call(tool_call)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(output)
                    })
                
                # Submit tool outputs
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
```

### 3. Multi-Agent Orchestration

```python
class OpenAIAgentOrchestrator:
    """
    Manage multiple OpenAI agents coordinating on same repo.
    """
    
    def __init__(self, num_agents: int = 3):
        self.agents = [
            CoordinatedOpenAIAgent(agent_id=f"openai-agent-{i}")
            for i in range(num_agents)
        ]
        self.coordination = CoordinationStateMachine()
    
    async def generate_in_parallel(self, tasks: List[Dict]):
        """
        Generate code for multiple tasks in parallel,
        with coordination preventing conflicts.
        """
        
        results = []
        for task in tasks:
            agent = self.agents[len(results) % len(self.agents)]
            
            result = await agent.generate_code(
                file_path=task['file'],
                region=task.get('region', ''),
                intent=task['intent']
            )
            
            results.append({
                'task': task,
                'agent_id': agent.agent_id,
                'status': result['status'],
                'code': result.get('code')
            })
        
        return results
```

## Deployment

### Option 1: Lambda (Serverless)

```python
# lambda_handler.py
from coordination_state_machine import CoordinationStateMachine

coordination = CoordinationStateMachine()

def lambda_handler(event, context):
    """
    API Gateway → Lambda → OpenAI + Coordination
    """
    
    agent_id = event['agent_id']
    file_path = event['file_path']
    intent = event['intent']
    
    agent = CoordinatedOpenAIAgent(agent_id=agent_id)
    result = asyncio.run(agent.generate_code(
        file_path=file_path,
        region=event.get('region', ''),
        intent=intent
    ))
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

### Option 2: Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openai-coordinator
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: coordinator
        image: openai-coordinator:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-creds
              key: api-key
        - name: COORDINATION_URL
          value: "http://coordination-service:8000"
        ports:
        - containerPort: 8000
```

## Cost Analysis

| Component | Cost/Month |
|-----------|-----------|
| OpenAI API (GPT-4, ~100k tokens) | $2-10 |
| Coordination Service | $30-100 |
| Database | $10-50 |
| **Total** | **$40-160** |

## Getting Started

- [ ] Set up Coordination Service
- [ ] Create CoordinatedOpenAIAgent class
- [ ] Define OpenAI function tools
- [ ] Implement tool execution handlers
- [ ] Test with 2 agents
- [ ] Deploy to Lambda/Kubernetes
- [ ] Monitor costs and latency

---

See `ENTERPRISE_SCALING_DEVIN.md` for Devin integration and `ENTERPRISE_SCALING_CODEX.md` for GitHub Copilot.
