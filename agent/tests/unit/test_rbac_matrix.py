"""Parameterized RBAC matrix vs USERS.md (Feature 8)."""

from __future__ import annotations

import logging

import pytest

from agent.access.rbac import (
    ADMIN_TOOLS,
    NURSE_TOOLS,
    TOOL_NAMES,
    ToolRefusal,
    assert_tool_allowed,
    assert_tools_allowed,
    canonical_agent_role,
    log_tool_refusal,
    refusal_message,
)
from agent.observability.events import LOG_EXTRA_EVENT, LOG_EXTRA_EVENT_TYPE


def _matrix_cases():
    for tool in sorted(TOOL_NAMES):
        yield ("PHYSICIAN", tool, True)
    for tool in sorted(TOOL_NAMES):
        yield ("NURSE", tool, tool in NURSE_TOOLS)
    for tool in sorted(TOOL_NAMES):
        yield ("CLINICIAN", tool, tool in NURSE_TOOLS)
    for tool in sorted(TOOL_NAMES):
        yield ("ADMIN", tool, tool in ADMIN_TOOLS)
    yield ("UNKNOWN", "demographics", False)
    yield ("PHYSICIAN", "not_a_tool", False)


@pytest.mark.parametrize("role,tool,allowed", list(_matrix_cases()))
def test_role_tool_matrix(role: str, tool: str, allowed: bool) -> None:
    if allowed:
        assert_tool_allowed(role, tool)
    else:
        with pytest.raises(ToolRefusal) as excinfo:
            assert_tool_allowed(role, tool)
        err = excinfo.value
        assert err.role == canonical_agent_role(role)
        assert err.tool == tool
        assert refusal_message(canonical_agent_role(role), tool) in str(err)


def test_refusal_message_names_role_and_tool() -> None:
    msg = refusal_message("NURSE", "labs")
    assert "NURSE" in msg
    assert "labs" in msg


def test_refusal_message_normalizes_clinician_alias() -> None:
    msg = refusal_message("CLINICIAN", "labs")
    assert "NURSE" in msg
    assert "labs" in msg


def test_assert_tools_allowed_partial_denial() -> None:
    with pytest.raises(ToolRefusal):
        assert_tools_allowed("NURSE", ["demographics", "labs"])
    with pytest.raises(ToolRefusal):
        assert_tools_allowed("CLINICIAN", ["demographics", "labs"])


def test_log_tool_refusal(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    log = logging.getLogger("rbac_test")
    log_tool_refusal(log, "ADMIN", "labs", patient_id_hash="abc", session_id_hash="def")
    rec = next(r for r in caplog.records if "tool_refusal" in r.message)
    assert getattr(rec, LOG_EXTRA_EVENT) == "tool_refusal"
    assert getattr(rec, LOG_EXTRA_EVENT_TYPE) == "tool_refusal"
    assert rec.role == "ADMIN"
    assert rec.tool == "labs"
