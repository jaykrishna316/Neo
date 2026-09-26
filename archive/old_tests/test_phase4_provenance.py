#!/usr/bin/env python3
"""
Test Neo 2.0 Phase 4: Reviewer Provenance Engine
Verifies reviewer candidate generation and relevance explanation
"""

import sys
from event_model import Event, EventType
from development_memory import DevelopmentMemory
from dependency_graph import DependencyGraph
from reviewer_provenance_engine import ReviewerProvenanceEngine


def test_provenance_graph_building():
    """Test building provenance graphs from events"""
    print("\n✓ Test: Provenance Graph Building")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Simulate developer activities
    memory.record_event(Event(
        event_type=EventType.DEVELOPER_REGISTERED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::charge",
    ))

    memory.record_event(Event(
        event_type=EventType.RESOURCE_CLAIMED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::charge",
        task_id="JIRA-100",
    ))

    memory.record_event(Event(
        event_type=EventType.WORK_COMPLETED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::charge",
        task_id="JIRA-100",
    ))

    # Build provenance
    provenance = engine.build_provenance_graph("payment.py::charge")

    assert "dev1" in provenance
    assert provenance["dev1"].involvement_count == 3
    assert len(provenance["dev1"].direct_modifications) > 0
    assert provenance["dev1"].relevance_score > 0

    print(f"  Provenance nodes: {list(provenance.keys())}")
    print(f"  Dev1 involvement: {provenance['dev1'].involvement_count}")
    print(f"  Dev1 relevance: {provenance['dev1'].relevance_score:.2f}")


def test_reviewer_candidate_generation():
    """Test generating reviewer candidates"""
    print("\n✓ Test: Reviewer Candidate Generation")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Multiple developers with different involvement levels
    for i in range(1, 4):
        for j in range(i):  # Dev1: 3 events, Dev2: 2, Dev3: 1
            memory.record_event(Event(
                event_type=EventType.RESOURCE_CLAIMED,
                actor=f"dev{i}",
                actor_type="human",
                resource="order.py::process",
                task_id=f"JIRA-{i*10 + j}",
            ))

    # Get candidates
    candidates = engine.get_reviewer_provenance("order.py::process")

    assert len(candidates) > 0
    assert candidates[0].relevance_score > candidates[-1].relevance_score
    assert all(hasattr(c, 'relevance_reasons') for c in candidates)

    print(f"  Total candidates: {len(candidates)}")
    for i, c in enumerate(candidates[:3]):
        print(f"  Candidate {i+1}: {c.actor} (score: {c.relevance_score:.2f})")


def test_exclude_author():
    """Test excluding change author from candidates"""
    print("\n✓ Test: Exclude Change Author")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Create events for multiple devs
    for actor in ["dev1", "dev2", "dev3"]:
        memory.record_event(Event(
            event_type=EventType.RESOURCE_CLAIMED,
            actor=actor,
            actor_type="human",
            resource="service.py::query",
            task_id=f"JIRA-{actor}",
        ))

    # Get candidates excluding dev1
    candidates = engine.get_reviewer_provenance(
        "service.py::query",
        exclude_author="dev1"
    )

    assert all(c.actor != "dev1" for c in candidates)

    print(f"  Candidates (excluding dev1): {[c.actor for c in candidates]}")


def test_relevance_explanation():
    """Test getting detailed relevance explanation"""
    print("\n✓ Test: Relevance Explanation")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Create rich event history
    memory.record_event(Event(
        event_type=EventType.RESOURCE_CLAIMED,
        actor="dev1",
        actor_type="human",
        resource="auth.py::validate",
        task_id="JIRA-100",
    ))

    memory.record_event(Event(
        event_type=EventType.CONTEXT_INVALIDATED,
        actor="dev2",
        actor_type="human",
        resource="auth.py::validate",
        task_id="JIRA-101",
        details={"affected_symbol": "db.py::lookup"},
    ))

    memory.record_event(Event(
        event_type=EventType.WORK_COMPLETED,
        actor="dev1",
        actor_type="human",
        resource="auth.py::validate",
        task_id="JIRA-100",
    ))

    # Get explanation
    explanation = engine.explain_reviewer_relevance("auth.py::validate", "dev1")

    assert explanation is not None
    assert explanation["actor"] == "dev1"
    assert explanation["relevance_score"] > 0
    assert "participation_evidence" in explanation
    assert len(explanation["explanation"]["modification_tasks"]) > 0

    print(f"  Actor: {explanation['actor']}")
    print(f"  Relevance Score: {explanation['relevance_score']:.2f}")
    print(f"  Evidence: {explanation['participation_evidence'][:2]}")


