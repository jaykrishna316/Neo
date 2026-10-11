#!/usr/bin/env python3
"""Manual test runner for C1/C2 claims (no pytest dependency)."""

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.optimized_activity_log import is_context_stale, CONTEXT_STALENESS_THRESHOLD_MS
from core.risk_classifier import regions_overlap, detect_signature_change

# Test data
SRC_V1 = '''def charge(amount):
    return amount * 2


def process_refund(order):
    return order.total


def audit(event):
    return event.name
'''

SRC_PROCESS_REFUND_V2 = SRC_V1.replace(
    "return order.total",
    "return order.total - order.fee",
)

SRC_FORMAT_ONLY = SRC_V1.replace("return amount * 2", "return  amount*2  # same logic")

SRC_BROKEN = SRC_V1 + "\ndef broken(:\n    pass\n"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tests = []

    def test(self, name, condition, reason=""):
        """Record a test result."""
        if condition:
            self.passed += 1
            status = "✓ PASS"
        else:
            self.failed += 1
            status = "✗ FAIL"

        self.tests.append((name, status, reason))
        print(f"{status} {name}" + (f" — {reason}" if reason else ""))

    def skip(self, name, reason=""):
        """Skip a test."""
        self.skipped += 1
        self.tests.append((name, "⏭️ SKIP", reason))
        print(f"⏭️ SKIP {name} — {reason}")

    def report(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Skipped: {self.skipped}")
        print(f"Total: {self.passed + self.failed + self.skipped}")
        print("=" * 70)

        if self.failed > 0:
            print("\nFailed tests:")
            for name, status, reason in self.tests:
                if status == "✗ FAIL":
                    print(f"  {name}: {reason}")


def run_tests():
    """Run all C1/C2 tests."""
    runner = TestRunner()

    print("=" * 70)
    print("C1/C2 CLAIM TESTS - AUTO-RUNNER")
    print("=" * 70)

    # ===== T1: Threshold Boundary =====
    print("\n[T1] Threshold Boundary Tests")
    print("-" * 70)
    now = 1_000_000.0

    stale_999, _ = is_context_stale(now - 0.999, now)
    runner.test("T1a: age=999ms not stale", stale_999 == False)

    stale_1000, _ = is_context_stale(now - 1.0, now)
    runner.test("T1b: age=1000ms not stale", stale_1000 == False)

    stale_1001, _ = is_context_stale(now - 1.001, now)
    runner.test("T1c: age=1001ms stale", stale_1001 == True)

    # ===== T1b: README =====
    print("\n[T1b] README Documentation")
    print("-" * 70)
    readme = (ROOT / "README.md").read_text()
    ms = CONTEXT_STALENESS_THRESHOLD_MS
    found = f"{ms} ms" in readme or f"{ms}ms" in readme or f">{ms}ms" in readme
    runner.test(
        "T1b: README documents threshold",
        found,
        f"Looking for '{ms}ms' or '{ms} ms' reference"
    )

    # ===== T2: Content-based Staleness (Expected FAIL - time-only check) =====
    print("\n[T2] Content-based Staleness Detection (Expected FAIL - time-only)")
    print("-" * 70)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "payment.py"
        f.write_text(SRC_V1)
        t0 = time.time()
        f.write_text(SRC_PROCESS_REFUND_V2)

        stale, _ = is_context_stale(t0, t0)
        runner.test(
            "T2: Content change detected at t0",
            stale == True,
            "Expected FAIL: is_context_stale() is time-only fallback. "
            "Use check_freshness() (C1) for content-based detection"
        )

    # ===== T2a: C1 - Changed Symbol Flags STALE_SOURCE =====
    print("\n[T2a-T2d] C1 Symbol-Level Staleness Tests")
    print("-" * 70)
    try:
        from core.freshness import record_read, check_freshness

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "payment.py"
            import os
            os.environ["NEO_STATE_DIR"] = str(Path(tmp) / "neo_state")

            # T2a: Changed symbol
            f.write_text(SRC_V1)
            record_read("agent_B", str(f))
            f.write_text(SRC_PROCESS_REFUND_V2)
            result = check_freshness("agent_B", str(f))
            runner.test("T2a: Changed symbol flags STALE_SOURCE", result == "STALE_SOURCE")

            # T2b: Unread symbol change doesn't flag
            f.write_text(SRC_V1)
            record_read("agent_C", str(f), symbols=["charge"])
            f.write_text(SRC_PROCESS_REFUND_V2)
            result = check_freshness("agent_C", str(f))
            runner.test(
                "T2b: Unread symbol change is CURRENT",
                result == "CURRENT",
                "Agent only depends on 'charge', not 'process_refund'"
            )

            # T2c: Formatting-only edit
            f.write_text(SRC_V1)
            record_read("agent_D", str(f))
            f.write_text(SRC_FORMAT_ONLY)
            result = check_freshness("agent_D", str(f))
            runner.test("T2c: Formatting-only is CURRENT", result == "CURRENT")

            # T2d: Unparseable file
            f.write_text(SRC_V1)
            record_read("agent_E", str(f))
            f.write_text(SRC_BROKEN)
            result = check_freshness("agent_E", str(f))
            runner.test("T2d: Broken syntax is UNVERIFIABLE", result == "UNVERIFIABLE")
    except ImportError:
        runner.skip("T2a-T2d", "core.freshness not found")

    # ===== T3: C2 Delta =====
    print("\n[T3-T3b] C2 Delta Refresh Tests")
    print("-" * 70)
    try:
        from core.freshness import record_read, delta_since_base

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "payment.py"
            import os
            os.environ["NEO_STATE_DIR"] = str(Path(tmp) / "neo_state")

            # T3: Delta contains only changed symbol
            f.write_text(SRC_V1)
            record_read("agent_F", str(f))
            f.write_text(SRC_PROCESS_REFUND_V2)
            payload = delta_since_base("agent_F", str(f))

            has_changed = "order.total - order.fee" in payload
            no_charge = "def charge" not in payload
            no_audit = "def audit" not in payload
            smaller = len(payload) < len(SRC_PROCESS_REFUND_V2)

            runner.test("T3: Delta contains changed symbol", has_changed)
            runner.test("T3: Delta excludes unchanged symbols", no_charge and no_audit)
            runner.test("T3: Delta is smaller than full file", smaller)

            # T3b: Five edits coalesce
            f.write_text(SRC_V1)
            record_read("agent_G", str(f))
            for i in range(1, 6):
                src = SRC_V1.replace("return order.total", f"return order.total - {i}")
                f.write_text(src)

            payload = delta_since_base("agent_G", str(f))
            final_state = "order.total - 5" in payload
            no_intermediate = not any(f"order.total - {i}" in payload for i in range(1, 5))
            only_one_def = payload.count("def process_refund") == 1

            runner.test("T3b: Final state in delta", final_state)
            runner.test("T3b: Intermediate edits not replayed", no_intermediate)
            runner.test("T3b: Single definition in delta", only_one_def)
    except ImportError:
        runner.skip("T3-T3b", "core.freshness not found")

    # ===== T7: Classifier Regressions =====
    print("\n[T7] Classifier Regression Tests")
    print("-" * 70)

    result = detect_signature_change("Move the cursor blink animation")
    runner.test("T7a: Move (UI) not signature change", result == False)

    result = detect_signature_change("Remove legacy helper")
    runner.test("T7b: Remove is signature change", result == True)

    result = regions_overlap("A.validate", "B.validate")
    runner.test("T7c: Different classes don't overlap", result == False)

    result = regions_overlap("A.validate", "A.validate")
    runner.test("T7d: Same name overlaps", result == True)

    # ===== T4: Token Cost (needs API key) =====
    print("\n[T4] Token Cost Measurement (Requires ANTHROPIC_API_KEY)")
    print("-" * 70)
    import os
    if os.environ.get("ANTHROPIC_API_KEY"):
        runner.skip("T4", "Not implemented in manual runner (requires anthropic SDK)")
    else:
        runner.skip("T4", "ANTHROPIC_API_KEY not set")

    # Print summary
    runner.report()

    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
