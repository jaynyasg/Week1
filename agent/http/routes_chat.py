"""POST /agent/chat handler (extracted for optional SlowAPI rate-limit wrapper)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request

from agent.http.deps import get_chat_turn_runner, resolve_agent_role
from agent.http.schemas import ChatRequest, ChatResponse
from agent.http.tool_trace import build_tool_execution_summary
from agent.services.chat_turn import new_session_id


async def chat_turn(
    request: Request,  # noqa: ARG001 - required by slowapi rate-limit wrapper
    body: ChatRequest,
    role: Annotated[str, Depends(resolve_agent_role)],
    run_turn: Annotated[Callable[..., object], Depends(get_chat_turn_runner)],
    x_session: Annotated[str | None, Header(alias="X-Clinical-Session-Id")] = None,
) -> ChatResponse:
    session_id = (x_session or "").strip() or new_session_id()
    st, assistant = run_turn(
        patient_id=body.patient_id,
        user_role=role,
        session_id=session_id,
        messages=body.messages,
        user_message=body.user_message,
    )
    return ChatResponse(
        assistant_message=assistant,
        verified=st.verified,
        verification_notes=list(st.verification_notes),
        verify_retry_count=st.verify_retry_count,
        tool_result_keys=sorted(st.tool_results.keys()),
        tool_execution_summary=build_tool_execution_summary(st.tool_results),
        messages=st.messages,
    )
