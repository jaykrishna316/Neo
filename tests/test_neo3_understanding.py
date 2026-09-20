"""
Neo 3.0 Understanding Layer Tests (2A-2C)

Tests all understanding layer features:
- 2A: Conflict Archaeology (conflict story reconstruction)
- 2B: Conflict Pattern Analysis (systemic pattern detection)
- 2C: Conflict Causality Tracking (root cause analysis)
"""

import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, '/home/user/Neo/.claude')

from understanding.conflict_archaeology import ConflictArchaeologist, ConflictArchaeologyRecord
from understanding.pattern_analyzer import PatternAnalyzer, ConflictPattern
from understanding.causality_tracker import CausalityAnalyzer


class TestConflictArchaeology(unittest.TestCase):
    """Test 2A: Conflict Archaeology - Reconstruct full conflict stories"""

    def setUp(self):
        self.archaeologist = ConflictArchaeologist()

    def test_record_and_retrieve_conflict(self):
        """Test recording and retrieving a conflict story"""
        record = ConflictArchaeologyRecord(
            conflict_id='conflict_001',
            resource='auth.py::validate_email',
            developer_1='dev1',
            developer_2='dev2',
            original_state='def validate_email(email): pass',
            dev1_change_description='Add email regex validation',
            dev1_intent='Improve email validation',
            dev2_change_description='Optimize with compiled cache',
            dev2_intent='Performance optimization',
            conflicting_sections=[(42, 'dev1: regex pattern'), (42, 'dev2: cache logic')],
            independent_sections=[(51, 'dev1: error handling')],
            intents_compatible=True,
            timestamp=datetime.now()
        )

        self.archaeologist.record_conflict(record)
        story = self.archaeologist.get_conflict_story('conflict_001')

        self.assertIsNotNone(story)
        self.assertEqual(story['resource'], 'auth.py::validate_email')
        self.assertEqual(story['developers'], ['dev1', 'dev2'])

    def test_compare_three_versions(self):
        """Test comparing original, dev1, dev2 versions"""
        record = ConflictArchaeologyRecord(
            conflict_id='conflict_002',
            resource='payment.py::process_payment',
            developer_1='alice',
            developer_2='bob',
            original_state='def process_payment(amount): return charge(amount)',
            dev1_change_description='Add validation before charge',
            dev1_intent='Add security check',
            dev2_change_description='Add logging to charge',
            dev2_intent='Add monitoring',
            conflicting_sections=[(5, 'both modify charge line')],
            independent_sections=[(3, 'alice adds validation'), (7, 'bob adds logging')],
            intents_compatible=True,
            timestamp=datetime.now()
        )

        self.archaeologist.record_conflict(record)
        comparison = self.archaeologist.compare_versions('conflict_002')

        self.assertIn('version_original', comparison)
        self.assertIn('version_dev1', comparison)
        self.assertIn('version_dev2', comparison)
        self.assertEqual(len(comparison['conflict_sections']), 1)

    def test_identify_learnable_conflicts(self):
        """Test identifying conflicts where compatible intents still conflicted"""
        record = ConflictArchaeologyRecord(
            conflict_id='conflict_003',
            resource='config.py',
            developer_1='charlie',
            developer_2='diana',
            original_state='CONFIG = {}',
            dev1_change_description='Add feature flag',
            dev1_intent='Enable new feature',
            dev2_change_description='Add debug mode',
            dev2_intent='Add debugging',
            conflicting_sections=[(2, 'both modify config dict')],
            independent_sections=[],
            intents_compatible=True,
            timestamp=datetime.now()
        )

        self.archaeologist.record_conflict(record)
        learnable = self.archaeologist.identify_learnable_conflicts()

        self.assertIn('conflict_003', learnable)

    def test_get_conflict_timeline(self):
        """Test retrieving timeline of conflicts"""
        now = datetime.now()

        for i in range(3):
            record = ConflictArchaeologyRecord(
                conflict_id=f'conflict_{i}',
                resource=f'file_{i}.py',
                developer_1='dev1',
                developer_2='dev2',
                original_state='original',
                dev1_change_description='change1',
                dev1_intent='intent1',
                dev2_change_description='change2',
                dev2_intent='intent2',
                conflicting_sections=[],
                independent_sections=[],
                intents_compatible=False,
                timestamp=now - timedelta(days=i)
            )
            self.archaeologist.record_conflict(record)

        timeline = self.archaeologist.get_timeline(days_back=7)
        self.assertEqual(len(timeline), 3)


