"""Structured agent events for logs / future Langfuse (Phase 4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

# Stable keys on LogRecord.extra for downstream JSON formatters / exporters.
LOG_EXTRA_EVENT = "event"
LOG_EXTRA_EVENT_TYPE = "event_type"


def log_agent_event(
    logger: logging.Logger,
    event_type: str,
    *,
    extra: Mapping[str, Any] | None = None,
    **fields: Any,
) -> None:
    """
    Emit a single structured log line and ``extra`` for downstream collectors.

    ``event_type`` is retained for backward compatibility; ``extra`` on the
    record always includes both ``event`` and ``event_type`` (same value) so
    Phase 4 tooling can standardize on ``event`` without breaking older parsers.
    """
    passthrough = dict(extra) if extra else {}
    merged: dict[str, Any] = {
        **fields,
        **passthrough,
        LOG_EXTRA_EVENT: event_type,
        LOG_EXTRA_EVENT_TYPE: event_type,
    }
    flat = " ".join(f"{k}={v!r}" for k, v in sorted(fields.items()))
    logger.info("agent_event %s=%r %s", LOG_EXTRA_EVENT, event_type, flat, extra=merged)


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Immutable structured event; call ``emit`` to write via ``log_agent_event``."""

    event: str
    fields: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def emit(self, logger: logging.Logger) -> None:
        log_agent_event(logger, self.event, extra=self.extra, **self.fields)
