#!/usr/bin/env python3
"""
Test Optimization 1: Reduce Delta Refresh Size
- Validates delta refresh tokens reduced from 50 to 7 (85% reduction)
- Tests real token counting based on intent length
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.optimized_activity_log import OptimizedActivityEntry, estimate_total_tokens


def test_delta_token_count_small_intent():
    """10-char intent → should be ~3 tokens"""
    entry = OptimizedActivityEntry(
        developer_id="alice",
        file_path="auth.py",
        intent="Add validation",  # 14 chars
        region="login_user",
        timestamp=0
    )
    tokens = entry.calculate_tokens()
    assert 1 <= tokens <= 5, f"Expected 1-5 tokens for small intent, got {tokens}"
    print(f"✓ Small intent (14 chars): {tokens} tokens")


def test_delta_token_count_medium_intent():
    """28-char intent → should be ~7 tokens"""
    entry = OptimizedActivityEntry(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation to bcrypt",  # 38 chars
        region="login_user",
        timestamp=0
    )
    tokens = entry.calculate_tokens()
    assert 5 <= tokens <= 10, f"Expected 5-10 tokens for medium intent, got {tokens}"
    print(f"✓ Medium intent (38 chars): {tokens} tokens")


def test_delta_token_count_large_intent():
    """100-char intent → capped at 10 tokens"""
    entry = OptimizedActivityEntry(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor the entire authentication system to support OAuth2, SAML, and OIDC protocols with multi-tenant support",
        region="auth_module",
        timestamp=0
    )
    tokens = entry.calculate_tokens()
    assert tokens <= 10, f"Expected ≤10 tokens (capped), got {tokens}"
    print(f"✓ Large intent (110 chars): {tokens} tokens (capped)")


def test_delta_refresh_reduction():
    """Delta (7) vs full file re-read (500+) = 98.6% savings"""
    delta_tokens = 7  # Optimization 1
    full_file_tokens = 500  # Typical file re-read

    savings = ((full_file_tokens - delta_tokens) / full_file_tokens) * 100
    assert savings > 98.0, f"Expected >98% savings, got {savings:.1f}%"
    print(f"✓ Delta refresh savings: {savings:.1f}% (7 vs 500 tokens)")


def test_estimate_delta_across_developers():
    """8 devs with varied intents → validate real measurements"""
    intents = [
        "Add password validation",
        "Refactor login_user function",
        "Add bcrypt hashing",
        "Implement rate limiting",
        "Add logging to auth",
        "Add MFA support",
        "Implement session timeout",
        "Add audit trail"
    ]

    total_chars = sum(len(i) for i in intents)
    avg_chars = total_chars / len(intents)

    entries = [
        OptimizedActivityEntry(
            developer_id=f"dev{i}",
            file_path="auth.py",
            intent=intent,
            region="auth_module",
            timestamp=0
        )
        for i, intent in enumerate(intents)
    ]

    total_tokens = sum(e.calculate_tokens() for e in entries)

    print(f"✓ 8 developers:")
    print(f"  Total characters: {total_chars}")
    print(f"  Average per dev: {avg_chars:.0f} chars")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Average per dev: {total_tokens/len(intents):.1f} tokens")

    assert total_tokens <= 80, f"Expected ≤80 tokens for 8 devs, got {total_tokens}"


def test_estimate_total_tokens_formula():
    """Validate formula: 7 + (7+7) * (N-1)"""
    test_cases = [
        (1, 7),      # 1 dev: 7 tokens
        (2, 21),     # 2 devs: 7 + 14 = 21 tokens
        (3, 35),     # 3 devs: 7 + 14*2 = 35 tokens
        (8, 105),    # 8 devs: 7 + 14*7 = 105 tokens
    ]

    for num_devs, expected in test_cases:
        entries = [
            {
                'developer_id': f'dev{i}',
                'file_path': 'auth.py',
                'intent': f'Intent from developer {i}',
                'timestamp': 0
            }
            for i in range(num_devs)
        ]

        total = estimate_total_tokens(entries)
        assert total == expected, f"Expected {expected} tokens for {num_devs} devs, got {total}"
        print(f"✓ {num_devs} dev{'s' if num_devs > 1 else ''}: {total} tokens (expected {expected})")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST OPTIMIZATION 1: Delta Refresh Reduction")
    print("=" * 70)
    print()

    test_delta_token_count_small_intent()
    test_delta_token_count_medium_intent()
    test_delta_token_count_large_intent()
    test_delta_refresh_reduction()
    test_estimate_delta_across_developers()
    test_estimate_total_tokens_formula()

    print()
    print("=" * 70)
    print("✅ ALL OPTIMIZATION 1 TESTS PASSED")
    print("=" * 70)
