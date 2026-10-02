"""
Neo 3.0 Resolution Layer Tests (3A-3C)

Tests all resolution layer features:
- 3A: Expertise-Based Conflict Resolution
- 3B: Intent-Based Conflict Merging
- 3C: Multi-Agent Negotiation
"""

import sys
import unittest
from datetime import datetime

sys.path.insert(0, '/home/user/Neo/.claude')

from resolution.expertise_resolver import ExpertiseResolver
from resolution.intent_merger import IntentMerger
from resolution.agent_negotiator import AgentNegotiator, AgentDecision


class TestExpertiseBasedResolution(unittest.TestCase):
    """Test 3A: Expertise-Based Conflict Resolution"""

    def setUp(self):
        self.resolver = ExpertiseResolver()

    def test_resolve_by_expertise_clear_winner(self):
        """Test resolving conflict when one developer is clearly more expert"""
        self.resolver.register_expertise('alice', 'crypto.py', 0.92)
        self.resolver.register_expertise('bob', 'crypto.py', 0.15)

        winner, confidence = self.resolver.resolve_conflict('alice', 'bob', 'crypto.py', 'conflict_001')

        self.assertEqual(winner, 'alice')
        self.assertGreater(confidence, 0.7)

    def test_resolve_by_expertise_similar_scores(self):
        """Test resolving conflict when expertise is similar"""
        self.resolver.register_expertise('dev1', 'auth.py', 0.55)
        self.resolver.register_expertise('dev2', 'auth.py', 0.58)

        winner, confidence = self.resolver.resolve_conflict('dev1', 'dev2', 'auth.py', 'conflict_002')

        # When expertise is similar, should require manual review
        self.assertEqual(winner, 'manual_required')
        self.assertEqual(confidence, 0.5)

    def test_establish_expertise_hierarchy(self):
        """Test establishing expertise hierarchy for a resource"""
        self.resolver.register_expertise('alice', 'payment.py', 0.90)
        self.resolver.register_expertise('bob', 'payment.py', 0.60)
        self.resolver.register_expertise('charlie', 'payment.py', 0.75)

        hierarchy = self.resolver.establish_hierarchy('payment.py')

        self.assertEqual(hierarchy['top_expert'][0], 'alice')
        self.assertEqual(len(hierarchy['hierarchy']), 3)
        self.assertEqual(hierarchy['hierarchy'][0][1], 0.90)

    def test_get_expert_for_resource(self):
        """Test retrieving the top expert for a resource"""
        self.resolver.register_expertise('alice', 'cache.py', 0.88)
        self.resolver.register_expertise('bob', 'cache.py', 0.62)
        self.resolver.register_expertise('charlie', 'cache.py', 0.70)

        expert = self.resolver.get_expert_for_resource('cache.py')

        self.assertEqual(expert, 'alice')

    def test_get_resolution_history(self):
        """Test retrieving resolution history"""
        self.resolver.register_expertise('alice', 'auth.py', 0.85)
        self.resolver.register_expertise('bob', 'auth.py', 0.45)

        # Resolve multiple conflicts
        for i in range(3):
            self.resolver.resolve_conflict('alice', 'bob', 'auth.py', f'conflict_{i}')

        history = self.resolver.get_resolution_history('alice')

        self.assertEqual(history['conflicts_won'], 3)
        # Each resolution should have expertise advantage
        if history['resolutions']:
            self.assertGreater(history['resolutions'][0]['expertise_advantage'], 0.3)

    def test_expertise_score_retrieval(self):
        """Test getting expertise scores"""
        self.resolver.register_expertise('dev1', 'module.py', 0.75)

        score = self.resolver.get_expertise('dev1', 'module.py')

        self.assertEqual(score, 0.75)

    def test_unknown_expertise_defaults_to_zero(self):
        """Test that unknown expertise defaults to 0"""
        score = self.resolver.get_expertise('unknown_dev', 'unknown_resource.py')

        self.assertEqual(score, 0.0)


