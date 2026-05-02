"""HTTP request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

_MAX_HISTORY_MESSAGES = 500


class ChatRequest(BaseModel):
    patient_id: str = Field(
        ..., min_length=1, description="Scoped patient for this turn"
    )
    user_message: str = Field(..., min_length=1, description="Latest clinician message")
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prior OpenAI-style messages for multi-turn continuity",
    )

    @field_validator("messages")
    @classmethod
    def cap_message_history(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) > _MAX_HISTORY_MESSAGES:
            raise ValueError(
                f"messages may contain at most {_MAX_HISTORY_MESSAGES} items"
            )
        return v


class ChatResponse(BaseModel):
    assistant_message: str = Field(..., description="Model reply for this turn")
    verified: bool = Field(
        ..., description="Whether verify() accepted the generated text"
    )
    verification_notes: list[str] = Field(
        default_factory=list,
        description="Human-readable verify notes (may include retry reasons)",
    )
    verify_retry_count: int = Field(
        ..., description="Number of verify failures before success or give-up"
    )
    tool_result_keys: list[str] = Field(
        default_factory=list,
        description="Sorted keys from the retrieve step tool bundle",
    )
    tool_execution_summary: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "When AGENT_LLM_CSV_TOOLS is on, a compact per-function trace "
            "(status, counts, demographics headline) — not full FHIR rows."
        ),
    )
    messages: list[dict[str, Any]] = Field(
        ...,
        description="Full transcript including the new user + assistant turns",
    )
