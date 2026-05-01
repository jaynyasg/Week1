"""
In-process Prometheus-style counters (thread-safe integers).

Export via ``render_prometheus()`` for ``/agent/metrics``; use ``snapshot()`` for tests.
"""

from __future__ import annotations

import threading
from typing import Final

_lock = threading.Lock()

_chat_turns_total: int = 0
_tool_refusals_total: int = 0
_verify_failures_total: int = 0
_rgv_degraded_total: int = 0
_category_boundary_flags_total: int = 0
_openemr_auth_failures_total: int = 0
_openemr_misconfiguration_total: int = 0
_client_missing_credentials_total: int = 0


def inc_chat_turn() -> None:
    global _chat_turns_total
    with _lock:
        _chat_turns_total += 1


def inc_tool_refusal() -> None:
    global _tool_refusals_total
    with _lock:
        _tool_refusals_total += 1


def inc_verify_failure() -> None:
    global _verify_failures_total
    with _lock:
        _verify_failures_total += 1


def inc_rgv_degraded() -> None:
    global _rgv_degraded_total
    with _lock:
        _rgv_degraded_total += 1


def inc_category_boundary() -> None:
    global _category_boundary_flags_total
    with _lock:
        _category_boundary_flags_total += 1


def inc_openemr_auth_failure() -> None:
    global _openemr_auth_failures_total
    with _lock:
        _openemr_auth_failures_total += 1


def inc_openemr_misconfiguration() -> None:
    global _openemr_misconfiguration_total
    with _lock:
        _openemr_misconfiguration_total += 1


def inc_client_missing_credentials() -> None:
    global _client_missing_credentials_total
    with _lock:
        _client_missing_credentials_total += 1


def snapshot() -> dict[str, int]:
    with _lock:
        return {
            "chat_turns_total": _chat_turns_total,
            "tool_refusals_total": _tool_refusals_total,
            "verify_failures_total": _verify_failures_total,
            "rgv_degraded_total": _rgv_degraded_total,
            "category_boundary_flags_total": _category_boundary_flags_total,
            "openemr_auth_failures_total": _openemr_auth_failures_total,
            "openemr_misconfiguration_total": _openemr_misconfiguration_total,
            "client_missing_credentials_total": _client_missing_credentials_total,
        }


_METRIC_META: Final[list[tuple[str, str]]] = [
    ("chat_turns_total", "Completed scaffold chat turns after RGV."),
    ("tool_refusals_total", "RBAC tool invocations refused."),
    (
        "verify_failures_total",
        "RGV verification failures (each failed verify attempt).",
    ),
    ("rgv_degraded_total", "RGV turns ending in unverified degraded path."),
    ("category_boundary_flags_total", "Category boundary review events logged."),
    ("openemr_auth_failures_total", "OpenEMR session validation failures."),
    (
        "openemr_misconfiguration_total",
        "OpenEMR base URL / config misconfiguration signals.",
    ),
    (
        "client_missing_credentials_total",
        "Chat/tool requests with neither Authorization nor Cookie header.",
    ),
]


def render_prometheus() -> str:
    snap = snapshot()
    lines: list[str] = []
    for name, help_text in _METRIC_META:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {snap[name]}")
    return "\n".join(lines) + "\n"


def reset_counters_for_testing() -> None:
    """Zero all counters (test-only; not for production use)."""
    global _chat_turns_total, _tool_refusals_total, _verify_failures_total
    global _rgv_degraded_total, _category_boundary_flags_total
    global _openemr_auth_failures_total, _openemr_misconfiguration_total
    global _client_missing_credentials_total
    with _lock:
        _chat_turns_total = 0
        _tool_refusals_total = 0
        _verify_failures_total = 0
        _rgv_degraded_total = 0
        _category_boundary_flags_total = 0
        _openemr_auth_failures_total = 0
        _openemr_misconfiguration_total = 0
        _client_missing_credentials_total = 0
