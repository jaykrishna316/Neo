#!/usr/bin/env python3
"""
Neo 2.0 Phase 5: Agent Autonomy Engine

Enables autonomous agent workflows with configurable policies.
Agents can automatically:
- Sync stale contexts
- Revalidate contexts after sync
- Consume handoffs and continue work
- Execute full workflow orchestrations
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

try:
    from .event_model import Event, EventType, EventFactory
    from .development_memory import DevelopmentMemory
    from .context_invalidation_engine import ContextInvalidationEngine
    from .temporal_handoff_engine import TemporalHandoffEngine
    from .dependency_graph import DependencyGraph
except ImportError:
    from event_model import Event, EventType, EventFactory
    from development_memory import DevelopmentMemory
    from context_invalidation_engine import ContextInvalidationEngine
    from temporal_handoff_engine import TemporalHandoffEngine
    from dependency_graph import DependencyGraph


class AutonomyLevel(Enum):
    """Agent autonomy levels"""
    NONE = "none"
    SYNC_ONLY = "sync_only"
    SYNC_AND_REVALIDATE = "sync_and_revalidate"
    FULL_AUTONOMOUS = "full_autonomous"


class AgentAutonomyPolicy:
    """Configuration for agent autonomy"""

    def __init__(
        self,
        agent_id: str,
        autonomy_level: AutonomyLevel = AutonomyLevel.SYNC_AND_REVALIDATE,
        can_auto_sync: bool = True,
        can_auto_revalidate: bool = True,
        can_auto_consume_handoffs: bool = False,
        can_auto_resolve_conflicts: bool = False,
        max_retry_attempts: int = 3,
        retry_delay_seconds: int = 60,
        rollback_on_failure: bool = True,
        notify_human_on_failure: bool = True,
    ):
        self.agent_id = agent_id
        self.autonomy_level = autonomy_level
        self.can_auto_sync = can_auto_sync
        self.can_auto_revalidate = can_auto_revalidate
        self.can_auto_consume_handoffs = can_auto_consume_handoffs
        self.can_auto_resolve_conflicts = can_auto_resolve_conflicts
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.rollback_on_failure = rollback_on_failure
        self.notify_human_on_failure = notify_human_on_failure
        self.created_at = datetime.now().isoformat()
        self.enabled = True

    def to_dict(self) -> Dict:
        """Serialize policy"""
        return {
            "agent_id": self.agent_id,
            "autonomy_level": self.autonomy_level.value,
            "can_auto_sync": self.can_auto_sync,
            "can_auto_revalidate": self.can_auto_revalidate,
            "can_auto_consume_handoffs": self.can_auto_consume_handoffs,
            "can_auto_resolve_conflicts": self.can_auto_resolve_conflicts,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "rollback_on_failure": self.rollback_on_failure,
            "notify_human_on_failure": self.notify_human_on_failure,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }


class AutonomousWorkflow:
    """Represents an autonomous workflow execution"""

    def __init__(
        self,
        workflow_id: str,
        agent_id: str,
        resource: str,
        workflow_type: str,  # "sync", "revalidate", "consume_handoff", "full_orchestration"
        trigger: str = "manual"  # "manual", "timeout", "context_invalidation", "handoff_available"
    ):
        self.workflow_id = workflow_id
        self.agent_id = agent_id
        self.resource = resource
        self.workflow_type = workflow_type
        self.trigger = trigger

        self.status = "PENDING"  # PENDING, EXECUTING, COMPLETED, FAILED, ROLLED_BACK
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None

        self.steps_executed = []  # List of step results
        self.current_step = None
        self.retry_count = 0
        self.error_message = None

    def to_dict(self) -> Dict:
        """Serialize workflow"""
        return {
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "resource": self.resource,
            "workflow_type": self.workflow_type,
            "trigger": self.trigger,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps_executed": self.steps_executed,
            "current_step": self.current_step,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
        }


class AgentAutonomyEngine:
    """
    Manages autonomous agent workflows.

    Enables agents to automatically:
    1. Sync stale contexts from handoffs
    2. Revalidate contexts after sync
    3. Consume handoffs and continue work
    4. Execute full workflow orchestrations
    """

    def __init__(
        self,
        development_memory: DevelopmentMemory,
        context_invalidation_engine: ContextInvalidationEngine,
        temporal_handoff_engine: TemporalHandoffEngine,
        dependency_graph: DependencyGraph
    ):
        self.development_memory = development_memory
        self.context_invalidation_engine = context_invalidation_engine
        self.temporal_handoff_engine = temporal_handoff_engine
        self.dependency_graph = dependency_graph

        # Agent policies: agent_id -> AgentAutonomyPolicy
        self.agent_policies: Dict[str, AgentAutonomyPolicy] = {}

        # Active workflows: workflow_id -> AutonomousWorkflow
        self.active_workflows: Dict[str, AutonomousWorkflow] = {}

        # Completed workflows history
        self.workflow_history: List[AutonomousWorkflow] = []

    def register_agent_policy(self, policy: AgentAutonomyPolicy) -> Tuple[bool, str]:
        """Register or update an agent's autonomy policy"""
        self.agent_policies[policy.agent_id] = policy

        event = Event(
            event_type=EventType.DEVELOPER_REGISTERED,
            actor=policy.agent_id,
            actor_type="agent",
            resource="system",
            details={
                "autonomy_level": policy.autonomy_level.value,
                "can_auto_sync": policy.can_auto_sync,
                "can_auto_revalidate": policy.can_auto_revalidate,
                "can_auto_consume_handoffs": policy.can_auto_consume_handoffs,
            }
        )
        self.development_memory.record_event(event)

        return True, f"Policy registered for agent {policy.agent_id}"

    def execute_auto_sync(
        self,
        agent_id: str,
        resource: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Autonomously sync a stale context.

        Returns: (success, message, workflow_id)
        """
        # Check policy
        policy = self.agent_policies.get(agent_id)
        if not policy or not policy.enabled:
            return False, "Agent policy not found or disabled", None

        if not policy.can_auto_sync:
            return False, "Agent not authorized for auto-sync", None

        # Create workflow
        import uuid
        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        workflow = AutonomousWorkflow(
            workflow_id=workflow_id,
            agent_id=agent_id,
            resource=resource,
            workflow_type="sync",
            trigger="manual"
        )

        self.active_workflows[workflow_id] = workflow
        workflow.status = "EXECUTING"
        workflow.started_at = datetime.now().isoformat()

        try:
            # Attempt sync
            success, message = self.context_invalidation_engine.sync_context(resource)

            if success:
                workflow.steps_executed.append({
                    "step": "sync",
                    "status": "completed",
                    "message": message
                })
                workflow.status = "COMPLETED"
            else:
                workflow.steps_executed.append({
                    "step": "sync",
                    "status": "failed",
                    "message": message
                })
                workflow.status = "FAILED"
                workflow.error_message = message

        except Exception as e:
            workflow.status = "FAILED"
            workflow.error_message = str(e)
            workflow.steps_executed.append({
                "step": "sync",
                "status": "error",
                "message": str(e)
            })

        workflow.completed_at = datetime.now().isoformat()
        self.workflow_history.append(workflow)

        return workflow.status == "COMPLETED", workflow.steps_executed[-1]["message"], workflow_id

    def execute_auto_revalidate(
        self,
        agent_id: str,
        resource: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Autonomously revalidate a synced context.

        Returns: (success, message, workflow_id)
        """
        # Check policy
        policy = self.agent_policies.get(agent_id)
        if not policy or not policy.enabled:
            return False, "Agent policy not found or disabled", None

        if not policy.can_auto_revalidate:
            return False, "Agent not authorized for auto-revalidate", None

        # Create workflow
        import uuid
        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        workflow = AutonomousWorkflow(
            workflow_id=workflow_id,
            agent_id=agent_id,
            resource=resource,
            workflow_type="revalidate",
            trigger="manual"
        )

        self.active_workflows[workflow_id] = workflow
        workflow.status = "EXECUTING"
        workflow.started_at = datetime.now().isoformat()

        try:
            # Attempt revalidate
            success, message, issues = self.context_invalidation_engine.revalidate_context(resource)

            workflow.steps_executed.append({
                "step": "revalidate",
                "status": "completed",
                "message": message,
                "issues_found": len(issues),
                "issues": issues
            })

            if success:
                workflow.status = "COMPLETED"
            else:
                workflow.status = "FAILED"
                workflow.error_message = f"Revalidation found issues: {issues}"

        except Exception as e:
            workflow.status = "FAILED"
            workflow.error_message = str(e)
            workflow.steps_executed.append({
                "step": "revalidate",
                "status": "error",
                "message": str(e)
            })

        workflow.completed_at = datetime.now().isoformat()
        self.workflow_history.append(workflow)

        return workflow.status == "COMPLETED", workflow.steps_executed[-1]["message"], workflow_id

    def execute_auto_consume_handoff(
        self,
        agent_id: str,
        handoff_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Autonomously consume a handoff and continue work.

        Returns: (success, message, workflow_id)
        """
        # Check policy
        policy = self.agent_policies.get(agent_id)
        if not policy or not policy.enabled:
            return False, "Agent policy not found or disabled", None

        if not policy.can_auto_consume_handoffs:
            return False, "Agent not authorized for auto-consume-handoffs", None

        # Find handoff
        handoff = self.temporal_handoff_engine._find_handoff_by_id(handoff_id)
        if not handoff:
            return False, f"Handoff {handoff_id} not found", None

        # Create workflow
        import uuid
        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        resource = handoff.resource
        workflow = AutonomousWorkflow(
            workflow_id=workflow_id,
            agent_id=agent_id,
            resource=resource,
            workflow_type="consume_handoff",
            trigger="handoff_available"
        )

        self.active_workflows[workflow_id] = workflow
        workflow.status = "EXECUTING"
        workflow.started_at = datetime.now().isoformat()

        try:
            # Consume handoff
            success, message = self.temporal_handoff_engine.consume_handoff(agent_id, handoff_id)

            workflow.steps_executed.append({
                "step": "consume_handoff",
                "status": "completed",
                "message": message,
                "handoff_id": handoff_id
            })

            if success:
                workflow.status = "COMPLETED"
                # Record workflow completion event
                event = Event(
                    event_type=EventType.WORK_STARTED,
                    actor=agent_id,
                    actor_type="agent",
                    resource=resource,
                    details={
                        "workflow_id": workflow_id,
                        "handoff_consumed": handoff_id,
                        "prior_actor": handoff.actor
                    }
                )
                self.development_memory.record_event(event)
            else:
                workflow.status = "FAILED"
                workflow.error_message = message

        except Exception as e:
            workflow.status = "FAILED"
            workflow.error_message = str(e)
            workflow.steps_executed.append({
                "step": "consume_handoff",
                "status": "error",
                "message": str(e)
            })

        workflow.completed_at = datetime.now().isoformat()
        self.workflow_history.append(workflow)

        return workflow.status == "COMPLETED", workflow.steps_executed[-1]["message"], workflow_id

    def execute_full_workflow_orchestration(
        self,
        agent_id: str,
        resource: str,
        include_sync: bool = True,
        include_revalidate: bool = True,
        include_consume_handoff: bool = False,
        handoff_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a full autonomous workflow orchestration.

        Orchestrates multiple steps:
        1. (Optional) Consume handoff if provided
        2. (Optional) Sync stale context
        3. (Optional) Revalidate context

        Returns: (success, message, workflow_id)
        """
        # Check policy
        policy = self.agent_policies.get(agent_id)
        if not policy or not policy.enabled:
            return False, "Agent policy not found or disabled", None

        # Create workflow
        import uuid
        workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        workflow = AutonomousWorkflow(
            workflow_id=workflow_id,
            agent_id=agent_id,
            resource=resource,
            workflow_type="full_orchestration",
            trigger="manual"
        )

        self.active_workflows[workflow_id] = workflow
        workflow.status = "EXECUTING"
        workflow.started_at = datetime.now().isoformat()

        try:
            # Step 1: Consume handoff if provided
            if include_consume_handoff and handoff_id:
                success, message = self.temporal_handoff_engine.consume_handoff(agent_id, handoff_id)
                workflow.steps_executed.append({
                    "step": "consume_handoff",
                    "status": "completed" if success else "failed",
                    "message": message
                })
                if not success and policy.rollback_on_failure:
                    workflow.status = "FAILED"
                    workflow.error_message = f"Handoff consumption failed: {message}"
                    raise Exception(workflow.error_message)

            # Step 2: Sync context
            if include_sync:
                success, message = self.context_invalidation_engine.sync_context(resource)
                workflow.steps_executed.append({
                    "step": "sync",
                    "status": "completed" if success else "failed",
                    "message": message
                })
                if not success and policy.rollback_on_failure:
                    workflow.status = "FAILED"
                    workflow.error_message = f"Context sync failed: {message}"
                    raise Exception(workflow.error_message)

            # Step 3: Revalidate context
            if include_revalidate:
                success, message, issues = self.context_invalidation_engine.revalidate_context(resource)
                workflow.steps_executed.append({
                    "step": "revalidate",
                    "status": "completed" if success else "partial",
                    "message": message,
                    "issues_found": len(issues),
                    "issues": issues
                })
                # Note: Don't fail on revalidation issues, just report them

            workflow.status = "COMPLETED"

        except Exception as e:
            workflow.status = "FAILED"
            workflow.error_message = str(e)
            if policy.rollback_on_failure:
                workflow.status = "ROLLED_BACK"

        workflow.completed_at = datetime.now().isoformat()
        self.workflow_history.append(workflow)

        return workflow.status == "COMPLETED", workflow.steps_executed[-1]["message"], workflow_id

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get status of a workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            return workflow.to_dict()

        # Check history
        for w in self.workflow_history:
            if w.workflow_id == workflow_id:
                return w.to_dict()

        return None

    def get_active_workflows(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get all active workflows, optionally filtered by agent"""
        workflows = []
        for workflow in self.active_workflows.values():
            if agent_id and workflow.agent_id != agent_id:
                continue
            workflows.append(workflow.to_dict())
        return workflows

    def get_workflow_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get workflow execution history"""
        workflows = []
        for workflow in self.workflow_history[-limit:]:
            if agent_id and workflow.agent_id != agent_id:
                continue
            workflows.append(workflow.to_dict())
        return workflows

    def disable_agent_autonomy(self, agent_id: str) -> Tuple[bool, str]:
        """Disable autonomy for an agent"""
        policy = self.agent_policies.get(agent_id)
        if not policy:
            return False, f"No policy found for agent {agent_id}"

        policy.enabled = False
        return True, f"Autonomy disabled for agent {agent_id}"

    def enable_agent_autonomy(self, agent_id: str) -> Tuple[bool, str]:
        """Enable autonomy for an agent"""
        policy = self.agent_policies.get(agent_id)
        if not policy:
            return False, f"No policy found for agent {agent_id}"

        policy.enabled = True
        return True, f"Autonomy enabled for agent {agent_id}"

    def clear(self):
        """Clear all workflows and policies"""
        self.agent_policies.clear()
        self.active_workflows.clear()
        self.workflow_history.clear()
