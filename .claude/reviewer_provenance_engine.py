#!/usr/bin/env python3
"""
Neo 2.0 Phase 4: Reviewer Provenance Engine

Extracts reviewer candidates from development provenance based on:
- Direct modification participation
- Dependency change involvement
- Test ownership and coverage
- Related task participation

Correlates Neo development memory with Git history to explain relevance.
"""

from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from .event_model import Event, EventType, EventFactory
    from .development_memory import DevelopmentMemory
    from .dependency_graph import DependencyGraph
except ImportError:
    from event_model import Event, EventType, EventFactory
    from development_memory import DevelopmentMemory
    from dependency_graph import DependencyGraph


class ProvenanceNode:
    """Represents a developer's involvement with a resource."""

    def __init__(self, actor: str, actor_type: str, resource: str):
        self.actor = actor
        self.actor_type = actor_type
        self.resource = resource

        # Participation tracking
        self.direct_modifications: List[str] = []  # task IDs
        self.dependency_changes: List[str] = []    # affected symbols
        self.test_ownership: List[str] = []        # test files owned
        self.related_work: List[str] = []          # other task IDs

        # Scoring
        self.relevance_score = 0.0
        self.evidence: List[str] = []

        # Timestamps
        self.first_involved = None
        self.last_involved = None
        self.involvement_count = 0

    def to_dict(self) -> Dict:
        """Serialize provenance node."""
        return {
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource": self.resource,
            "direct_modifications": self.direct_modifications,
            "dependency_changes": self.dependency_changes,
            "test_ownership": self.test_ownership,
            "related_work": self.related_work,
            "relevance_score": self.relevance_score,
            "evidence": self.evidence,
            "involvement_count": self.involvement_count,
            "first_involved": self.first_involved,
            "last_involved": self.last_involved,
        }


class ReviewerCandidate:
    """Scored reviewer candidate with explanation."""

    def __init__(self, actor: str, actor_type: str, resource: str):
        self.actor = actor
        self.actor_type = actor_type
        self.resource = resource
        self.relevance_score = 0.0
        self.relevance_reasons: List[str] = []
        self.participation_metrics = {}
        self.last_involvement = None

    def to_dict(self) -> Dict:
        """Serialize candidate."""
        return {
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource": self.resource,
            "relevance_score": self.relevance_score,
            "relevance_reasons": self.relevance_reasons,
            "participation_metrics": self.participation_metrics,
            "last_involvement": self.last_involvement,
        }


