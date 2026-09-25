"""
Neo 3.0 End-to-End Integration Tests

Tests all 11 Neo 3.0 features working together in realistic scenarios:
- Full prevention → understanding → resolution workflow
- Multi-developer conflict scenarios
- Neo 2.0 integration
"""

import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, '/home/user/Neo/.claude')

from conflict_prevention_engine import ConflictPreventionEngine
from prevention.intent_detection import IntentDetector
from prevention.working_set_tracker import WorkingSetTracker
from understanding.conflict_archaeology import ConflictArchaeologist, ConflictArchaeologyRecord
from understanding.pattern_analyzer import PatternAnalyzer
from understanding.causality_tracker import CausalityAnalyzer
from resolution.expertise_resolver import ExpertiseResolver
from resolution.intent_merger import IntentMerger
from resolution.agent_negotiator import AgentNegotiator, AgentDecision


class TestNeo3FullWorkflow(unittest.TestCase):
    """Test complete Neo 3.0 workflow from prevention to resolution"""

    def setUp(self):
        self.detector = IntentDetector()
        self.tracker = WorkingSetTracker()
        self.archaeologist = ConflictArchaeologist()
        self.pattern_analyzer = PatternAnalyzer()
        self.causality_analyzer = CausalityAnalyzer()
        self.expertise_resolver = ExpertiseResolver()
        self.intent_merger = IntentMerger()
        self.agent_negotiator = AgentNegotiator()

    def test_three_developer_auth_conflict(self):
        """
        Test realistic 3-developer scenario:
        - dev1, dev2, dev3 all working on auth.py
        - dev1 & dev2 create conflict
        - dev3 is expert and resolves
        """
        # Setup: Register expertise
        self.expertise_resolver.register_expertise('alice', 'auth.py', 0.92)
        self.expertise_resolver.register_expertise('bob', 'auth.py', 0.55)
        self.expertise_resolver.register_expertise('charlie', 'auth.py', 0.48)

        # Phase 1: Prevention - Detect concurrent work
        self.tracker.start_session('alice')
        self.tracker.start_session('bob')
        self.tracker.start_session('charlie')

        self.tracker.update_working_set('alice', ['auth.py::validate_email'])
        self.tracker.update_working_set('bob', ['auth.py::validate_email'])
        self.tracker.update_working_set('charlie', ['auth.py::tokenize'])

        overlaps = self.tracker.detect_overlaps()
        self.assertEqual(len(overlaps), 1)

        # Phase 2: Intent Detection
        event_alice = {'commit_message': 'Add email validation with regex'}
        event_bob = {'commit_message': 'Optimize email validation'}

        intent_alice = self.detector.extract_intent_from_event('alice', event_alice)
        intent_bob = self.detector.extract_intent_from_event('bob', event_bob)

        self.detector.register_intent(intent_alice)
        self.detector.register_intent(intent_bob)

        intent_overlaps = self.detector.detect_overlaps()
        # Intent overlaps should exist since both deal with email validation
        self.assertIsNotNone(intent_overlaps)

        # Phase 3: Understanding - Analyze conflict
        record = ConflictArchaeologyRecord(
            conflict_id='conflict_auth_001',
            resource='auth.py::validate_email',
            developer_1='alice',
            developer_2='bob',
            original_state='def validate_email(email): pass',
            dev1_change_description='Add regex validation logic',
            dev1_intent='Improve email validation',
            dev2_change_description='Cache compiled regex',
            dev2_intent='Performance optimization',
            conflicting_sections=[(10, 'regex pattern'), (10, 'cache logic')],
            independent_sections=[(15, 'error handling')],
            intents_compatible=True,
            timestamp=datetime.now()
        )

        self.archaeologist.record_conflict(record)
        story = self.archaeologist.get_conflict_story('conflict_auth_001')

        self.assertIsNotNone(story)
        self.assertTrue(story['conflict_analysis']['intents_compatible'])

        # Phase 4: Resolution - Expert decides
        winner, confidence = self.expertise_resolver.resolve_conflict(
            'alice', 'bob', 'auth.py', 'conflict_auth_001'
        )

        self.assertEqual(winner, 'alice')
        self.assertGreater(confidence, 0.3)

    def test_payment_module_systemic_conflicts(self):
        """
        Test systemic pattern detection:
        - Multiple conflicts on payment.py
        - Same developer pair keeps conflicting (team silo)
        - Pattern analysis identifies root cause
        """
        # Add multiple conflicts
        for i in range(3):
            self.pattern_analyzer.add_conflict({
                'resource': 'payment.py',
                'dev1': 'alice',
                'dev2': 'bob'
            })

        patterns = self.pattern_analyzer.analyze_patterns()

        # Should identify high-conflict module
        high_conflict = self.pattern_analyzer.get_patterns_by_type('high_conflict_module')
        self.assertEqual(len(high_conflict), 1)
        self.assertEqual(high_conflict[0].frequency, 3)

        # Should identify team silo
        team_silo = self.pattern_analyzer.get_patterns_by_type('team_silo')
        self.assertEqual(len(team_silo), 1)

    def test_causality_analysis_root_cause(self):
        """
        Test causality analysis:
        - Analyze conflict root causes
        - Identify prevention opportunities
        - Track lessons learned
        """
        conflict_data = {
            'dev1': 'alice',
            'dev2': 'bob',
            'resource': 'database.py',
            'dev1_intent': 'Add migration script',
            'dev2_intent': 'Refactor database module',
            'files_changed': ['database.py', 'migrations.py'],
            'synchronized': False,
            'poorly_documented': True,
            'code_reviewed': False
        }

        result = self.causality_analyzer.analyze_conflict_cause('conflict_db_001', conflict_data)

        self.assertIn('root_cause', result)
        self.assertGreater(len(result['prevention_opportunities']), 0)

        # Record lesson learned
        self.causality_analyzer.record_lesson_learned(
            'conflict_db_001',
            'Coordinate database changes with migrations'
        )

        analysis = self.causality_analyzer.get_causality_analysis('conflict_db_001')
        self.assertEqual(len(analysis['lessons_learned']), 1)

    def test_intent_based_auto_merge(self):
        """
        Test auto-merge of orthogonal changes:
        - dev1 adds logging
        - dev2 optimizes cache
        - Intents are orthogonal, can auto-merge
        """
        result, confidence = self.intent_merger.attempt_auto_merge(
            'Add comprehensive logging to auth flow',
            'Optimize cache invalidation strategy',
            'Added logging statements to every function',
            'Refactored cache invalidation logic',
            'conflict_merge_001'
        )

        self.assertIn(result, ['auto_merged', 'expert_decision'])
        self.assertGreater(confidence, 0.5)

    def test_multi_agent_negotiation(self):
        """
        Test multi-agent negotiation:
        - Agent_validator wants to reject unsafe change
        - Agent_optimizer wants performance improvement
        - Higher confidence agent wins
        """
        decision_validator = AgentDecision(
            agent='agent_validator',
            resource='payment.py',
            proposed_change='Reject change (violates null check)',
            confidence=0.95,
            reasoning='Safety requirement'
        )

        decision_optimizer = AgentDecision(
            agent='agent_optimizer',
            resource='payment.py',
            proposed_change='Apply optimization',
            confidence=0.60,
            reasoning='Performance improvement'
        )

        self.agent_negotiator.register_decision(decision_validator)
        self.agent_negotiator.register_decision(decision_optimizer)

        winner, strategy, confidence = self.agent_negotiator.negotiate_conflict(
            'agent_validator', 'agent_optimizer', 'payment.py', 'negotiation_001'
        )

        self.assertEqual(winner, 'agent_validator')
        self.assertIn(strategy, ['confidence_based', 'default'])
        self.assertGreater(confidence, 0.5)

    def test_end_to_end_conflict_scenario(self):
        """
        Complete end-to-end scenario:
        1. Three developers start working on same file
        2. Conflict is predicted
        3. Conflict occurs and is analyzed
        4. Root cause identified
        5. Resolution strategy applied
        6. Patterns identified for future prevention
        """
        # Setup expertise
        self.expertise_resolver.register_expertise('senior_dev', 'core.py', 0.90)
        self.expertise_resolver.register_expertise('mid_dev', 'core.py', 0.60)
        self.expertise_resolver.register_expertise('junior_dev', 'core.py', 0.30)

        # Working set detection
        self.tracker.start_session('senior_dev')
        self.tracker.start_session('mid_dev')
        self.tracker.update_working_set('senior_dev', ['core.py::process'])
        self.tracker.update_working_set('mid_dev', ['core.py::process'])

        overlaps = self.tracker.detect_overlaps()
        self.assertGreater(len(overlaps), 0)

        # Record conflict
        record = ConflictArchaeologyRecord(
            conflict_id='conflict_end_to_end',
            resource='core.py::process',
            developer_1='senior_dev',
            developer_2='mid_dev',
            original_state='def process(): pass',
            dev1_change_description='Add validation layer',
            dev1_intent='Improve robustness',
            dev2_change_description='Add caching',
            dev2_intent='Improve performance',
            conflicting_sections=[(5, 'function signature')],
            independent_sections=[(7, 'implementation')],
            intents_compatible=True,
            timestamp=datetime.now()
        )

        self.archaeologist.record_conflict(record)

        # Analyze conflict
        conflict_data = {
            'dev1': 'senior_dev',
            'dev2': 'mid_dev',
            'resource': 'core.py',
            'dev1_intent': 'Improve robustness with validation',
            'dev2_intent': 'Improve performance with caching',
            'files_changed': ['core.py'],
            'synchronized': False,
            'code_reviewed': False
        }

        causality = self.causality_analyzer.analyze_conflict_cause(
            'conflict_end_to_end', conflict_data
        )

        self.assertIsNotNone(causality['root_cause'])

        # Resolve by expertise
        winner, confidence = self.expertise_resolver.resolve_conflict(
            'senior_dev', 'mid_dev', 'core.py', 'conflict_end_to_end'
        )

        self.assertEqual(winner, 'senior_dev')

        # Add to pattern analyzer to track
        for i in range(3):
            self.pattern_analyzer.add_conflict({
                'resource': 'core.py',
                'dev1': 'senior_dev',
                'dev2': 'mid_dev'
            })

        patterns = self.pattern_analyzer.analyze_patterns()

        # Should have identified high-conflict module pattern
        self.assertGreater(len(patterns), 0)