class TestConflictPatternAnalysis(unittest.TestCase):
    """Test 2B: Conflict Pattern Analysis - Identify systemic patterns"""

    def setUp(self):
        self.analyzer = PatternAnalyzer()

    def test_identify_high_conflict_module(self):
        """Test identifying modules with high conflict frequency"""
        # Add 3 conflicts on same resource
        for i in range(3):
            self.analyzer.add_conflict({
                'resource': 'auth.py',
                'dev1': 'dev1',
                'dev2': f'dev{i+2}'
            })

        patterns = self.analyzer.analyze_patterns()
        high_conflict = [p for p in patterns if p.pattern_type == 'high_conflict_module']

        self.assertEqual(len(high_conflict), 1)
        self.assertEqual(high_conflict[0].frequency, 3)
        self.assertIn('auth.py', high_conflict[0].affected_resources)

    def test_identify_team_silo(self):
        """Test identifying developers who keep conflicting with each other"""
        # Add 2 conflicts between same two developers
        for i in range(2):
            self.analyzer.add_conflict({
                'resource': f'file_{i}.py',
                'dev1': 'alice',
                'dev2': 'bob'
            })

        patterns = self.analyzer.analyze_patterns()
        team_silo = [p for p in patterns if p.pattern_type == 'team_silo']

        self.assertEqual(len(team_silo), 1)
        self.assertEqual(team_silo[0].frequency, 2)
        self.assertIn('alice', team_silo[0].involved_developers)
        self.assertIn('bob', team_silo[0].involved_developers)

    def test_get_patterns_by_type(self):
        """Test filtering patterns by type"""
        # Create high-conflict module pattern
        for i in range(3):
            self.analyzer.add_conflict({
                'resource': 'auth.py',
                'dev1': 'alice',
                'dev2': 'charlie'
            })

        self.analyzer.analyze_patterns()

        high_conflict = self.analyzer.get_patterns_by_type('high_conflict_module')

        self.assertEqual(len(high_conflict), 1)

    def test_get_high_frequency_patterns(self):
        """Test retrieving high-frequency patterns"""
        for i in range(5):
            self.analyzer.add_conflict({
                'resource': 'critical.py',
                'dev1': 'dev1',
                'dev2': 'dev2'
            })

        patterns = self.analyzer.analyze_patterns()
        high_freq = self.analyzer.get_high_frequency_patterns(min_frequency=3)

        self.assertGreater(len(high_freq), 0)
        self.assertGreaterEqual(high_freq[0].frequency, 3)

    def test_get_improvement_metrics(self):
        """Test getting improvement metrics from patterns"""
        for i in range(3):
            self.analyzer.add_conflict({
                'resource': 'auth.py',
                'dev1': 'dev1',
                'dev2': 'dev2'
            })

        self.analyzer.analyze_patterns()
        metrics = self.analyzer.get_improvement_metrics()

        self.assertIn('total_patterns', metrics)
        self.assertIn('avg_pattern_frequency', metrics)
        self.assertGreater(metrics['total_patterns'], 0)


