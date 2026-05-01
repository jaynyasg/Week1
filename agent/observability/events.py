"""Structured agent events for logs / future Langfuse (Phase 4)."""

from __future__ import annotations

import logging
from typing import Any


def log_agent_event(
    logger: logging.Logger,
    event_type: str,
    **fields: Any,
) -> None:
    """Emit a single structured log line + ``extra`` for downstream collectors."""
    flat = " ".join(f"{k}={v!r}" for k, v in sorted(fields.items()))
    logger.info("agent_event type=%s %s", event_type, flat, extra={"event_type": event_type, **fields})