def test_cross_resource_reviewers():
    """Test finding reviewers across multiple resources"""
    print("\n✓ Test: Cross-Resource Reviewers")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Create participation across multiple resources
    resources = ["auth.py::validate", "db.py::query", "api.py::endpoint"]

    participation = {
        "dev1": [True, True, False],    # 2 resources
        "dev2": [True, True, True],     # 3 resources (best candidate)
        "dev3": [False, True, False],   # 1 resource
    }

    for resource_idx, resource in enumerate(resources):
        for actor, has_involvement in [(a, p[resource_idx]) for a, p in participation.items()]:
            if has_involvement:
                memory.record_event(Event(
                    event_type=EventType.RESOURCE_CLAIMED,
                    actor=actor,
                    actor_type="human",
                    resource=resource,
                    task_id=f"JIRA-{actor}-{resource_idx}",
                ))

    # Get cross-resource reviewers
    candidates = engine.get_cross_resource_reviewers(resources, min_participation=2)

    assert len(candidates) > 0
    assert candidates[0].actor == "dev2"  # Should be highest
    assert all(c.relevance_score > 0 for c in candidates)

    print(f"  Cross-resource candidates: {[c.actor for c in candidates]}")
    print(f"  Top candidate: {candidates[0].actor}")


def test_git_history_correlation():
    """Test correlating with Git history"""
    print("\n✓ Test: Git History Correlation")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Create Neo provenance
    memory.record_event(Event(
        event_type=EventType.WORK_COMPLETED,
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        task_id="JIRA-100",
    ))

    # Simulate Git history
    git_commits = [
        {"author": "dev1", "message": "Initial commit", "timestamp": "2026-09-09", "hash": "abc123"},
        {"author": "dev2", "message": "Added optimization", "timestamp": "2026-09-10", "hash": "def456"},
        {"author": "dev1", "message": "Bug fix", "timestamp": "2026-09-11", "hash": "ghi789"},
    ]

    correlation = engine.correlate_with_git_history("service.py::query", git_commits)

    assert correlation["resource"] == "service.py::query"
    assert "dev1" in correlation["overlap"]
    assert "dev2" in correlation["git_only"]
    assert len(correlation["detailed"]) > 0

    print(f"  Neo participants: {correlation['neo_participants']}")
    print(f"  Git authors: {correlation['git_authors']}")
    print(f"  Overlap: {correlation['overlap']}")


def test_multiple_involvement_types():
    """Test handling multiple types of involvement"""
    print("\n✓ Test: Multiple Involvement Types")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ReviewerProvenanceEngine(memory, graph)

    # Dev with multiple types of involvement
    memory.record_event(Event(
        event_type=EventType.RESOURCE_CLAIMED,
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        task_id="JIRA-100",
    ))

    memory.record_event(Event(
        event_type=EventType.CONTEXT_INVALIDATED,
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        task_id="JIRA-101",
        details={"affected_symbol": "dataset.py::load"},
    ))

    memory.record_event(Event(
        event_type=EventType.HANDOFF_CREATED,
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        task_id="JIRA-100",
    ))

    candidates = engine.get_reviewer_provenance("ml.py::train")

    assert len(candidates) > 0
    candidate = candidates[0]
    assert candidate.participation_metrics["direct_modifications"] > 0
    assert len(candidate.relevance_reasons) > 0

    print(f"  Candidate: {candidate.actor}")
    print(f"  Modification count: {candidate.participation_metrics['direct_modifications']}")
    print(f"  Dependency changes: {candidate.participation_metrics['dependency_changes']}")
    print(f"  Reasons: {candidate.relevance_reasons}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo 2.0 Phase 4 Tests: Reviewer Provenance Engine")
    print("=" * 60)

    try:
        test_provenance_graph_building()
        test_reviewer_candidate_generation()
        test_exclude_author()
        test_relevance_explanation()
        test_cross_resource_reviewers()
        test_git_history_correlation()
        test_multiple_involvement_types()

        print("\n" + "=" * 60)
        print("✓ All Phase 4 tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
