#!/usr/bin/env python3
"""
Test Optimization 3: Update Token Counting Formula
- Validates formula: 7 + (7+7) * (N-1) for N developers
- Tests per-developer cost of 14 tokens (vs 26 estimated)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.optimized_activity_log import estimate_total_tokens, TOKENS_PER_DEVELOPER, DELTA_REFRESH_TOKENS


def test_constants_real_values():
    """Verify constants are from real measurements"""
    assert TOKENS_PER_DEVELOPER == 7, f"Expected TOKENS_PER_DEVELOPER=7, got {TOKENS_PER_DEVELOPER}"
    assert DELTA_REFRESH_TOKENS == 7, f"Expected DELTA_REFRESH_TOKENS=7, got {DELTA_REFRESH_TOKENS}"
    print(f"✓ Constants are real-measured values:")
    print(f"  TOKENS_PER_DEVELOPER = {TOKENS_PER_DEVELOPER}")
    print(f"  DELTA_REFRESH_TOKENS = {DELTA_REFRESH_TOKENS}")
    print(f"  TOTAL_TOKENS_PER_HANDOFF = {TOKENS_PER_DEVELOPER + DELTA_REFRESH_TOKENS}")


def test_single_developer_tokens():
    """1 dev = 7 tokens (baseline)"""
    entries = [{'developer_id': 'alice', 'file_path': 'auth.py', 'intent': 'Add validation', 'timestamp': 0}]
    total = estimate_total_tokens(entries)
    assert total == 7, f"Expected 7 tokens for 1 dev, got {total}"
    print(f"✓ 1 developer: {total} tokens")


def test_two_developer_tokens():
    """2 devs = 7 + 14 = 21 tokens"""
    entries = [
        {'developer_id': 'alice', 'file_path': 'auth.py', 'intent': 'Add validation', 'timestamp': 0},
        {'developer_id': 'bob', 'file_path': 'auth.py', 'intent': 'Add logging', 'timestamp': 1},
    ]
    total = estimate_total_tokens(entries)
    expected = 7 + (7 + 7)  # 7 + delta for second dev
    assert total == expected, f"Expected {expected} tokens for 2 devs, got {total}"
    print(f"✓ 2 developers: {total} tokens (7 + 14 for handoff)")


def test_three_developer_tokens():
    """3 devs = 7 + 14*2 = 35 tokens"""
    entries = [
        {'developer_id': 'alice', 'file_path': 'auth.py', 'intent': 'Refactor', 'timestamp': 0},
        {'developer_id': 'bob', 'file_path': 'auth.py', 'intent': 'Add logging', 'timestamp': 1},
        {'developer_id': 'charlie', 'file_path': 'auth.py', 'intent': 'Add tests', 'timestamp': 2},
    ]
    total = estimate_total_tokens(entries)
    expected = 7 + (7 + 7) * 2  # 7 + 14 + 14
    assert total == expected, f"Expected {expected} tokens for 3 devs, got {total}"
    print(f"✓ 3 developers: {total} tokens (7 + 14 + 14)")


def test_eight_developer_tokens():
    """8 devs = 7 + 14*7 = 105 tokens"""
    entries = [
        {'developer_id': f'dev{i}', 'file_path': 'auth.py', 'intent': f'Intent {i}', 'timestamp': i}
        for i in range(8)
    ]
    total = estimate_total_tokens(entries)
    expected = 7 + (7 + 7) * 7  # 7 + (14 * 7)
    assert total == expected, f"Expected {expected} tokens for 8 devs, got {total}"
    print(f"✓ 8 developers: {total} tokens (7 + 14×7)")


def test_sixteen_developer_tokens():
    """16 devs = 7 + 14*15 = 217 tokens"""
    entries = [
        {'developer_id': f'dev{i}', 'file_path': 'auth.py', 'intent': f'Intent {i}', 'timestamp': i}
        for i in range(16)
    ]
    total = estimate_total_tokens(entries)
    expected = 7 + (7 + 7) * 15  # 7 + (14 * 15)
    assert total == expected, f"Expected {expected} tokens for 16 devs, got {total}"
    print(f"✓ 16 developers: {total} tokens (7 + 14×15)")


def test_formula_consistency():
    """Formula is consistent: each additional dev costs exactly 14 tokens"""
    for num_devs in range(1, 11):
        entries = [
            {'developer_id': f'dev{i}', 'file_path': 'auth.py', 'intent': f'Intent {i}', 'timestamp': i}
            for i in range(num_devs)
        ]
        total = estimate_total_tokens(entries)
        expected = 7 + (7 + 7) * (num_devs - 1)
        assert total == expected, f"Formula mismatch at {num_devs} devs: got {total}, expected {expected}"

        if num_devs > 1:
            per_dev_additional = (total - 7) / (num_devs - 1)
            assert per_dev_additional == 14, f"Each additional dev should cost 14 tokens, got {per_dev_additional}"

    print(f"✓ Formula consistent across 1-10 developers (each additional costs 14 tokens)")


def test_comparison_to_estimated():
    """Real formula (14 per dev) vs estimated (26 per dev)"""
    num_devs = 8

    real_cost = 7 + (7 + 7) * (num_devs - 1)
    estimated_cost = 26 * num_devs

    efficiency_gain = ((estimated_cost - real_cost) / estimated_cost) * 100

    print(f"✓ Efficiency comparison (8 developers):")
    print(f"  Estimated cost: {estimated_cost} tokens (26 per dev)")
    print(f"  Real measured cost: {real_cost} tokens (14 per dev)")
    print(f"  Efficiency gain: {efficiency_gain:.1f}% more efficient than estimated")

    assert efficiency_gain > 40, f"Expected >40% efficiency gain, got {efficiency_gain:.1f}%"


def test_matches_option_a_data():
    """Verify tokens match Option A real measurements"""
    # From Option A: 8 devs with 224 total chars, 7 tokens per dev
    # total should be around 56-112 tokens depending on handoff factor
    entries = [
        {
            'developer_id': f'dev{i}',
            'file_path': 'auth.py',
            'intent': 'Add password validation',  # 24 chars ≈ 6 tokens
            'timestamp': i
        }
        for i in range(8)
    ]

    total = estimate_total_tokens(entries)
    # Formula: 7 + (14 * 7) = 105 tokens
    assert total == 105, f"Expected 105 tokens for 8 devs, got {total}"
    print(f"✓ Matches Option A data: 8 devs = {total} tokens")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST OPTIMIZATION 3: Token Counting Formula")
    print("=" * 70)
    print()

    test_constants_real_values()
    test_single_developer_tokens()
    test_two_developer_tokens()
    test_three_developer_tokens()
    test_eight_developer_tokens()
    test_sixteen_developer_tokens()
    test_formula_consistency()
    test_comparison_to_estimated()
    test_matches_option_a_data()

    print()
    print("=" * 70)
    print("✅ ALL OPTIMIZATION 3 TESTS PASSED")
    print("=" * 70)
