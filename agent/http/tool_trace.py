"""Summarize CSV tool executions for structured API responses (no full row payloads)."""

from __future__ import annotations

from typing import Any


def build_tool_execution_summary(tool_results: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Build a compact list from ``openai_tool_loop`` ``executions`` entries.

    Omits large arrays (medications, labs, vitals, allergies); callers use ``count`` / codes only.
    """
    raw = tool_results.get("executions")
    if not isinstance(raw, list) or not raw:
        return None
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fn = str(item.get("function") or "")
        res = item.get("result")
        if not isinstance(res, dict):
            res = {}
        err = res.get("error")
        row: dict[str, Any] = {
            "function": fn,
            "status": "error" if err else "ok",
            "error_code": err,
            "rbac_tool": res.get("rbac_tool"),
        }
        if err:
            out.append(row)
            continue
        if "last" in res or "first" in res:
            row["demographics"] = {
                "last": res.get("last"),
                "first": res.get("first"),
                "birthdate": res.get("birthdate"),
            }
        if "count" in res and "medications" in res:
            row["medications_count"] = res.get("count")
        if "count" in res and "labs" in res:
            row["labs_count"] = res.get("count")
        if "count" in res and "vitals" in res:
            row["vitals_count"] = res.get("count")
        if "count" in res and "allergies" in res:
            row["allergies_count"] = res.get("count")
        out.append(row)
    return out or None
