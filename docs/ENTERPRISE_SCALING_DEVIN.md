# Enterprise Scaling: Devin Agent Coordination

## Overview

Integrate coordination state machine with **Devin** (Cognition's autonomous AI engineer) for enterprise deployments. Devin handles end-to-end tasks; coordination prevents multiple Devins from conflicting on the same codebase.

## Architecture

```
Devin (Autonomous Engineer)
├── Pre-Task Hook → Check Coordination
├── Execute Task (file editing, git, testing)
└── Post-Task Hook → Mark Complete

Coordination Service
├── Shared Activity Log
├── Event Bus
└── Checkpoint Store

Multiple Devin Instances
├── Devin 1: "Add authentication"
├── Devin 2: "Refactor payment module"
└── Devin 3: "Update database schema"
```

## Implementation

### 1. Devin SDK Integration

```python
from devin import DevinClient, Task
from coordination_state_machine import CoordinationStateMachine

class CoordinatedDevinAgent:
    def __init__(self, agent_id: str, api_key: str = None):
        self.agent_id = agent_id
        self.devin = DevinClient(api_key=api_key or os.getenv("DEVIN_API_KEY"))
        self.coordination = CoordinationStateMachine()
    
    async def execute_task(
        self,
        task_description: str,
        affected_files: List[str],
        affected_regions: List[str] = None
    ) -> Dict:
        """
        Execute a task with coordination awareness.
        Devin operates autonomously but checks for conflicts.
        """
        
        # STEP 1: Coordination Check
        regions = affected_regions or ["full_file"]
        
        coordination_checks = []
        for file_path, region in zip(affected_files, regions):
            check = self.coordination.check_conflicts(
                agent_id=self.agent_id,
                file_path=file_path,
                region=region
            )
            coordination_checks.append({
                'file': file_path,
                'region': region,
                'risk_score': check['risk_score'],
                'conflicting_agents': check['conflicting_agents']
            })
        
        # High risk? Get decision
        high_risk = [c for c in coordination_checks if c['risk_score'] > 70]
        if high_risk:
            decision = await self._get_task_decision(high_risk)
            
            if decision == 'wait':
                return await self._defer_task(task_description, affected_files)
            elif decision == 'collaborate':
                return await self._schedule_collaboration(
                    task_description,
                    high_risk
                )
        
        # STEP 2: Log Intent
        for file_path in affected_files:
            self.coordination.log_intent(
                agent_id=self.agent_id,
                file_path=file_path,
                region="full_file",
                intent=task_description
            )
        
        # STEP 3: Devin Executes
        task = Task(
            description=task_description,
            context={
                'coordination_aware': True,
                'affected_files': affected_files,
                'coordination_checks': coordination_checks
            }
        )
        
        result = await self.devin.execute_task(task)
        
        # STEP 4: Completion
        for file_path in affected_files:
            self.coordination.mark_completed(self.agent_id)
        
        return {
            'status': 'completed',
            'task': task_description,
            'devin_result': result
        }
    
    async def _get_task_decision(self, high_risk_files):
        """
        Decide how to handle high-risk conflicts.
        For Devin: usually wait, since it's autonomous.
        """
        
        # Simple heuristic: wait if risk > 80
        max_risk = max(f['risk_score'] for f in high_risk_files)
        
        if max_risk > 80:
            return 'wait'
        elif max_risk > 70:
            return 'collaborate'  # Suggest sync with other agent
        else:
            return 'proceed'
    
    async def _defer_task(self, task: str, files: List[str]):
        """
        Schedule task to run later (after lock clears).
        """
        
        # Save task
        deferred_task = {
            'agent_id': self.agent_id,
            'task': task,
            'files': files,
            'saved_at': datetime.now().isoformat()
        }
        
        # Wait for all files to be unlocked
        tasks = []
        for file_path in files:
            task = asyncio.create_task(
                self.coordination.await_event('lock_removed')
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Re-execute
        return await self.execute_task(task, files)
    
    async def _schedule_collaboration(self, task: str, conflicts):
        """
        Notify other agents to sync up.
        """
        
        self.coordination._enter_collaboration_state(self.agent_id)
        
        return {
            'status': 'collaboration_needed',
            'task': task,
            'conflicting_agents': [c['conflicting_agents'] for c in conflicts],
            'message': 'Waiting for team to coordinate'
        }
```

### 2. Devin Task Queue with Coordination

```python
class DevinTaskQueue:
    """
    Queue tasks for multiple Devin instances,
    respecting coordination constraints.
    """
    
    def __init__(self, num_devins: int = 2):
        self.devins = [
            CoordinatedDevinAgent(agent_id=f"devin-{i}")
            for i in range(num_devins)
        ]
        self.queue = asyncio.Queue()
        self.coordination = CoordinationStateMachine()
    
    async def enqueue_task(self, task_description: str, affected_files: List[str]):
        """Add task to queue"""
        
        await self.queue.put({
            'description': task_description,
            'files': affected_files,
            'enqueued_at': datetime.now()
        })
    
    async def start_workers(self):
        """Start Devin workers processing queue"""
        
        for devin in self.devins:
            asyncio.create_task(self._worker(devin))
    
    async def _worker(self, devin: CoordinatedDevinAgent):
        """Process tasks for one Devin instance"""
        
        while True:
            task = await self.queue.get()
            
            result = await devin.execute_task(
                task_description=task['description'],
                affected_files=task['files']
            )
            
            self.queue.task_done()
```

### 3. Conflict Resolution in Devin Tasks

```python
class DevinConflictResolver:
    """
    When Devin detects a merge conflict (git merge, etc.),
    use coordination to resolve intelligently.
    """
    
    def __init__(self, coordination: CoordinationStateMachine):
        self.coordination = coordination
    
    async def resolve_conflict(
        self,
        file_path: str,
        conflict_markers: str,
        devin_agent_id: str
    ) -> str:
        """
        Resolve conflict by:
        1. Understanding what other agent was doing
        2. Coordinating the merge
        3. Returning resolved code
        """
        
        # Get context of conflicting agent
        status = self.coordination.get_status()
        other_agents = [
            s for s in status
            if s['file'] == file_path and s['agent'] != devin_agent_id
        ]
        
        if not other_agents:
            # No coordination info, Devin resolves independently
            return None
        
        other_agent = other_agents[0]
        conflict_context = {
            'other_agent': other_agent['agent'],
            'their_intent': other_agent['intent'],
            'region': other_agent.get('region', '')
        }
        
        # Devin resolves knowing what the other agent was trying to do
        return conflict_context
```

## Deployment

### Scenario 1: Scheduled Tasks

```python
# Cron: Every 4 hours, spawn Devin to handle backlog
import schedule

coordinator = DevinTaskQueue(num_devins=2)

def run_devin_tasks():
    # Load tasks from issue tracker, kanban, etc.
    tasks = [
        {'description': 'Add OAuth2 support', 'files': ['src/auth.py']},
        {'description': 'Update docs', 'files': ['docs/README.md']}
    ]
    
    for task in tasks:
        asyncio.run(
            coordinator.enqueue_task(
                task['description'],
                task['files']
            )
        )

schedule.every(4).hours.do(run_devin_tasks)
```

### Scenario 2: On-Demand from Issues

```python
# GitHub Issues → Devin with Coordination
async def issue_to_devin_task(issue):
    """
    When issue is labeled "auto-fix", spawn Devin.
    """
    
    # Parse affected files from issue
    affected_files = extract_files_from_issue(issue)
    
    coordinator = DevinTaskQueue(num_devins=1)
    
    await coordinator.enqueue_task(
        task_description=issue.title,
        affected_files=affected_files
    )
    
    await coordinator.start_workers()
```

## Integration with Devin's Built-in Tools

Devin has tools: git, file editor, CLI, etc. Enhance them with coordination:

```python
class CoordinatedDevinTools:
    """
    Wrap Devin's tools with coordination awareness.
    """
    
    def __init__(self, coordination: CoordinationStateMachine):
        self.coordination = coordination
    
    async def git_commit(self, message: str, files: List[str]):
        """
        Before committing, check coordination.
        """
        
        # Verify no conflicts on these files
        for file in files:
            check = self.coordination.check_conflicts(
                agent_id="devin",
                file_path=file,
                region="full_file"
            )
            
            if check['risk_score'] > 50:
                return {
                    'status': 'blocked',
                    'message': f'Cannot commit {file}: conflict detected',
                    'conflicting_agents': check['conflicting_agents']
                }
        
        # Safe to commit
        return await self.devin.git_commit(message, files)
    
    async def file_edit(self, file_path: str, changes: str, region: str):
        """
        Before editing file, check coordination.
        """
        
        check = self.coordination.check_conflicts(
            agent_id="devin",
            file_path=file_path,
            region=region
        )
        
        if check['risk_score'] > 70:
            return {
                'status': 'high_risk',
                'message': 'High risk conflict. Coordinate first.'
            }
        
        return await self.devin.edit_file(file_path, changes)
```

## Monitoring Devin + Coordination

```python
class DevinCoordinationMonitor:
    """Monitor Devin tasks through coordination lens"""
    
    def __init__(self, coordination: CoordinationStateMachine):
        self.coordination = coordination
    
    def get_dashboard(self):
        """
        Real-time dashboard of:
        - Active Devin tasks
        - Coordination conflicts
        - Wait times
        - Deferred tasks
        """
        
        status = self.coordination.get_status()
        
        return {
            'active_tasks': len([s for s in status if s['state'] == 'active']),
            'waiting_tasks': len([s for s in status if s['state'] == 'waiting']),
            'conflicts_detected': len([s for s in status if s.get('risk_score', 0) > 70]),
            'total_time_saved': self._calculate_time_saved(),
            'merge_conflicts_prevented': self._count_prevented_conflicts()
        }
```

## Cost Estimation

| Component | Cost |
|-----------|------|
| Devin API (per task) | $10-50 |
| Coordination Service | $30-100/month |
| Database | $10-50/month |
| **Per Devin Instance** | **$100-200/month** |

## Getting Started

- [ ] Set up CoordinatedDevinAgent
- [ ] Create task queue
- [ ] Connect to issue tracker
- [ ] Test with 1 Devin
- [ ] Add 2nd Devin, verify coordination
- [ ] Set up monitoring
- [ ] Deploy to production

---

See `ENTERPRISE_SCALING_CLAUDE.md` and `ENTERPRISE_SCALING_OPENAI.md` for other frameworks.
