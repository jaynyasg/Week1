"""Structured tool execution summaries for /agent/chat."""

from __future__ import annotations

from agent.http.tool_trace import build_tool_execution_summary


def test_summary_none_when_no_executions() -> None:
    assert build_tool_execution_summary({}) is None
    assert build_tool_execution_summary({"executions": []}) is None


def test_summary_demographics_ok() -> None:
    out = build_tool_execution_summary(
        {
            "executions": [
                {
                    "function": "get_patient_demographics",
                    "result": {
                        "rbac_tool": "demographics",
                        "last": "Brekke496",
                        "first": "Wilford830",
                        "birthdate": "1980-01-01",
                    },
                }
            ]
        }
    )
    assert out is not None
    assert out[0]["function"] == "get_patient_demographics"
    assert out[0]["status"] == "ok"
    assert out[0]["demographics"]["last"] == "Brekke496"


def test_summary_rbac_error() -> None:
    out = build_tool_execution_summary(
        {
            "executions": [
                {
                    "function": "list_recent_laboratory_results",
                    "result": {"error": "rbac_refusal", "tool": "labs"},
                }
            ]
        }
    )
    assert out is not None
    assert out[0]["status"] == "error"
    assert out[0]["error_code"] == "rbac_refusal"
