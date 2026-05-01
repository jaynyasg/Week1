"""Stable OpenAPI surface for /agent/* (guards accidental route renames)."""

from __future__ import annotations

from agent.http.app import create_app


def test_openapi_includes_core_agent_paths_and_methods() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]
    assert "/agent/health" in paths
    assert "get" in paths["/agent/health"]
    assert "/agent/health/ready" in paths
    assert "get" in paths["/agent/health/ready"]
    assert "/agent/metrics" in paths
    assert "get" in paths["/agent/metrics"]
    assert "/agent/chat" in paths
    assert "post" in paths["/agent/chat"]
    assert "/agent/tools/{tool_name}" in paths
    assert "post" in paths["/agent/tools/{tool_name}"]


def test_openapi_tags_include_expected_groups() -> None:
    schema = create_app().openapi()
    tags = {t["name"] for t in schema.get("tags", [])}
    for name in ("health", "chat", "tools", "observability"):
        assert name in tags
