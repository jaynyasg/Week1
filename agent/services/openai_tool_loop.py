"""
OpenAI Chat Completions with **model-chosen tools** (CSV cohort backend).

Enable with ``AGENT_LLM_CSV_TOOLS=1`` and ``OPENAI_API_KEY``. The model may call
one or more of the five RBAC-aligned functions in ``agent.tools.dispatch``; each
execution is authorized with ``assert_tool_allowed`` and scoped to
``ClinicalTurnState.patient_id``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agent.access.rbac import ToolRefusal
from agent.runtime.rgv_pipeline import ClinicalTurnState
from agent.services.openai_generate import DEFAULT_SYSTEM_PROMPT
from agent.tools.dispatch import (
    execute_tool_function,
    handle_tool_refusal,
    openai_tool_schemas,
)
from agent.tools.csv_cohort import get_cohort_store

_LOG = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 10


def _system_prompt_tool_mode(state: ClinicalTurnState) -> str:
    base = os.environ.get("AGENT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()
    return (
        f"{base}\n\n"
        "You have access to clinical **tools** (function calls). "
        "Call only the tools you need; prefer minimal calls. "
        "Always pass patient_id exactly as given in the session line. "
        "Do not invent patient identifiers.\n\n"
        f"Session: patient_id={state.patient_id!r}, user_role={state.user_role!r}, "
        f"session_id={state.session_id!r}."
    )


def _transcript_without_retrieve_blob(state: ClinicalTurnState) -> list[dict[str, Any]]:
    """User/assistant messages for OpenAI (no pre-baked retrieve JSON)."""
    out: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt_tool_mode(state)}]
    for m in state.messages:
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or content is None:
            continue
        out.append({"role": str(role), "content": str(content)})
    return out


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """Serialize assistant message (possibly with ``tool_calls``) for the next API round."""
    out: dict[str, Any] = {"role": getattr(msg, "role", "assistant")}
    content = getattr(msg, "content", None)
    if content:
        out["content"] = content
    tool_calls = getattr(msg, "tool_calls", None) or []
    if tool_calls:
        serialized: list[dict[str, Any]] = []
        for tc in tool_calls:
            fn = getattr(tc, "function", None)
            serialized.append(
                {
                    "id": getattr(tc, "id", ""),
                    "type": getattr(tc, "type", "function"),
                    "function": {
                        "name": getattr(fn, "name", "") if fn else "",
                        "arguments": getattr(fn, "arguments", "") if fn else "",
                    },
                }
            )
        out["tool_calls"] = serialized
    return out


def complete_chat_openai_with_csv_tools(state: ClinicalTurnState) -> str:
    """Run chat completions with tool loop; mutates ``state.tool_results`` with traces."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)
    messages: list[dict[str, Any]] = _transcript_without_retrieve_blob(state)
    tools = openai_tool_schemas()
    store = get_cohort_store()
    merged_results: dict[str, Any] = {"csv_tools": [], "patient_id": state.patient_id}

    for round_i in range(_MAX_TOOL_ROUNDS):
        _LOG.debug("openai_tool_round=%d messages=%d", round_i, len(messages))
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=1200,
            temperature=0.2,
        )
        choice = resp.choices[0].message
        tool_calls = getattr(choice, "tool_calls", None) or []
        if not tool_calls:
            text = (choice.content or "").strip()
            if not text:
                raise RuntimeError("OpenAI returned empty content (no tool calls)")
            state.tool_results = merged_results
            return text

        messages.append(_message_to_dict(choice))
        for call in tool_calls:
            fn = getattr(call, "function", None)
            name = getattr(fn, "name", "") if fn else ""
            raw_args = getattr(fn, "arguments", "") if fn else ""
            call_id = getattr(call, "id", "") or ""
            try:
                payload = execute_tool_function(
                    function_name=name,
                    arguments_json=raw_args or "{}",
                    user_role=state.user_role,
                    session_patient_id=state.patient_id,
                    store=store,
                )
            except ToolRefusal as exc:
                payload = handle_tool_refusal(exc)
            merged_results.setdefault("executions", []).append(
                {"function": name, "result": payload}
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(payload, default=str, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"Exceeded {_MAX_TOOL_ROUNDS} tool rounds without final content")