class TestConflictCausalityTracking(unittest.TestCase):
    """Test 2C: Conflict Causality Tracking - Analyze root causes"""

    def setUp(self):
        self.analyzer = CausalityAnalyzer()

    def test_record_and_analyze_causality(self):
        """Test recording conflict causality information"""
        conflict_data = {
            'dev1': 'dev1',
            'dev2': 'dev2',
            'resource': 'auth.py',
            'dev1_intent': 'Add authentication validation',
            'dev2_intent': 'Refactor auth module',
            'files_changed': ['auth.py', 'utils.py'],
            'synchronized': False,
            'poorly_documented': True,
            'code_reviewed': False
        }

        result = self.analyzer.analyze_conflict_cause('conflict_001', conflict_data)

        self.assertIsNotNone(result)
        self.assertIn('root_cause', result)
        self.assertIn('contributing_factors', result)

    def test_identify_prevention_opportunities(self):
        """Test identifying prevention opportunities from causality"""
        conflict_data = {
            'dev1': 'alice',
            'dev2': 'bob',
            'resource': 'payment.py',
            'dev1_intent': '',
            'dev2_intent': '',
            'synchronized': False
        }

        result = self.analyzer.analyze_conflict_cause('conflict_002', conflict_data)
        opportunities = result.get('prevention_opportunities', [])

        self.assertGreater(len(opportunities), 0)

    def test_find_similar_past_conflicts(self):
        """Test finding similar conflicts from history"""
        # Record multiple conflicts with same root cause
        for i in range(3):
            conflict_data = {
                'dev1': 'dev1',
                'dev2': 'dev2',
                'resource': 'auth.py',
                'dev1_intent': 'Implement auth',
                'dev2_intent': 'Refactor modules',
                'files_changed': ['auth.py', 'utils.py']
            }
            self.analyzer.analyze_conflict_cause(f'conflict_{i}', conflict_data)

        # Get all root causes
        root_causes = self.analyzer.get_root_causes()

        self.assertGreater(len(root_causes), 0)

    def test_get_causality_statistics(self):
        """Test getting statistics from causality analysis"""
        for i in range(3):
            conflict_data = {
                'dev1': 'dev1',
                'dev2': 'dev2',
                'resource': f'resource_{i}.py',
                'dev1_intent': 'Intent A' if i == 0 else '',
                'dev2_intent': 'Intent B' if i == 0 else '',
                'files_changed': ['file.py'] if i < 2 else ['a.py', 'b.py', 'c.py', 'd.py']
            }
            self.analyzer.analyze_conflict_cause(f'conflict_{i}', conflict_data)

        root_causes = self.analyzer.get_root_causes()

        self.assertGreater(len(root_causes), 0)

    def test_most_common_root_cause(self):
        """Test identifying most common root cause"""
        # Record multiple conflicts with misaligned requirements (different intent keywords)
        for i in range(3):
            conflict_data = {
                'dev1': 'dev1',
                'dev2': 'dev2',
                'resource': f'resource_{i}.py',
                'dev1_intent': 'Add feature X',
                'dev2_intent': 'Remove feature Y',
                'files_changed': ['file.py']
            }
            self.analyzer.analyze_conflict_cause(f'conflict_{i}', conflict_data)

        # Record conflicts with insufficient communication (no intents)
        for i in range(2):
            conflict_data = {
                'dev1': 'dev1',
                'dev2': 'dev2',
                'resource': f'resource_other_{i}.py',
                'dev1_intent': '',
                'dev2_intent': '',
                'files_changed': ['file.py']
            }
            self.analyzer.analyze_conflict_cause(f'conflict_other_{i}', conflict_data)

        root_causes = self.analyzer.get_root_causes(limit=1)

        self.assertEqual(len(root_causes), 1)
        self.assertGreater(root_causes[0][1], 0)


def run_understanding_tests():
    """Run all understanding layer tests"""
    suite = unittest.TestSuite()

    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConflictArchaeology))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConflictPatternAnalysis))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConflictCausalityTracking))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_understanding_tests()
    sys.exit(0 if success else 1)
