"""Map OpenAI function names → RBAC tool ids and execute against CSV cohort."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.access.rbac import ToolRefusal, assert_tool_allowed
from agent.tools.csv_cohort import CsvCohortStore, get_cohort_store

_LOG = logging.getLogger(__name__)

# OpenAI function name → RBAC tool name (must exist in rbac.TOOL_NAMES)
FUNCTION_TO_RBAC: dict[str, str] = {
    "get_patient_demographics": "demographics",
    "list_active_medications": "medications",
    "list_recent_laboratory_results": "labs",
    "list_recent_vital_signs": "vitals",
    "list_allergies": "allergies",
}


def openai_tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI Chat Completions ``tools`` list."""
    pid = {
        "type": "string",
        "description": "Patient UUID; must match the active chart session.",
    }
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {"patient_id": pid},
                    "required": ["patient_id"],
                },
            },
        }
        for name, desc in (
            (
                "get_patient_demographics",
                "Return name, DOB, gender, race/ethnicity, and city/state for one patient.",
            ),
            (
                "list_active_medications",
                "Return active medication rows (description, dates, RxNorm-like code).",
            ),
            (
                "list_recent_laboratory_results",
                "Return recent laboratory Observation rows for the patient.",
            ),
            (
                "list_recent_vital_signs",
                "Return recent vital-sign Observation rows (BP, HR, weight, etc.).",
            ),
            (
                "list_allergies",
                "Return allergy / intolerance rows for the patient.",
            ),
        )
    ]


def execute_tool_function(
    *,
    function_name: str,
    arguments_json: str,
    user_role: str,
    session_patient_id: str,
    store: CsvCohortStore | None = None,
) -> dict[str, Any]:
    """Execute one tool call with RBAC + patient scope enforcement."""
    rbac_tool = FUNCTION_TO_RBAC.get(function_name)
    if rbac_tool is None:
        return {"error": "unknown_function", "function": function_name}
    assert_tool_allowed(user_role, rbac_tool)
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as exc:
        return {"error": "invalid_arguments_json", "detail": str(exc)}
    arg_pid = (args.get("patient_id") or "").strip()
    if arg_pid != session_patient_id:
        return {
            "error": "patient_scope_violation",
            "detail": "Tool patient_id must match the active session patient_id.",
            "expected": session_patient_id,
            "got": arg_pid,
        }
    st = store or get_cohort_store()
    if function_name == "get_patient_demographics":
        payload = st.demographics_payload(session_patient_id)
    elif function_name == "list_active_medications":
        payload = st.medications_payload(session_patient_id)
    elif function_name == "list_recent_laboratory_results":
        payload = st.labs_payload(session_patient_id)
    elif function_name == "list_recent_vital_signs":
        payload = st.vitals_payload(session_patient_id)
    elif function_name == "list_allergies":
        payload = st.allergies_payload(session_patient_id)
    else:
        payload = {"error": "unhandled_function"}
    payload["rbac_tool"] = rbac_tool
    _LOG.info("csv_tool_executed function=%s rbac_tool=%s", function_name, rbac_tool)
    return payload


def handle_tool_refusal(exc: ToolRefusal) -> dict[str, Any]:
    return {
        "error": "rbac_refusal",
        "role": exc.role,
        "tool": exc.tool,
        "message": str(exc),
    }
