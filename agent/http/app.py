"""
Minimal FastAPI surface: OpenEMR session validation, per-tool RBAC, and Phase 3 scaffold chat (RGV).

Mount this app at /agent behind Nginx in the full stack (see ARCHITECTURE.md).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.access.rbac import ToolRefusal, assert_tool_allowed, log_tool_refusal
from agent.http.deps import get_chat_turn_runner, resolve_agent_role
from agent.http.env import load_dotenv_if_present
from agent.http.schemas import ChatRequest, ChatResponse
from agent.services.chat_turn import new_session_id

_LOG = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str] | None:
    """Comma-separated origins, or ``*`` for any origin (demo only; no credentials)."""
    raw = os.environ.get("AGENT_CORS_ORIGINS", "").strip()
    if not raw:
        return None
    if raw == "*":
        return ["*"]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    load_dotenv_if_present()
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        app.state.http_client = client
        yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Clinical Co-Pilot Agent",
        version="0.1.0",
        lifespan=_lifespan,
    )

    cors = _parse_cors_origins()
    if cors:
        allow_all = cors == ["*"]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"] if allow_all else cors,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(ToolRefusal)
    async def _tool_refusal(_request: Request, exc: ToolRefusal) -> JSONResponse:
        log_tool_refusal(_LOG, exc.role, exc.tool)
        return JSONResponse(
            status_code=403,
            content={
                "error": "tool_refusal",
                "role": exc.role,
                "tool": exc.tool,
                "message": str(exc),
            },
        )

    @app.get("/agent/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/agent/chat", response_model=ChatResponse)
    async def chat(
        body: ChatRequest,
        role: Annotated[str, Depends(resolve_agent_role)],
        run_turn: Annotated[Callable[..., object], Depends(get_chat_turn_runner)],
        x_session: Annotated[str | None, Header(alias="X-Clinical-Session-Id")] = None,
    ) -> ChatResponse:
        """
        Multi-turn scaffold: prior ``messages`` + new ``user_message`` → RGV → assistant reply.

        Full stack replaces scaffold retrieve/generate/verify with LangGraph + LLM + rules.
        """
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
            messages=st.messages,
        )

    @app.post("/agent/tools/{tool_name}")
    async def invoke_tool(
        tool_name: str,
        role: Annotated[str, Depends(resolve_agent_role)],
    ) -> dict[str, str]:
        """
        Thin RBAC gate: real retrieve/graph code would run after this check.

        Kept synchronous RBAC for clarity; graph remains async in full implementation.
        """
        assert_tool_allowed(role, tool_name)
        return {"status": "ok", "role": role, "tool": tool_name}

    return app
