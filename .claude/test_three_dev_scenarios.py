#!/usr/bin/env python3
"""
Three-Developer Scenario Testing
Tests linear, non-linear, and context-updated workflows with full change log tracking
"""

import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from enum import Enum

class WorkflowType(Enum):
    LINEAR = "linear"           # alice → bob → charlie (sequential)
    NON_LINEAR = "non_linear"   # alice + bob parallel, then charlie
    CONTEXT_UPDATE = "context_update"  # Shows context refresh at each step

@dataclass
class Change:
    """Individual code change"""
    developer: str
    timestamp: str
    file: str
    function: str
    action: str  # add, modify, delete
    lines_added: int
    lines_removed: int
    intent: str
    content_hash: str

@dataclass
class ContextSnapshot:
    """Context state at a point in time"""
    timestamp: str
    version: str
    created_by: str
    developer_state: Dict[str, str]
    key_assumptions: List[str]
    dependencies: List[str]
    staleness_score: float

@dataclass
class SharedChangeLogEntry:
    """Entry in the shared change log"""
    sequence: int
    timestamp: str
    developer: str
    change: Change
    context_snapshot: ContextSnapshot
    state_transition: Dict[str, str]
    conflict_check_result: str
    auto_merge_confidence: float
    metadata: Dict[str, Any]

