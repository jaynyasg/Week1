"""
OpenAI Chat Completions for the scaffold RGV generate step.

``OPENAI_API_KEY`` must be set (e.g. Fly secret) for live calls. Model defaults to
``gpt-4o-mini``; override with ``OPENAI_CHAT_MODEL``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agent.runtime.rgv_pipeline import ClinicalTurnState

_LOG = logging.getLogger(__name__)

# Demo-grade system prompt; replace with policy-tuned prompt in production fork.
DEFAULT_SYSTEM_PROMPT = (
    "You are Clinical Co-Pilot (demo scaffold): a concise clinical documentation "
    "assistant. You are not a licensed clinician; do not diagnose or prescribe. "
    "Use the retrieve context JSON when relevant. Answer in plain language, "
    "short paragraphs or bullets unless the user asks otherwise."
)


def _tool_context_block(tool_results: dict[str, Any]) -> str:
    try:
        blob = json.dumps(tool_results, default=str, ensure_ascii=False)
    except TypeError:
        blob = repr(tool_results)
    if len(blob) > 12_000:
        blob = blob[:12_000] + "\n…(truncated)"
    return f"Retrieve context (JSON):\n{blob}"


def build_chat_messages(state: ClinicalTurnState) -> list[dict[str, str]]:
    """Map ``ClinicalTurnState`` to OpenAI ``messages`` (system + transcript)."""
    system = os.environ.get("AGENT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()
    system = system + "\n\n" + _tool_context_block(state.tool_results)
    system += (
        f"\n\nSession: patient_id={state.patient_id!r}, user_role={state.user_role!r}, "
        f"session_id={state.session_id!r}."
    )
    out: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in state.messages:
        role = m.get("role")
        content = m.get("content")
        # Ignore client-supplied "system" so our policy prompt cannot be overridden.
        if role not in ("user", "assistant") or content is None:
            continue
        out.append({"role": str(role), "content": str(content)})
    return out


def complete_chat_openai(state: ClinicalTurnState) -> str:
    """Synchronous Chat Completions call; raises on API/SDK errors."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)
    messages = build_chat_messages(state)
    _LOG.debug("openai_chat_request model=%s messages=%d", model, len(messages))
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1024,
        temperature=0.2,
    )
    choice = resp.choices[0].message
    text = (choice.content or "").strip()
    if not text:
        raise RuntimeError("OpenAI returned empty content")
    return text