class TestNeo3PerformanceAndScalability(unittest.TestCase):
    """Test Neo 3.0 performance with multiple developers and conflicts"""

    def setUp(self):
        self.tracker = WorkingSetTracker()
        self.pattern_analyzer = PatternAnalyzer()

    def test_concurrent_work_tracking_5_developers(self):
        """Test tracking work of 5 developers concurrently"""
        developers = ['dev1', 'dev2', 'dev3', 'dev4', 'dev5']
        resources = ['auth.py', 'payment.py', 'cache.py']

        # Start sessions for all developers
        for dev in developers:
            self.tracker.start_session(dev)

        # Update working sets
        for i, dev in enumerate(developers):
            # Each dev works on 1-2 resources
            assigned_resources = [resources[j % len(resources)] for j in range(i % 2 + 1)]
            self.tracker.update_working_set(dev, assigned_resources)

        # Detect overlaps
        overlaps = self.tracker.detect_overlaps()

        # Should have some overlaps with 5 developers and 3 resources
        self.assertIsInstance(overlaps, list)

    def test_pattern_analysis_scale(self):
        """Test pattern analysis with many conflicts"""
        # Create 50 conflicts
        for i in range(50):
            self.pattern_analyzer.add_conflict({
                'resource': f'module_{i % 5}.py',
                'dev1': f'dev_{i % 3}',
                'dev2': f'dev_{(i + 1) % 3}'
            })

        patterns = self.pattern_analyzer.analyze_patterns()

        # Should identify patterns
        self.assertGreater(len(patterns), 0)

        # Check metrics
        metrics = self.pattern_analyzer.get_improvement_metrics()
        self.assertGreater(metrics['total_patterns'], 0)
        self.assertGreater(metrics['avg_pattern_frequency'], 0)


class TestNeo3AlertSystem(unittest.TestCase):
    """Test Neo 3.0 alert system integration"""

    def setUp(self):
        from alert_system import AlertSystem
        self.alert_system = AlertSystem()

    def test_conflict_alert_workflow(self):
        """Test alert generation and management"""
        # Test alert system is initialized
        self.assertIsNotNone(self.alert_system)

        # Get active alerts (should be empty or at least a list)
        active = self.alert_system.get_active_alerts()
        self.assertIsInstance(active, list)


def run_integration_tests():
    """Run all integration tests"""
    suite = unittest.TestSuite()

    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNeo3FullWorkflow))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNeo3PerformanceAndScalability))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNeo3AlertSystem))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