class ThreeDevScenarioTester:
    def __init__(self, scenario_type: WorkflowType):
        self.scenario_type = scenario_type
        self.shared_change_log: List[SharedChangeLogEntry] = []
        self.developer_logs: Dict[str, List[Change]] = {
            'alice': [],
            'bob': [],
            'charlie': [],
            'system': []
        }
        self.context_history: List[ContextSnapshot] = []
        self.sequence_counter = 0

    def record_change(self, developer: str, change: Change, context: ContextSnapshot, 
                     state_transition: Dict[str, str], conflict_result: str, 
                     auto_merge_conf: float, metadata: Dict[str, Any]):
        """Record a change to both individual and shared logs"""
        
        self.sequence_counter += 1
        
        # Add to developer's personal log
        self.developer_logs[developer].append(change)
        
        # Add to shared change log with full context
        log_entry = SharedChangeLogEntry(
            sequence=self.sequence_counter,
            timestamp=change.timestamp,
            developer=developer,
            change=change,
            context_snapshot=context,
            state_transition=state_transition,
            conflict_check_result=conflict_result,
            auto_merge_confidence=auto_merge_conf,
            metadata=metadata
        )
        
        self.shared_change_log.append(log_entry)
        self.context_history.append(context)

    def run_linear_scenario(self):
        """Linear: alice → bob → charlie"""
        print("\n" + "="*80)
        print("SCENARIO 1: LINEAR (alice → bob → charlie)")
        print("="*80)

        # PHASE 1: Alice edits
        print("\n[PHASE 1] alice starts editing auth.py")
        
        alice_change = Change(
            developer='alice',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=8,
            lines_removed=2,
            intent='Add JWT expiration check for security',
            content_hash='abc123def456'
        )
        
        alice_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-1-v1',
            created_by='alice',
            developer_state={'alice': 'EDITING', 'bob': 'AVAILABLE', 'charlie': 'AVAILABLE'},
            key_assumptions=['No expiration check exists', 'Token validation is basic'],
            dependencies=['jwt.decode()', 'datetime.now()'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='alice',
            change=alice_change,
            context=alice_context,
            state_transition={'alice': 'AVAILABLE→EDITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'queue_position': 0,
                'execution_time_ms': 145,
                'lines_changed': 10,
                'cyclomatic_complexity_delta': 1,
                'test_coverage_before': 78,
                'test_coverage_after': 92
            }
        )
        print("  ✓ alice's change recorded")
        print(f"  - Intent: {alice_change.intent}")
        print(f"  - Lock: auth.py::validate_token acquired")
        
        # alice finishes, context shared to bob & charlie
        print("\n[CONTEXT SHARING] alice's context shared to bob & charlie")
        print(f"  - Context version: ctx-1-v1")
        print(f"  - Key assumptions shared:")
        for assumption in alice_context.key_assumptions:
            print(f"    • {assumption}")
        
        time.sleep(0.1)  # Simulate time passing
        
        # PHASE 2: Bob edits
        print("\n[PHASE 2] bob gets lock and edits")
        
        bob_change = Change(
            developer='bob',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=12,
            lines_removed=0,
            intent='Add comprehensive unit tests for expiration check',
            content_hash='def789ghi012'
        )
        
        bob_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-1-v2',
            created_by='bob',
            developer_state={'alice': 'AVAILABLE', 'bob': 'EDITING', 'charlie': 'CONFLICT_WAITING'},
            key_assumptions=['Expiration check implemented', 'Tests needed for validation'],
            dependencies=['pytest', 'validate_token', 'alice_changes'],
            staleness_score=0.1
        )
        
        self.record_change(
            developer='bob',
            change=bob_change,
            context=bob_context,
            state_transition={'bob': 'CONFLICT_WAITING→EDITING', 'charlie': 'AVAILABLE→CONFLICT_WAITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=86.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'queue_position': 1,
                'promoted_from_queue': True,
                'wait_time_ms': 3200,
                'execution_time_ms': 287,
                'lines_changed': 12,
                'test_coverage_before': 92,
                'test_coverage_after': 98,
                'tests_added': 5,
                'context_version_used': 'ctx-1-v1',
                'context_staleness_ms': 3200,
                'intent_alignment': 'HIGH'
            }
        )
        print("  ✓ bob's change recorded")
        print(f"  - Intent: {bob_change.intent}")
        print(f"  - Wait time: 3.2s (promoted from CONFLICT_WAITING)")
        print(f"  - Auto-merge confidence: 86%")
        
        # bob finishes, context shared to alice & charlie
        print("\n[CONTEXT SHARING] bob's context shared to alice & charlie")
        print(f"  - Context version: ctx-1-v2 (updated)")
        print(f"  - Key findings:")
        print(f"    • Tests validate alice's expiration check ✓")
        print(f"    • No conflicts detected")
        print(f"    • charlie's context refreshed (staleness check)")
        
        time.sleep(0.1)
        
        # PHASE 3: Charlie edits
        print("\n[PHASE 3] charlie gets lock and edits")
        
        charlie_change = Change(
            developer='charlie',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=6,
            lines_removed=0,
            intent='Add documentation and error handling for token validation',
            content_hash='jkl345mno678'
        )
        
        charlie_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-1-v3',
            created_by='charlie',
            developer_state={'alice': 'AVAILABLE', 'bob': 'AVAILABLE', 'charlie': 'EDITING'},
            key_assumptions=['Expiration check implemented', 'Tests comprehensive', 'Ready for docs'],
            dependencies=['alice_changes', 'bob_tests', 'docstring_format'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='charlie',
            change=charlie_change,
            context=charlie_context,
            state_transition={'charlie': 'CONFLICT_WAITING→EDITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=88.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'queue_position': 2,
                'promoted_from_queue': True,
                'wait_time_ms': 6890,
                'execution_time_ms': 156,
                'lines_changed': 6,
                'test_coverage_before': 98,
                'test_coverage_after': 98,
                'documentation_added': True,
                'error_handling_added': True,
                'context_version_used': 'ctx-1-v2-refreshed',
                'context_staleness_ms': 6890,
                'staleness_detected': False,
                'intent_alignment': 'PERFECT'
            }
        )
        print("  ✓ charlie's change recorded")
        print(f"  - Intent: {charlie_change.intent}")
        print(f"  - Wait time: 6.9s (promoted from CONFLICT_WAITING)")
        print(f"  - Auto-merge confidence: 88%")
        
        print("\n[APPROVAL GATHERING]")
        print("  - alice: Author (approved) ✓")
        print("  - bob: Testing expert (approved) ✓")
        print("  - charlie: Documentation expert (approved) ✓")
        print("  - Overall PR approval: 88% auto-merge confidence")

    def run_non_linear_scenario(self):
        """Non-linear: alice on auth.py + bob on user.py parallel, then charlie"""
        print("\n" + "="*80)
        print("SCENARIO 2: NON-LINEAR (alice + bob parallel, then charlie)")
        print("="*80)

        # PHASE 1a: Alice edits auth.py
        print("\n[PHASE 1a] alice starts editing auth.py")
        
        alice_change = Change(
            developer='alice',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=8,
            lines_removed=2,
            intent='Add JWT expiration check',
            content_hash='par001abc123'
        )
        
        alice_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-par-v1',
            created_by='alice',
            developer_state={'alice': 'BOTH_EDITING', 'bob': 'AVAILABLE', 'charlie': 'AVAILABLE'},
            key_assumptions=['No expiration check'],
            dependencies=['jwt.decode()'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='alice',
            change=alice_change,
            context=alice_context,
            state_transition={'alice': 'AVAILABLE→BOTH_EDITING (auth.py)'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'parallel_mode': True,
                'resource_specific': True,
                'other_resources_locked': [],
                'execution_time_ms': 145
            }
        )
        print("  ✓ alice's change on auth.py recorded")
        
        # PHASE 1b: Bob edits user.py (PARALLEL)
        print("\n[PHASE 1b] bob simultaneously edits user.py (PARALLEL)")
        
        bob_change = Change(
            developer='bob',
            timestamp=datetime.now().isoformat(),
            file='user.py',
            function='get_user_profile',
            action='modify',
            lines_added=10,
            lines_removed=1,
            intent='Add user profile caching for performance',
            content_hash='par001def789'
        )
        
        bob_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-par-v1b',
            created_by='bob',
            developer_state={'alice': 'BOTH_EDITING (auth.py)', 'bob': 'BOTH_EDITING (user.py)', 'charlie': 'AVAILABLE'},
            key_assumptions=['User profiles need caching'],
            dependencies=['cache.set()', 'get_user_profile'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='bob',
            change=bob_change,
            context=bob_context,
            state_transition={'bob': 'AVAILABLE→BOTH_EDITING (user.py)'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'user.py::get_user_profile',
                'parallel_mode': True,
                'resource_specific': True,
                'other_resources_locked': ['auth.py (alice)'],
                'no_interference': True,
                'execution_time_ms': 167
            }
        )
        print("  ✓ bob's change on user.py recorded (parallel to alice)")
        print("  - No lock conflict: alice on auth.py, bob on user.py")
        print("  - Both in BOTH_EDITING state")
        
        time.sleep(0.1)
        
        # PHASE 2a: Alice finishes
        print("\n[PHASE 2a] alice finishes editing auth.py")
        
        alice_finish_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-par-v2',
            created_by='system',
            developer_state={'alice': 'AVAILABLE', 'bob': 'BOTH_EDITING (user.py)', 'charlie': 'AVAILABLE'},
            key_assumptions=['alice done', 'bob still editing user.py'],
            dependencies=['alice_changes', 'bob_still_editing'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='alice',
            change=Change(
                developer='alice',
                timestamp=datetime.now().isoformat(),
                file='auth.py',
                function='validate_token',
                action='modify',
                lines_added=0,
                lines_removed=0,
                intent='Finish editing',
                content_hash='par001finish1'
            ),
            context=alice_finish_context,
            state_transition={'alice': 'BOTH_EDITING→AVAILABLE'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'event_type': 'lock_release',
                'released_resource': 'auth.py::validate_token',
                'execution_time_ms': 0,
                'bob_still_working': True,
                'concurrent_activities': 1
            }
        )
        print("  ✓ alice released lock on auth.py")
        
        time.sleep(0.1)
        
        # PHASE 2b: Bob finishes
        print("\n[PHASE 2b] bob finishes editing user.py")
        
        bob_finish_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-par-v3',
            created_by='system',
            developer_state={'alice': 'AVAILABLE', 'bob': 'AVAILABLE', 'charlie': 'AVAILABLE'},
            key_assumptions=['alice done', 'bob done', 'charlie ready'],
            dependencies=['alice_changes', 'bob_changes'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='bob',
            change=Change(
                developer='bob',
                timestamp=datetime.now().isoformat(),
                file='user.py',
                function='get_user_profile',
                action='modify',
                lines_added=0,
                lines_removed=0,
                intent='Finish editing',
                content_hash='par001finish2'
            ),
            context=bob_finish_context,
            state_transition={'bob': 'BOTH_EDITING→AVAILABLE'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'event_type': 'lock_release',
                'released_resource': 'user.py::get_user_profile',
                'execution_time_ms': 0,
                'parallel_execution_time_total_ms': 334,
                'concurrent_activities': 0
            }
        )
        print("  ✓ bob released lock on user.py")
        print("  - Parallel execution completed")
        print("  - Time: alice(145ms) + bob(167ms) = 312ms in parallel (vs 287ms sequential)")
        
        time.sleep(0.1)
        
        # PHASE 3: Charlie edits (after parallel work)
        print("\n[PHASE 3] charlie edits (integrates both alice & bob changes)")
        
        charlie_change = Change(
            developer='charlie',
            timestamp=datetime.now().isoformat(),
            file='integration.py',
            function='authenticate_and_get_profile',
            action='modify',
            lines_added=15,
            lines_removed=3,
            intent='Integrate auth validation with user profile retrieval',
            content_hash='par001charlie1'
        )
        
        charlie_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-par-v4',
            created_by='charlie',
            developer_state={'alice': 'AVAILABLE', 'bob': 'AVAILABLE', 'charlie': 'EDITING'},
            key_assumptions=['alice: expiration check done', 'bob: caching done'],
            dependencies=['alice_changes', 'bob_changes', 'integration_layer'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='charlie',
            change=charlie_change,
            context=charlie_context,
            state_transition={'charlie': 'AVAILABLE→EDITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=92.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'integration.py::authenticate_and_get_profile',
                'parallel_predecessor_count': 2,
                'execution_time_ms': 198,
                'dependencies_ready': True,
                'context_integration_time': 1.2
            }
        )
        print("  ✓ charlie's integrating change recorded")
        print(f"  - Integrated alice (auth) + bob (profile caching)")
        print(f"  - Auto-merge confidence: 92%")

    def run_context_update_scenario(self):
        """Shows context being updated/refreshed during the workflow"""
        print("\n" + "="*80)
        print("SCENARIO 3: CONTEXT UPDATE & STALENESS DETECTION")
        print("="*80)

        # PHASE 1: Alice edits
        print("\n[PHASE 1] alice edits and shares context")
        
        alice_change = Change(
            developer='alice',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=8,
            lines_removed=2,
            intent='Add JWT expiration check',
            content_hash='ctx001alice1'
        )
        
        alice_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-upd-v1',
            created_by='alice',
            developer_state={'alice': 'EDITING', 'bob': 'AVAILABLE', 'charlie': 'AVAILABLE'},
            key_assumptions=['Expiration check needed', 'No refactoring'],
            dependencies=['jwt.decode()'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='alice',
            change=alice_change,
            context=alice_context,
            state_transition={'alice': 'AVAILABLE→EDITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=100.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'context_version': 'ctx-upd-v1',
                'shared_to': ['bob', 'charlie']
            }
        )
        print("  ✓ alice's change recorded")
        print(f"  - Context v1 created and shared")
        
        time.sleep(0.5)  # Simulate some time passing
        
        # PHASE 2: Bob makes unexpected changes (major refactor)
        print("\n[PHASE 2] bob gets lock and does MAJOR REFACTOR (unexpected)")
        
        bob_change = Change(
            developer='bob',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=25,
            lines_removed=15,
            intent='Major refactor for maintainability (different from alice\'s intent)',
            content_hash='ctx001bob_refactor'
        )
        
        bob_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-upd-v2',
            created_by='bob',
            developer_state={'alice': 'AVAILABLE', 'bob': 'EDITING', 'charlie': 'CONFLICT_WAITING'},
            key_assumptions=['Refactoring for clarity', 'Expiration check integrated'],
            dependencies=['refactored_function', 'expiration_logic'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='bob',
            change=bob_change,
            context=bob_context,
            state_transition={'bob': 'CONFLICT_WAITING→EDITING'},
            conflict_result='INTENT_MISMATCH_DETECTED',
            auto_merge_conf=65.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'staleness_detection_triggered': True,
                'previous_context_version': 'ctx-upd-v1',
                'current_context_version': 'ctx-upd-v2',
                'intent_deviation': 'MAJOR_REFACTOR (not just tests)',
                'charlie_context_invalidated': True,
                'confidence_reduction': 35
            }
        )
        print("  ✓ bob's MAJOR REFACTOR recorded")
        print(f"  - Intent MISMATCH detected!")
        print(f"  - alice: Add expiration check")
        print(f"  - bob: Refactor entire function")
        print(f"  - charlie's context INVALIDATED (staleness detected)")
        print(f"  - Auto-merge confidence: 65% (down from 100%)")
        
        time.sleep(0.5)
        
        # PHASE 2.5: CONTEXT REFRESH TRIGGERED
        print("\n[CONTEXT REFRESH] system detects staleness and refreshes charlie's context")
        
        refresh_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-upd-v2-refreshed',
            created_by='system',
            developer_state={'alice': 'AVAILABLE', 'bob': 'EDITING', 'charlie': 'CONFLICT_WAITING_REFRESHED'},
            key_assumptions=['alice: expiration added', 'bob: major refactor (intent mismatch)'],
            dependencies=['refactored_code', 'expiration_logic'],
            staleness_score=0.75  # High staleness
        )
        
        self.record_change(
            developer='system',
            change=Change(
                developer='system',
                timestamp=datetime.now().isoformat(),
                file='auth.py',
                function='validate_token',
                action='refresh',
                lines_added=0,
                lines_removed=0,
                intent='Context refresh due to staleness detection',
                content_hash='refresh_marker'
            ),
            context=refresh_context,
            state_transition={'charlie': 'CONFLICT_WAITING→CONFLICT_WAITING_REFRESHED'},
            conflict_result='CONTEXT_STALE_REFRESHED',
            auto_merge_conf=65.0,
            metadata={
                'event_type': 'context_refresh',
                'reason': 'STALENESS_DETECTED',
                'staleness_age_ms': 500,
                'staleness_threshold_ms': 300,
                'refresh_mechanisms': [
                    'AST_DIFF_VALIDATION',
                    'INTENT_MISMATCH_DETECTION',
                    'TIME_BASED_REFRESH'
                ],
                'charlie_notification': 'Your context is stale (500ms old). alice: expiration check added. bob: MAJOR REFACTOR detected. Review before editing.',
                'old_version': 'ctx-upd-v1',
                'new_version': 'ctx-upd-v2-refreshed',
                'assumptions_violated': 2,
                'conflict_probability': 'MEDIUM'
            }
        )
        print("  ✓ Context refresh recorded")
        print(f"  - Staleness: 500ms (threshold: 300ms)")
        print(f"  - Detection method: Intent mismatch + AST diff")
        print(f"  - charlie notified of context refresh")
        
        time.sleep(0.5)
        
        # PHASE 3: Charlie edits with refreshed context
        print("\n[PHASE 3] charlie gets lock with REFRESHED context")
        
        charlie_change = Change(
            developer='charlie',
            timestamp=datetime.now().isoformat(),
            file='auth.py',
            function='validate_token',
            action='modify',
            lines_added=4,
            lines_removed=0,
            intent='Add error handling (aware of refactor)',
            content_hash='ctx001charlie1'
        )
        
        charlie_context = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            version='ctx-upd-v3',
            created_by='charlie',
            developer_state={'alice': 'AVAILABLE', 'bob': 'AVAILABLE', 'charlie': 'EDITING'},
            key_assumptions=['alice: expiration', 'bob: refactored', 'charlie: error handling'],
            dependencies=['refactored_function', 'error_handling'],
            staleness_score=0.0
        )
        
        self.record_change(
            developer='charlie',
            change=charlie_change,
            context=charlie_context,
            state_transition={'charlie': 'CONFLICT_WAITING_REFRESHED→EDITING'},
            conflict_result='NO_CONFLICT',
            auto_merge_conf=82.0,
            metadata={
                'lock_acquired': True,
                'lock_resource': 'auth.py::validate_token',
                'context_version_used': 'ctx-upd-v2-refreshed',
                'context_refreshed_before_edit': True,
                'acknowledged_context_refresh': True,
                'conflict_check_result': 'NO_CONFLICT',
                'assumptions_verified': True,
                'wait_time_with_refresh_ms': 1000,
                'execution_time_ms': 134
            }
        )
        print("  ✓ charlie's change recorded")
        print(f"  - Used refreshed context (ctx-upd-v2-refreshed)")
        print(f"  - Acknowledged intent mismatch between alice & bob")
        print(f"  - No conflicts detected with refreshed understanding")
        print(f"  - Auto-merge confidence: 82%")

    def generate_report(self):
        """Generate comprehensive report with logs and metadata"""
        report = {
            'scenario_type': self.scenario_type.value,
            'total_changes': len(self.shared_change_log),
            'total_context_snapshots': len(self.context_history),
            'shared_change_log': [
                {
                    'sequence': entry.sequence,
                    'timestamp': entry.timestamp,
                    'developer': entry.developer,
                    'change': asdict(entry.change),
                    'context': asdict(entry.context_snapshot),
                    'state_transition': entry.state_transition,
                    'conflict_check': entry.conflict_check_result,
                    'auto_merge_confidence': entry.auto_merge_confidence,
                    'metadata': entry.metadata
                }
                for entry in self.shared_change_log
            ],
            'developer_individual_logs': {
                dev: [asdict(change) for change in changes]
                for dev, changes in self.developer_logs.items()
            }
        }
        return report

