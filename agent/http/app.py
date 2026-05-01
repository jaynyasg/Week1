"""
Minimal FastAPI surface for Phase 2: session validation + per-tool RBAC before dispatch.

Mount this app at /agent behind Nginx in the full stack (see ARCHITECTURE.md).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from agent.access.rbac import ToolRefusal, assert_tool_allowed, log_tool_refusal
from agent.http.deps import resolve_agent_role

_LOG = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Clinical Co-Pilot Agent", version="0.1.0")

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
