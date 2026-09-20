#!/usr/bin/env python3
"""
Neo 2.0 Phase 3: Context Invalidation Engine

Detects when developer's assumptions/context become stale
even when Git reports no conflict.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
try:
    from .event_model import Event, EventType
    from .development_memory import DevelopmentMemory
    from .dependency_graph import DependencyGraph, ContextSnapshot
except ImportError:
    from event_model import Event, EventType
    from development_memory import DevelopmentMemory
    from dependency_graph import DependencyGraph, ContextSnapshot


class ContextInvalidationEngine:
    """
    Detects and manages context invalidation.

    Key insight: A developer's code may merge cleanly, but their
    assumptions about dependencies/APIs may be stale.

    Example:
    - Dev A: assumes PaymentService.process() returns immediately
    - Dev B: changes it to async (added timeout behavior)
    - No Git conflict, but Dev A's context is now invalid
    """

    def __init__(
        self,
        development_memory: DevelopmentMemory,
        dependency_graph: DependencyGraph
    ):
        self.development_memory = development_memory
        self.dependency_graph = dependency_graph

        # Active context snapshots: resource -> snapshot
        self.active_contexts: Dict[str, ContextSnapshot] = {}

        # History of all snapshots
        self.snapshot_history: List[ContextSnapshot] = []

        # Stale contexts awaiting sync/revalidation
        self.stale_contexts: Dict[str, ContextSnapshot] = {}

    def create_context_snapshot(
        self,
        actor: str,
        actor_type: str,
        resource: str,
        base_commit: str,
        task_id: Optional[str] = None,
        files: Optional[List[str]] = None,
        symbols: Optional[List[str]] = None,
        assumptions: Optional[Dict[str, str]] = None,
        api_signatures: Optional[Dict[str, str]] = None,
        configuration: Optional[Dict[str, str]] = None,
    ) -> ContextSnapshot:
        """
        Create a context snapshot when developer starts work.

        Captures what the developer knows/assumes at this point.
        """
        snapshot = ContextSnapshot(
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            base_commit=base_commit,
            task_id=task_id,
        )

        snapshot.timestamp = datetime.now().isoformat()

        if files:
            snapshot.files_involved = set(files)
        if symbols:
            snapshot.symbols_involved = set(symbols)
        if assumptions:
            snapshot.assumptions = assumptions
        if api_signatures:
            snapshot.api_signatures = api_signatures
        if configuration:
            snapshot.configuration = configuration

        # Build dependency set from symbols
        for symbol in snapshot.symbols_involved:
            deps = self.dependency_graph.get_all_dependencies(symbol)
            snapshot.dependencies.update(deps)

        # Store snapshot
        self.active_contexts[resource] = snapshot
        self.snapshot_history.append(snapshot)

        # Record event
        event = Event(
            event_type=EventType.CONTEXT_SNAPSHOT_CREATED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
            details={
                "base_commit": base_commit,
                "files": list(snapshot.files_involved),
                "symbols": list(snapshot.symbols_involved),
                "dependencies": list(snapshot.dependencies),
            }
        )
        self.development_memory.record_event(event)

        return snapshot

    def mark_symbol_changed(self, symbol: str, changed_by: str, reason: str):
        """
        Record that a symbol was changed (by another developer).

        Triggers invalidation detection for affected contexts.
        """
        self.dependency_graph.mark_changed(symbol)

        # Find affected contexts
        affected = self._find_affected_contexts(symbol)

        for context in affected:
            self._invalidate_context(
                context=context,
                changed_by=changed_by,
                changed_symbol=symbol,
                reason=reason
            )

    def _find_affected_contexts(self, changed_symbol: str) -> List[ContextSnapshot]:
        """Find contexts affected by a symbol change."""
        affected = []

        for context in self.active_contexts.values():
            if context.status == "CURRENT":
                # Check if this context depends on changed symbol
                if changed_symbol in context.dependencies:
                    affected.append(context)

        return affected

    def _invalidate_context(
        self,
        context: ContextSnapshot,
        changed_by: str,
        changed_symbol: str,
        reason: str
    ):
        """Mark a context as stale."""
        context.status = "STALE"
        context.changed_dependencies.add(changed_symbol)
        context.invalidation_reasons.append(
            f"{changed_symbol} changed by {changed_by}: {reason}"
        )

        # Move to stale queue
        if context.resource not in self.stale_contexts:
            self.stale_contexts[context.resource] = context

        # Record event
        event = Event(
            event_type=EventType.CONTEXT_INVALIDATED,
            actor=context.actor,
            actor_type=context.actor_type,
            resource=context.resource,
            task_id=context.task_id,
            details={
                "changed_by": changed_by,
                "affected_symbol": changed_symbol,
                "reason": reason,
                "dependencies_affected": list(context.changed_dependencies),
            }
        )
        self.development_memory.record_event(event)

    def sync_context(self, resource: str) -> Tuple[bool, str]:
        """
        Sync a stale context with latest code.

        In a real implementation, this would:
        - Pull latest code
        - Re-analyze dependencies
        - Verify assumptions
        """
        if resource not in self.stale_contexts:
            return False, "Context not in stale queue"

        context = self.stale_contexts[resource]
        context.status = "SYNC_REQUIRED"

        event = Event(
            event_type=EventType.CONTEXT_SYNC_REQUIRED,
            actor=context.actor,
            actor_type=context.actor_type,
            resource=resource,
            task_id=context.task_id,
            details={"invalidation_reasons": context.invalidation_reasons}
        )
        self.development_memory.record_event(event)

        return True, "Context sync required"

    def revalidate_context(self, resource: str) -> Tuple[bool, str, List[str]]:
        """
        Revalidate a synced context.

        Returns: (success, message, issues_found)
        """
        if resource not in self.active_contexts:
            return False, "Context not found", []

        context = self.active_contexts[resource]
        issues = []

        # Simulate validation: check if changed dependencies break assumptions
        for changed_dep in context.changed_dependencies:
            # Check if dependency appears in assumptions
            for assumption_key, assumption_desc in context.assumptions.items():
                if changed_dep in assumption_desc:
                    issues.append(
                        f"Assumption '{assumption_key}' may be invalidated by {changed_dep}"
                    )

        if issues:
            context.status = "REVALIDATING"
            event = Event(
                event_type=EventType.CONTEXT_REVALIDATING,
                actor=context.actor,
                actor_type=context.actor_type,
                resource=resource,
                task_id=context.task_id,
                details={"validation_issues": issues}
            )
            self.development_memory.record_event(event)

            return False, "Context revalidation found issues", issues
        else:
            context.status = "REVALIDATED"
            context.changed_dependencies.clear()
            context.invalidation_reasons.clear()

            if resource in self.stale_contexts:
                del self.stale_contexts[resource]

            event = Event(
                event_type=EventType.CONTEXT_REVALIDATED,
                actor=context.actor,
                actor_type=context.actor_type,
                resource=resource,
                task_id=context.task_id
            )
            self.development_memory.record_event(event)

            return True, "Context revalidated successfully", []

    def get_context_status(self, resource: str) -> Optional[Dict]:
        """Get current status of a context."""
        context = self.active_contexts.get(resource)
        if not context:
            return None

        return {
            "resource": resource,
            "actor": context.actor,
            "status": context.status,
            "base_commit": context.base_commit,
            "files": list(context.files_involved),
            "symbols": list(context.symbols_involved),
            "dependencies": list(context.dependencies),
            "assumptions": context.assumptions,
            "invalidation_reasons": context.invalidation_reasons,
            "changed_dependencies": list(context.changed_dependencies),
        }

    def get_stale_contexts(self) -> List[Dict]:
        """Get all stale contexts awaiting sync/revalidation."""
        result = []
        for context in self.stale_contexts.values():
            result.append(self.get_context_status(context.resource))
        return result

    def get_context_revalidation_workflow(self, resource: str) -> Dict:
        """
        Get human-friendly revalidation workflow for a developer.
        """
        context = self.stale_contexts.get(resource)
        if not context:
            return {}

        return {
            "resource": resource,
            "status": "STALE_CONTEXT",
            "message": f"Your development context for {resource} is stale",
            "invalidation_reasons": context.invalidation_reasons,
            "changed_dependencies": list(context.changed_dependencies),
            "assumptions_affected": [
                (k, v) for k, v in context.assumptions.items()
                if any(dep in v for dep in context.changed_dependencies)
            ],
            "recommended_actions": [
                "SYNC: Pull latest code and dependencies",
                "REVIEW: Check changes in affected symbols",
                "VALIDATE: Verify your assumptions still hold",
                "PROCEED: Continue with your changes (at your own risk)",
            ],
            "workflow_steps": [
                {
                    "step": 1,
                    "action": "SYNC",
                    "description": "git fetch origin && git merge origin/main"
                },
                {
                    "step": 2,
                    "action": "REVIEW",
                    "description": f"Review changes in: {', '.join(context.changed_dependencies)}"
                },
                {
                    "step": 3,
                    "action": "VALIDATE",
                    "description": "Run tests and validate assumptions"
                },
                {
                    "step": 4,
                    "action": "REVALIDATE",
                    "description": "POST /api/revalidate_context"
                },
            ]
        }

    def clear(self):
        """Clear all contexts (for testing)."""
        self.active_contexts.clear()
        self.snapshot_history.clear()
        self.stale_contexts.clear()
