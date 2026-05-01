"""HTTP request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, description="Scoped patient for this turn")
    user_message: str = Field(..., min_length=1, description="Latest clinician message")
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prior OpenAI-style messages for multi-turn continuity",
    )


class ChatResponse(BaseModel):
    assistant_message: str
    verified: bool
    verification_notes: list[str]
    verify_retry_count: int
    tool_result_keys: list[str]
    messages: list[dict[str, Any]]
