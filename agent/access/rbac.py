"""
Role-based access for patient-context tools (PRD Feature 8 / USERS.md).

Enforcement belongs on the agent retrieve/dispatch path before any tool runs.
"""

from __future__ import annotations

import logging
from typing import Final, Iterable

from agent.observability.events import LOG_EXTRA_EVENT, LOG_EXTRA_EVENT_TYPE

# Canonical tool identifiers — must match USERS.md matrix.
PHYSICIAN_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "demographics",
        "problem_list",
        "medications",
        "labs",
        "vitals",
        "allergies",
        "visit_notes",
        "schedule",
    }
)
NURSE_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "demographics",
        "medications",
        "vitals",
        "allergies",
        "schedule",
    }
)
ADMIN_TOOLS: Final[frozenset[str]] = frozenset({"demographics", "schedule"})
TOOL_NAMES: Final[frozenset[str]] = frozenset(
    PHYSICIAN_TOOLS | NURSE_TOOLS | ADMIN_TOOLS
)


class ToolRefusal(Exception):
    """Raised when a role may not invoke a tool (explicit deny, not silent filter)."""

    def __init__(self, message: str, *, role: str, tool: str) -> None:
        super().__init__(message)
        self.role = role
        self.tool = tool


def refusal_message(role: str, tool: str) -> str:
    return f"Role {role} is not permitted to use tool {tool!r}."


def allowed_tools(user_role: str) -> frozenset[str]:
    if user_role == "PHYSICIAN":
        return PHYSICIAN_TOOLS
    if user_role == "NURSE":
        return NURSE_TOOLS
    if user_role == "ADMIN":
        return ADMIN_TOOLS
    return frozenset()


def is_tool_allowed(user_role: str, tool: str) -> bool:
    if tool not in TOOL_NAMES:
        return False
    return tool in allowed_tools(user_role)


def assert_tool_allowed(user_role: str, tool: str) -> None:
    if tool not in TOOL_NAMES:
        raise ToolRefusal(refusal_message(user_role, tool), role=user_role, tool=tool)
    if tool not in allowed_tools(user_role):
        raise ToolRefusal(refusal_message(user_role, tool), role=user_role, tool=tool)


def assert_tools_allowed(user_role: str, tools: Iterable[str]) -> None:
    for tool in tools:
        assert_tool_allowed(user_role, tool)


def log_tool_refusal(
    logger: logging.Logger,
    role: str,
    tool: str,
    *,
    patient_id_hash: str | None = None,
    session_id_hash: str | None = None,
) -> None:
    """Structured refusal log — no raw PHI; identifiers should be hashed upstream."""
    logger.info(
        "tool_refusal role=%s tool=%s patient_id_hash=%s session_id_hash=%s",
        role,
        tool,
        patient_id_hash or "",
        session_id_hash or "",
        extra={
            LOG_EXTRA_EVENT: "tool_refusal",
            LOG_EXTRA_EVENT_TYPE: "tool_refusal",
            "role": role,
            "tool": tool,
            "patient_id_hash": patient_id_hash,
            "session_id_hash": session_id_hash,
            "what": "rbac_tool_denied",
            "why": "role_tool_matrix",
            "duration_ms": 0.0,
            "fallback": "none",
            "cost_envelope": "unknown",
        },
    )