def main():
    # Run all three scenarios
    
    # Scenario 1: Linear
    tester1 = ThreeDevScenarioTester(WorkflowType.LINEAR)
    tester1.run_linear_scenario()
    report1 = tester1.generate_report()
    
    # Scenario 2: Non-linear
    tester2 = ThreeDevScenarioTester(WorkflowType.NON_LINEAR)
    tester2.run_non_linear_scenario()
    report2 = tester2.generate_report()
    
    # Scenario 3: Context update
    tester3 = ThreeDevScenarioTester(WorkflowType.CONTEXT_UPDATE)
    tester3.run_context_update_scenario()
    report3 = tester3.generate_report()
    
    # Save reports
    reports = {
        'linear': report1,
        'non_linear': report2,
        'context_update': report3
    }
    
    with open('/tmp/claude-0/-home-user-Neo/5f8f1250-4774-59c0-9acf-6b5ca5217fc7/scratchpad/three_dev_scenario_logs.json', 'w') as f:
        json.dump(reports, f, indent=2)
    
    print("\n" + "="*80)
    print("Reports saved to three_dev_scenario_logs.json")
    print("="*80)
    
    # Print metadata analysis
    print_metadata_analysis(reports)

def print_metadata_analysis(reports):
    """Analyze and print metadata requirements"""
    print("\n" + "="*80)
    print("METADATA ANALYSIS")
    print("="*80)
    
    metadata_fields = set()
    for scenario_name, report in reports.items():
        for entry in report['shared_change_log']:
            if entry['metadata']:
                metadata_fields.update(entry['metadata'].keys())
    
    print("\nMetadata Fields Captured:")
    print("-" * 80)
    for field in sorted(metadata_fields):
        print(f"  • {field}")
    
    print("\nMetadata Categories:")
    print("-" * 80)
    categories = {
        'Lock Management': ['lock_acquired', 'lock_resource', 'queue_position', 'promoted_from_queue', 'wait_time_ms'],
        'Execution': ['execution_time_ms', 'lines_changed', 'lines_added', 'lines_removed'],
        'Quality': ['test_coverage_before', 'test_coverage_after', 'tests_added', 'cyclomatic_complexity_delta'],
        'Context': ['context_version_used', 'context_staleness_ms', 'intent_alignment'],
        'Parallel': ['parallel_mode', 'resource_specific', 'other_resources_locked', 'concurrent_activities'],
        'Conflict': ['conflict_check_result', 'intent_deviation', 'assumptions_violated', 'conflict_probability'],
        'Refresh': ['staleness_detection_triggered', 'context_invalidated', 'staleness_age_ms', 'refresh_mechanisms']
    }
    
    for category, fields in categories.items():
        print(f"\n  {category}:")
        for field in fields:
            if field in metadata_fields:
                print(f"    ✓ {field}")

if __name__ == '__main__':
    main()
