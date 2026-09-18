"""
Neo 3.0 Prevention Layer Tests (1A-1E)

Tests all prevention layer features:
- 1A: Intent-Aware Path Detection
- 1B: Concurrent Work Detection
- 1C: Temporal Conflict Prediction
- 1D: Semantic Invariant Checking
- 1E: Knowledge Gap Detection
"""

import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, '/home/user/Neo/.claude')

from prevention.intent_detection import IntentDetector
from prevention.working_set_tracker import WorkingSetTracker
from prevention.temporal_predictor import TemporalPredictor
from prevention.semantic_checker import SemanticChecker, create_null_check_invariant
from prevention.knowledge_gap_detector import KnowledgeGapDetector


class TestIntentDetection(unittest.TestCase):
    """Test 1A: Intent-Aware Path Detection"""

    def setUp(self):
        self.detector = IntentDetector()

    def test_extract_intent_from_commit(self):
        """Test extracting intent from commit message"""
        event = {'commit_message': 'Add email validation to auth module'}
        intent = self.detector.extract_intent_from_event('dev1', event)

        self.assertIsNotNone(intent)
        self.assertEqual(intent.developer, 'dev1')
        self.assertIn('email', intent.intent_description.lower())

    def test_detect_overlapping_intents(self):
        """Test detecting overlapping intents"""
        event1 = {
            'commit_message': 'Add email validation',
            'files_changed': ['auth.py', 'email.py']
        }
        event2 = {
            'commit_message': 'Refactor email validation',
            'files_changed': ['email.py', 'utils.py']
        }

        intent1 = self.detector.extract_intent_from_event('dev1', event1)
        intent2 = self.detector.extract_intent_from_event('dev2', event2)

        self.detector.register_intent(intent1)
        self.detector.register_intent(intent2)

        overlaps = self.detector.detect_overlaps()
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0][:2], ('dev1', 'dev2'))


class TestWorkingSetTracker(unittest.TestCase):
    """Test 1B: Concurrent Work Detection"""

    def setUp(self):
        self.tracker = WorkingSetTracker()

    def test_track_working_sets(self):
        """Test tracking developer working sets"""
        self.tracker.start_session('dev1')
        self.tracker.update_working_set('dev1', ['auth.py::login', 'auth.py::validate'])

        ws = self.tracker.get_developer_working_set('dev1')
        self.assertEqual(len(ws), 2)
        self.assertIn('auth.py::login', ws)

    def test_detect_overlapping_work(self):
        """Test detecting overlapping working sets"""
        self.tracker.start_session('dev1')
        self.tracker.start_session('dev2')

        self.tracker.update_working_set('dev1', ['auth.py::login', 'auth.py::validate'])
        self.tracker.update_working_set('dev2', ['auth.py::validate', 'email.py::send'])

        overlaps = self.tracker.detect_overlaps()
        self.assertEqual(len(overlaps), 1)
        self.assertIn('auth.py::validate', overlaps[0][2])


class TestTemporalPredictor(unittest.TestCase):
    """Test 1C: Temporal Conflict Prediction"""

    def setUp(self):
        self.predictor = TemporalPredictor()

    def test_predict_conflict_with_invalidation(self):
        """Test conflict prediction with context invalidation"""
        resource = 'auth.py::validate'

        self.predictor.record_context_invalidation(resource)
        self.predictor.record_developer_activity('dev1', resource, datetime.now())
        self.predictor.record_developer_activity('dev2', resource, datetime.now())

        prediction = self.predictor.predict_conflict('dev1', 'dev2', resource)

        self.assertIsNotNone(prediction)
        self.assertGreater(prediction.probability, 0.3)


class TestSemanticChecker(unittest.TestCase):
    """Test 1D: Semantic Invariant Checking"""

    def setUp(self):
        self.checker = SemanticChecker()

    def test_register_and_check_invariant(self):
        """Test registering and checking semantic invariants"""
        resource = 'auth.py'
        invariant = create_null_check_invariant(resource, 'user_id')

        self.checker.register_invariant(resource, invariant)

        violations = self.checker.check_change('dev1', resource, [10, 11],
                                              'Remove null check for user_id')

        self.assertGreater(len(violations), 0)


class TestKnowledgeGapDetector(unittest.TestCase):
    """Test 1E: Knowledge Gap Detection"""

    def setUp(self):
        self.detector = KnowledgeGapDetector()

    def test_detect_knowledge_gap(self):
        """Test detecting knowledge gaps"""
        resource = 'crypto.py'
        expert = 'alice'

        self.detector.register_expert(expert, resource, 0.95, 50)

        gap = self.detector.detect_gap('bob', expert, resource)

        self.assertIsNotNone(gap)
        self.assertEqual(gap['expert'], expert)
        self.assertEqual(gap['developer'], 'bob')


def run_prevention_tests():
    """Run all prevention layer tests"""
    suite = unittest.TestSuite()

    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntentDetection))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWorkingSetTracker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTemporalPredictor))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSemanticChecker))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeGapDetector))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_prevention_tests()
    sys.exit(0 if success else 1)