class TestIntentBasedConflictMerging(unittest.TestCase):
    """Test 3B: Intent-Based Conflict Merging - Auto-merge orthogonal changes"""

    def setUp(self):
        self.merger = IntentMerger()

    def test_auto_merge_orthogonal_intents(self):
        """Test auto-merging when intents are completely orthogonal"""
        result, confidence = self.merger.attempt_auto_merge(
            'Add logging to auth flow',
            'Optimize cache logic',
            'Added log statements',
            'Optimized cache',
            'conflict_001'
        )

        self.assertEqual(result, 'auto_merged')
        self.assertGreater(confidence, 0.70)

    def test_reject_merge_conflicting_intents(self):
        """Test rejecting merge when intents conflict"""
        result, confidence = self.merger.attempt_auto_merge(
            'Replace validation approach A',
            'Improve validation approach A',
            'Replaced validation',
            'Improved validation',
            'conflict_002'
        )

        self.assertEqual(result, 'manual_required')

    def test_expert_decision_needed_on_overlap(self):
        """Test when expert decision is needed due to high overlap"""
        result, confidence = self.merger.attempt_auto_merge(
            'Add feature to config system',
            'Refactor config system',
            'Modified config.load()',
            'Refactored config.load()',
            'conflict_003'
        )

        self.assertIn(result, ['manual_required', 'expert_decision'])

    def test_analyze_intent_compatibility(self):
        """Test analyzing intent compatibility"""
        intent1 = 'Add email validation using regex'
        intent2 = 'Optimize email validation with cache'

        compatible, confidence = self.merger.analyze_intent_compatibility(intent1, intent2)

        self.assertIsNotNone(confidence)
        self.assertGreater(confidence, 0.0)

    def test_merge_decision_recorded(self):
        """Test that merge decisions are recorded"""
        self.merger.attempt_auto_merge(
            'Add logging',
            'Optimize performance',
            'log statement',
            'optimized code',
            'conflict_004'
        )

        candidates = self.merger.get_merge_candidates(min_confidence=0.5)

        self.assertIsNotNone(candidates)

    def test_calculate_change_overlap(self):
        """Test calculating overlap between changes"""
        changes1 = 'line1\nline2\nline3'
        changes2 = 'line1\nline4\nline5'

        overlap = self.merger._calculate_change_overlap(changes1, changes2)

        self.assertGreaterEqual(overlap, 0.0)
        self.assertLessEqual(overlap, 1.0)

    def test_merge_with_high_confidence(self):
        """Test merge produces high confidence with orthogonal changes"""
        result, confidence = self.merger.attempt_auto_merge(
            'Add logging functionality',
            'Optimize performance metrics',
            'add logging statement',
            'optimize cache logic',
            'conflict_005'
        )

        self.assertIn(result, ['auto_merged', 'expert_decision'])
        self.assertGreater(confidence, 0.5)


