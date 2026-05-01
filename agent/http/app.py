"""
Minimal FastAPI surface: OpenEMR session validation, per-tool RBAC, and Phase 3 scaffold chat (RGV).

Mount this app at /agent behind Nginx in the full stack (see ARCHITECTURE.md).
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from agent.access.rbac import ToolRefusal, assert_tool_allowed, log_tool_refusal
from agent.http.deps import resolve_agent_role
from agent.observability.metrics_counters import render_prometheus
from agent.http.env import load_dotenv_if_present
from agent.http.middleware_body_limit import body_too_large_response
from agent.http.routes_chat import chat_turn
from agent.http.schemas import ChatResponse

_LOG = logging.getLogger(__name__)


def _http_client_timeout_seconds() -> float:
    raw = (os.environ.get("OPENEMR_HTTP_TIMEOUT_SECONDS") or "30").strip() or "30"
    return max(1.0, float(raw))


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
    async with httpx.AsyncClient(
        timeout=_http_client_timeout_seconds(),
        follow_redirects=True,
    ) as client:
        app.state.http_client = client
        yield


def create_app() -> FastAPI:
    chat_limit = os.environ.get("AGENT_RATE_LIMIT_CHAT", "").strip()
    limiter = None
    if chat_limit:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address)
        app = FastAPI(
            title="Clinical Co-Pilot Agent",
            version="0.1.0",
            lifespan=_lifespan,
            openapi_tags=[
                {
                    "name": "health",
                    "description": "Process liveness and optional readiness signals.",
                },
                {"name": "chat", "description": "Scaffold RGV conversational turns."},
                {"name": "tools", "description": "RBAC-gated tool invocation stubs."},
                {
                    "name": "observability",
                    "description": "Prometheus-style metrics (stub).",
                },
            ],
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
    else:
        app = FastAPI(
            title="Clinical Co-Pilot Agent",
            version="0.1.0",
            lifespan=_lifespan,
            openapi_tags=[
                {
                    "name": "health",
                    "description": "Process liveness and optional readiness signals.",
                },
                {"name": "chat", "description": "Scaffold RGV conversational turns."},
                {"name": "tools", "description": "RBAC-gated tool invocation stubs."},
                {
                    "name": "observability",
                    "description": "Prometheus-style metrics (stub).",
                },
            ],
        )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        early = body_too_large_response(request)
        if early is not None:
            return early
        incoming = (
            request.headers.get("x-request-id")
            or request.headers.get("x-correlation-id")
            or request.headers.get("x-trace-id")
        )
        rid = (incoming or "").strip()[:128] or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

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

    @app.get(
        "/agent/health",
        tags=["health"],
        summary="Liveness probe",
        response_description="Process is running and accepting HTTP.",
    )
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/agent/health/ready",
        tags=["health"],
        summary="Readiness hints",
        response_description="Configuration snapshot for orchestrators (always 200).",
    )
    async def ready() -> dict[str, str | bool]:
        openemr = bool(os.environ.get("OPENEMR_BASE_URL", "").strip())
        return {
            "status": "ready",
            "openemr_base_url_configured": openemr,
        }

    @app.get(
        "/agent/metrics",
        tags=["observability"],
        summary="Prometheus metrics (stub)",
        response_class=PlainTextResponse,
    )
    async def metrics() -> PlainTextResponse:
        body = (
            "# HELP clinical_agent_up Process is accepting HTTP\n"
            "# TYPE clinical_agent_up gauge\n"
            "clinical_agent_up 1\n" + render_prometheus()
        )
        return PlainTextResponse(
            body,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    chat_endpoint: Callable[..., object] = chat_turn
    if limiter is not None and chat_limit:
        chat_endpoint = limiter.limit(chat_limit)(chat_turn)

    app.add_api_route(
        "/agent/chat",
        chat_endpoint,
        methods=["POST"],
        response_model=ChatResponse,
        tags=["chat"],
        summary="Run one RGV chat turn",
        description=(
            "Prior messages plus a new user_message run through retrieve → generate → verify. "
            "Requires OpenEMR session headers unless demo bypass is enabled on the server."
        ),
    )

    @app.post(
        "/agent/tools/{tool_name}",
        tags=["tools"],
        summary="RBAC gate for a named tool",
        response_description="Acknowledgement when the role may invoke the tool.",
    )
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
