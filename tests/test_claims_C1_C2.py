"""Neo C1/C2 claim tests. Neo only, no external baselines.

Tests that depend on core/freshness.py skip until it exists.
Tests marked 'FAIL today' are expected to fail on the current code.
"""
import os
import sys
import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.optimized_activity_log import is_context_stale, CONTEXT_STALENESS_THRESHOLD_MS  # noqa: E402
from core.risk_classifier import regions_overlap, detect_signature_change  # noqa: E402

RESULTS = ROOT / "test_results"  # written only if you create it; tests skip writing otherwise


def _freshness(tmp_path, monkeypatch):
    """Import core.freshness with an isolated state dir, or skip if not built."""
    monkeypatch.setenv("NEO_STATE_DIR", str(tmp_path / "neo_state"))
    try:
        import core.freshness as fr  # noqa: WPS433
    except ImportError:
        pytest.skip("core/freshness.py not implemented yet (C1/C2 mechanism missing)")
    return fr


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


# ---------- T1: timing (fallback only) ----------

@pytest.mark.parametrize("age_ms,expected_stale", [(999, False), (1000, False), (1001, True)])
def test_T1_threshold_boundary(age_ms, expected_stale):
    now = 1_000_000.0
    stale, _ = is_context_stale(now - age_ms / 1000.0, now)
    assert stale == expected_stale


def test_T1b_readme_threshold_matches_code():
    readme = (ROOT / "README.md").read_text()
    ms = CONTEXT_STALENESS_THRESHOLD_MS
    assert f"{ms} ms" in readme or f"{ms}ms" in readme, (
        f"README does not state the code threshold of {ms} ms"
    )


# ---------- T2: C1, content-based staleness ----------

def test_T2_current_check_sees_content_change_FAIL_TODAY(tmp_path):
    """EXPECTED FAIL: is_context_stale() is a time-only fallback for quick checks.

    It cannot detect content changes at t=0 because it only checks elapsed time (>1000ms).
    For content-based staleness detection, use check_freshness() (C1 mechanism) instead.
    This test documents the intended limitation of the legacy time-based approach.
    """
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    t0 = time.time()
    f.write_text(SRC_PROCESS_REFUND_V2)
    stale, _ = is_context_stale(t0, t0)
    assert stale is True, "is_context_stale ignores content changes (expected limitation)"


def test_T2a_changed_symbol_flags_STALE_SOURCE(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f))
    f.write_text(SRC_PROCESS_REFUND_V2)
    assert fr.check_freshness("agent_B", str(f)) == "STALE_SOURCE"


def test_T2b_unread_symbol_change_does_not_flag(tmp_path, monkeypatch):
    """Agent B only read `charge`. Changing `process_refund` must not flag B."""
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f), symbols=["charge"])  # expects optional symbols arg
    f.write_text(SRC_PROCESS_REFUND_V2)
    assert fr.check_freshness("agent_B", str(f)) == "CURRENT"


def test_T2c_formatting_only_edit_is_CURRENT(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f))
    f.write_text(SRC_FORMAT_ONLY)
    assert fr.check_freshness("agent_B", str(f)) == "CURRENT"


def test_T2d_unparseable_file_is_UNVERIFIABLE(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f))
    f.write_text(SRC_BROKEN)
    assert fr.check_freshness("agent_B", str(f)) == "UNVERIFIABLE"


# ---------- T3: C2, delta payload contents ----------

def test_T3_delta_contains_only_changed_symbol(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f))
    f.write_text(SRC_PROCESS_REFUND_V2)
    payload = fr.delta_since_base("agent_B", str(f))
    assert "order.total - order.fee" in payload, "changed body missing from delta"
    assert "def charge" not in payload, "unchanged symbol leaked into delta"
    assert "def audit" not in payload, "unchanged symbol leaked into delta"
    assert len(payload) < len(SRC_PROCESS_REFUND_V2), "delta not smaller than full file"


# ---------- T3b: C2, coalescing ----------

def test_T3b_five_edits_coalesce_into_one_net_delta(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    f = tmp_path / "payment.py"
    f.write_text(SRC_V1)
    fr.record_read("agent_B", str(f))
    versions = []
    for i in range(1, 6):
        src = SRC_V1.replace("return order.total", f"return order.total - {i}")
        f.write_text(src)
        versions.append(f"order.total - {i}")
    payload = fr.delta_since_base("agent_B", str(f))
    assert "order.total - 5" in payload, "final state missing"
    for stale_version in versions[:-1]:
        assert stale_version not in payload, f"intermediate edit replayed: {stale_version}"
    assert payload.count("def process_refund") == 1


# ---------- T4: C2, token cost with Claude's tokenizer (needs API key) ----------

FILES_T4 = ["core/risk_classifier.py", "core/optimized_activity_log.py", "core/lock_manager.py"]


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")
def test_T4_delta_cheaper_than_full_reread_claude_tokens(tmp_path, monkeypatch):
    fr = _freshness(tmp_path, monkeypatch)
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("NEO_TEST_MODEL", "claude-haiku-5-5")

    def count(text):
        r = client.messages.count_tokens(model=model, messages=[{"role": "user", "content": text}])
        return r.input_tokens

    rows = []
    for rel in FILES_T4:
        src = (ROOT / rel).read_text()
        f = tmp_path / Path(rel).name
        f.write_text(src)
        fr.record_read("agent_B", str(f))
        f.write_text(src + "\n\ndef _t4_probe():\n    return 1\n")  # one added symbol
        payload = fr.delta_since_base("agent_B", str(f))
        full_tokens = count(src)
        delta_tokens = count(payload)
        rows.append({"file": rel, "full_tokens": full_tokens, "delta_tokens": delta_tokens, "model": model})
        assert delta_tokens < full_tokens, f"{rel}: delta {delta_tokens} >= full {full_tokens}"
    print(json.dumps(rows, indent=2))


# ---------- T7: classifier regressions (supports C1 scoping) ----------

def test_T7_move_word_is_not_signature_change():
    assert detect_signature_change("Move the cursor blink animation") is False


def test_T7_remove_word_is_signature_change():
    assert detect_signature_change("Remove legacy helper") is True


def test_T7_same_name_different_class_not_overlapping():
    assert regions_overlap("A.validate", "B.validate") is False


def test_T7_same_class_same_method_overlaps():
    assert regions_overlap("A.validate", "A.validate") is True