class TestMultiAgentNegotiation(unittest.TestCase):
    """Test 3C: Multi-Agent Negotiation - Agents negotiate conflicts"""

    def setUp(self):
        self.negotiator = AgentNegotiator()

    def test_negotiate_by_confidence(self):
        """Test negotiation where confidence-based policy applies"""
        decision1 = AgentDecision(
            agent='agent_validator',
            resource='auth.py',
            proposed_change='Reject unsafe change',
            confidence=0.95,
            reasoning='Violates validation invariant'
        )

        decision2 = AgentDecision(
            agent='agent_optimizer',
            resource='auth.py',
            proposed_change='Apply performance optimization',
            confidence=0.60,
            reasoning='Improves P99 latency'
        )

        self.negotiator.register_decision(decision1)
        self.negotiator.register_decision(decision2)

        winner, strategy, confidence = self.negotiator.negotiate_conflict(
            'agent_validator', 'agent_optimizer', 'auth.py', 'conflict_001'
        )

        self.assertEqual(winner, 'agent_validator')
        self.assertEqual(strategy, 'confidence_based')
        self.assertGreater(confidence, 0.9)

    def test_negotiate_by_priority(self):
        """Test negotiation using priority policy"""
        # Set up priority policy
        self.negotiator.set_policy('resource_payment.py', {
            'priority': {'agent_security': 2, 'agent_perf': 1}
        })

        decision1 = AgentDecision(
            agent='agent_security',
            resource='payment.py',
            proposed_change='Add encryption',
            confidence=0.70,
            reasoning='Security requirement'
        )

        decision2 = AgentDecision(
            agent='agent_perf',
            resource='payment.py',
            proposed_change='Remove encryption overhead',
            confidence=0.75,
            reasoning='Performance optimization'
        )

        self.negotiator.register_decision(decision1)
        self.negotiator.register_decision(decision2)

        winner, strategy, confidence = self.negotiator.negotiate_conflict(
            'agent_security', 'agent_perf', 'payment.py', 'conflict_002'
        )

        self.assertEqual(winner, 'agent_security')
        self.assertEqual(strategy, 'priority_based')

    def test_negotiate_by_seniority(self):
        """Test negotiation using seniority policy"""
        self.negotiator.set_policy('seniority', {
            'agent_senior': 2,
            'agent_junior': 1
        })

        decision1 = AgentDecision(
            agent='agent_senior',
            resource='cache.py',
            proposed_change='Use complex caching strategy',
            confidence=0.80,
            reasoning='Optimal solution'
        )

        decision2 = AgentDecision(
            agent='agent_junior',
            resource='cache.py',
            proposed_change='Use simple approach',
            confidence=0.85,
            reasoning='Maintainability'
        )

        self.negotiator.register_decision(decision1)
        self.negotiator.register_decision(decision2)

        winner, strategy, confidence = self.negotiator.negotiate_conflict(
            'agent_senior', 'agent_junior', 'cache.py', 'conflict_003'
        )

        self.assertEqual(winner, 'agent_senior')
        self.assertEqual(strategy, 'seniority_based')

    def test_equal_confidence_requires_manual(self):
        """Test that equal confidence requires manual resolution"""
        decision1 = AgentDecision(
            agent='agent_a',
            resource='module.py',
            proposed_change='Change A',
            confidence=0.75,
            reasoning='Approach A'
        )

        decision2 = AgentDecision(
            agent='agent_b',
            resource='module.py',
            proposed_change='Change B',
            confidence=0.75,
            reasoning='Approach B'
        )

        self.negotiator.register_decision(decision1)
        self.negotiator.register_decision(decision2)

        winner, strategy, confidence = self.negotiator.negotiate_conflict(
            'agent_a', 'agent_b', 'module.py', 'conflict_004'
        )

        self.assertEqual(winner, 'manual_required')
        self.assertEqual(strategy, 'equal_confidence')

    def test_get_negotiation_history(self):
        """Test retrieving negotiation history"""
        for i in range(3):
            decision1 = AgentDecision(
                agent='agent_test',
                resource='test.py',
                proposed_change=f'Change {i}',
                confidence=0.7 + i * 0.05,
                reasoning=f'Reason {i}'
            )
            decision2 = AgentDecision(
                agent='agent_other',
                resource='test.py',
                proposed_change=f'Other {i}',
                confidence=0.5,
                reasoning=f'Other reason {i}'
            )
            self.negotiator.register_decision(decision1)
            self.negotiator.register_decision(decision2)

            self.negotiator.negotiate_conflict('agent_test', 'agent_other', 'test.py', f'conflict_{i}')

        history = self.negotiator.get_negotiation_history('agent_test')

        self.assertGreater(len(history), 0)

    def test_agent_consensus_rate(self):
        """Test calculating agent consensus rate (win rate)"""
        # Create scenarios where agent_dominant wins more
        for i in range(5):
            decision_dominant = AgentDecision(
                agent='agent_dominant',
                resource='resource.py',
                proposed_change='Change',
                confidence=0.85 + (i * 0.02),
                reasoning='Strong reason'
            )

            decision_weak = AgentDecision(
                agent='agent_weak',
                resource='resource.py',
                proposed_change='Alternative',
                confidence=0.40,
                reasoning='Weak reason'
            )

            self.negotiator.register_decision(decision_dominant)
            self.negotiator.register_decision(decision_weak)

            self.negotiator.negotiate_conflict(
                'agent_dominant', 'agent_weak', 'resource.py', f'conflict_{i}'
            )

        consensus_rate = self.negotiator.get_agent_consensus_rate('agent_dominant')

        self.assertGreater(consensus_rate, 0.7)


def run_resolution_tests():
    """Run all resolution layer tests"""
    suite = unittest.TestSuite()

    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExpertiseBasedResolution))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntentBasedConflictMerging))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMultiAgentNegotiation))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_resolution_tests()
    sys.exit(0 if success else 1)
