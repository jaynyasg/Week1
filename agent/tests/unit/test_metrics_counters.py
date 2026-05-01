"""Unit tests for in-process Prometheus-style counters."""

from __future__ import annotations

import pytest

from agent.observability.metrics_counters import (
    inc_category_boundary,
    inc_chat_turn,
    inc_openemr_auth_failure,
    inc_openemr_misconfiguration,
    inc_rgv_degraded,
    inc_tool_refusal,
    inc_verify_failure,
    render_prometheus,
    reset_counters_for_testing,
    snapshot,
)


@pytest.fixture(autouse=True)
def _clean_counters() -> None:
    reset_counters_for_testing()
    yield
    reset_counters_for_testing()


def test_increment_and_snapshot() -> None:
    assert snapshot()["chat_turns_total"] == 0
    inc_chat_turn()
    inc_chat_turn()
    inc_tool_refusal()
    inc_verify_failure()
    inc_rgv_degraded()
    inc_category_boundary()
    inc_openemr_auth_failure()
    inc_openemr_misconfiguration()
    s = snapshot()
    assert s["chat_turns_total"] == 2
    assert s["tool_refusals_total"] == 1
    assert s["verify_failures_total"] == 1
    assert s["rgv_degraded_total"] == 1
    assert s["category_boundary_flags_total"] == 1
    assert s["openemr_auth_failures_total"] == 1
    assert s["openemr_misconfiguration_total"] == 1


def test_render_prometheus_includes_help_type_and_values() -> None:
    inc_chat_turn()
    text = render_prometheus()
    assert "# HELP chat_turns_total" in text
    assert "# TYPE chat_turns_total counter" in text
    assert "\nchat_turns_total 1\n" in text or text.endswith("chat_turns_total 1\n")
    for name in (
        "tool_refusals_total",
        "verify_failures_total",
        "rgv_degraded_total",
        "category_boundary_flags_total",
        "openemr_auth_failures_total",
        "openemr_misconfiguration_total",
    ):
        assert f"# TYPE {name} counter" in text
        assert f"{name} 0" in text