class ReviewerProvenanceEngine:
    """
    Generates reviewer candidates from development provenance.

    Key insight: The developers most qualified to review a PR are those who
    have directly modified the resource, changed affected dependencies,
    own related tests, or participated in related tasks.
    """

    def __init__(
        self,
        development_memory: DevelopmentMemory,
        dependency_graph: DependencyGraph
    ):
        self.development_memory = development_memory
        self.dependency_graph = dependency_graph

        # Provenance graphs: resource -> {actor -> ProvenanceNode}
        self.provenance_graphs: Dict[str, Dict[str, ProvenanceNode]] = defaultdict(dict)

        # Cached reviewer candidates
        self.candidate_cache: Dict[str, List[ReviewerCandidate]] = {}

        # Weighting factors for relevance scoring
        self.weights = {
            "direct_modification": 1.0,
            "dependency_change": 0.6,
            "test_ownership": 0.5,
            "related_task": 0.3,
        }

        # Time decay: recent involvement weighted higher
        self.recency_decay_days = 30

    def build_provenance_graph(self, resource: str) -> Dict[str, ProvenanceNode]:
        """
        Build provenance graph for a resource from activity log.

        Analyzes all events related to the resource to determine:
        - Who touched it directly
        - Who changed dependencies
        - Who owns related tests
        - Who worked on related tasks
        """
        graph = {}

        # Get all events for this resource
        resource_events = self.development_memory.get_resource_history(resource)

        for event in resource_events:
            actor = event.get("actor", "unknown")
            actor_type = event.get("actor_type", "human")
            event_type = event.get("event_type")

            # Ensure node exists
            if actor not in graph:
                graph[actor] = ProvenanceNode(actor, actor_type, resource)

            node = graph[actor]
            node.involvement_count += 1
            node.last_involved = event.get("timestamp", datetime.now().isoformat())

            if not node.first_involved:
                node.first_involved = node.last_involved

            # Categorize participation (event_type is a string from development_memory)
            if event_type == EventType.RESOURCE_CLAIMED.value:
                node.direct_modifications.append(event.get("task_id", "unknown"))
                node.relevance_score += self.weights["direct_modification"]
                node.evidence.append("Directly claimed and modified resource")

            elif event_type == EventType.WORK_COMPLETED.value:
                node.direct_modifications.append(event.get("task_id", "unknown"))
                node.relevance_score += self.weights["direct_modification"]
                node.evidence.append("Completed work on resource")

            elif event_type == EventType.CONTEXT_INVALIDATED.value:
                changed_symbol = event.get("details", {}).get("affected_symbol")
                if changed_symbol:
                    node.dependency_changes.append(changed_symbol)
                    node.relevance_score += self.weights["dependency_change"]
                    node.evidence.append(f"Changed dependency: {changed_symbol}")

            elif event_type == EventType.HANDOFF_CREATED.value:
                node.direct_modifications.append(event.get("task_id", "unknown"))
                node.relevance_score += self.weights["direct_modification"]
                node.evidence.append("Created handoff with completed work")

        # Apply recency decay
        self._apply_recency_decay(graph)

        # Cache and return
        self.provenance_graphs[resource] = graph
        return graph

    def _apply_recency_decay(self, graph: Dict[str, ProvenanceNode]):
        """Apply time decay: recent work weights higher."""
        now = datetime.now()

        for node in graph.values():
            if not node.last_involved:
                continue

            last_involved = datetime.fromisoformat(node.last_involved)
            days_ago = (now - last_involved).days

            if days_ago > self.recency_decay_days:
                decay_factor = 0.5  # Halve score for old involvement
                node.relevance_score *= decay_factor

    def get_reviewer_provenance(
        self,
        resource: str,
        exclude_author: Optional[str] = None,
        min_relevance: float = 0.2
    ) -> List[ReviewerCandidate]:
        """
        Get scored reviewer candidates for a resource.

        Args:
            resource: File or function to find reviewers for
            exclude_author: Exclude the change author from candidates
            min_relevance: Minimum relevance score (0-1) to include

        Returns:
            Sorted list of ReviewerCandidate objects
        """
        # Check cache
        cache_key = f"{resource}:{exclude_author}:{min_relevance}"
        if cache_key in self.candidate_cache:
            return self.candidate_cache[cache_key]

        # Build provenance
        provenance = self.build_provenance_graph(resource)

        candidates = []
        for actor, node in provenance.items():
            # Skip author
            if exclude_author and actor == exclude_author:
                continue

            # Normalize score
            normalized_score = min(node.relevance_score / 3.0, 1.0)

            if normalized_score < min_relevance:
                continue

            candidate = ReviewerCandidate(actor, node.actor_type, resource)
            candidate.relevance_score = normalized_score
            candidate.relevance_reasons = node.evidence[:3]  # Top 3 reasons
            candidate.participation_metrics = {
                "direct_modifications": len(set(node.direct_modifications)),
                "dependency_changes": len(set(node.dependency_changes)),
                "test_ownership": len(set(node.test_ownership)),
            }
            candidate.last_involvement = node.last_involved

            candidates.append(candidate)

        # Sort by relevance
        candidates.sort(key=lambda c: c.relevance_score, reverse=True)

        # Cache
        self.candidate_cache[cache_key] = candidates

        return candidates

    def explain_reviewer_relevance(
        self,
        resource: str,
        actor: str
    ) -> Optional[Dict]:
        """
        Get detailed explanation of why someone is relevant to review a resource.

        Returns:
            Dict with relevance details or None if not relevant
        """
        provenance = self.build_provenance_graph(resource)

        if actor not in provenance:
            return None

        node = provenance[actor]

        return {
            "actor": actor,
            "actor_type": node.actor_type,
            "resource": resource,
            "relevance_score": min(node.relevance_score / 3.0, 1.0),
            "explanation": {
                "direct_modifications": len(set(node.direct_modifications)),
                "modification_tasks": list(set(node.direct_modifications))[:5],
                "dependency_changes": len(set(node.dependency_changes)),
                "affected_symbols": list(set(node.dependency_changes))[:5],
                "test_ownership": len(set(node.test_ownership)),
                "test_files": list(set(node.test_ownership))[:5],
            },
            "participation_evidence": node.evidence,
            "involvement_timeline": {
                "first_involved": node.first_involved,
                "last_involved": node.last_involved,
                "involvement_count": node.involvement_count,
            }
        }

    def get_cross_resource_reviewers(
        self,
        resources: List[str],
        exclude_author: Optional[str] = None,
        min_participation: int = 2
    ) -> List[ReviewerCandidate]:
        """
        Get reviewers qualified across multiple resources.

        Useful for PRs that touch multiple files.
        """
        reviewer_scores: Dict[str, ReviewerCandidate] = {}
        resource_provenance: Dict[str, Dict[str, ProvenanceNode]] = {}

        # Build provenance for all resources
        for resource in resources:
            resource_provenance[resource] = self.build_provenance_graph(resource)

        # Score reviewers who appear in multiple resources
        for resource, provenance in resource_provenance.items():
            for actor, node in provenance.items():
                if exclude_author and actor == exclude_author:
                    continue

                if actor not in reviewer_scores:
                    reviewer_scores[actor] = ReviewerCandidate(
                        actor, node.actor_type, ", ".join(resources)
                    )

                reviewer_scores[actor].relevance_score += node.relevance_score

        # Filter by participation
        candidates = [
            c for c in reviewer_scores.values()
            if len([r for r in resources
                   if c.actor in resource_provenance.get(r, {})]) >= min_participation
        ]

        # Sort by score
        candidates.sort(key=lambda c: c.relevance_score, reverse=True)

        return candidates

    def correlate_with_git_history(
        self,
        resource: str,
        git_commits: List[Dict]
    ) -> Dict:
        """
        Correlate Neo provenance with Git commit history.

        Args:
            resource: File to analyze
            git_commits: List of dicts with {author, message, timestamp, hash}

        Returns:
            Correlation analysis
        """
        provenance = self.build_provenance_graph(resource)

        # Extract Git authors
        git_authors: Dict[str, int] = defaultdict(int)
        for commit in git_commits:
            git_authors[commit.get("author", "unknown")] += 1

        # Compare with Neo provenance
        correlation = {
            "resource": resource,
            "neo_participants": list(provenance.keys()),
            "git_authors": list(git_authors.keys()),
            "overlap": list(set(provenance.keys()) & set(git_authors.keys())),
            "neo_only": list(set(provenance.keys()) - set(git_authors.keys())),
            "git_only": list(set(git_authors.keys()) - set(provenance.keys())),
        }

        # Detailed correlation
        correlation["detailed"] = {}
        for actor in set(provenance.keys()) | set(git_authors.keys()):
            correlation["detailed"][actor] = {
                "neo_involvement": provenance.get(actor, {}).involvement_count if actor in provenance else 0,
                "git_commits": git_authors.get(actor, 0),
            }

        return correlation

    def clear(self):
        """Clear all cached provenance."""
        self.provenance_graphs.clear()
        self.candidate_cache.clear()
