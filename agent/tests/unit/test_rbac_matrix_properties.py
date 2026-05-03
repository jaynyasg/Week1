"""Property-style checks for the USERS.md tool matrix (no matrix table duplication)."""

from __future__ import annotations

import pytest

from agent.access.rbac import (
    ADMIN_TOOLS,
    NURSE_TOOLS,
    PHYSICIAN_TOOLS,
    TOOL_NAMES,
    allowed_tools,
    is_tool_allowed,
)


@pytest.mark.parametrize("role", ["PHYSICIAN", "NURSE", "ADMIN", "CLINICIAN"])
def test_allowed_tools_subset_of_canonical_names(role: str) -> None:
    per_role = allowed_tools(role)
    assert per_role <= TOOL_NAMES
    assert per_role == per_role & TOOL_NAMES


def test_clinician_matches_nurse_toolset() -> None:
    assert allowed_tools("CLINICIAN") == allowed_tools("NURSE")


def test_physician_is_most_permissive_among_three_roles() -> None:
    assert NURSE_TOOLS <= PHYSICIAN_TOOLS
    assert ADMIN_TOOLS <= PHYSICIAN_TOOLS


def test_unknown_role_gets_empty_toolset() -> None:
    assert allowed_tools("GUEST") == frozenset()
    assert is_tool_allowed("GUEST", "demographics") is False


def test_unknown_tool_name_denied_even_for_physician() -> None:
    assert is_tool_allowed("PHYSICIAN", "not_a_real_tool") is False


def test_union_of_role_sets_covers_all_tool_names() -> None:
    assert PHYSICIAN_TOOLS | NURSE_TOOLS | ADMIN_TOOLS == TOOL_NAMES
