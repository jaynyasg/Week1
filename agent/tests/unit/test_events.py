from __future__ import annotations

import logging

import pytest

from agent.observability.events import (
    LOG_EXTRA_EVENT,
    LOG_EXTRA_EVENT_TYPE,
    AgentEvent,
    log_agent_event,
)


@pytest.fixture
def caplog_events(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO)
    return caplog


def test_log_agent_event_happy_path_sets_stable_extra(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    log_agent_event(
        log,
        "chat_turn_complete",
        verified=True,
        verify_retry_count=0,
        patient_id="p1",
        session_id="s1",
    )
    assert len(caplog_events.records) == 1
    r = caplog_events.records[0]
    assert getattr(r, LOG_EXTRA_EVENT) == "chat_turn_complete"
    assert getattr(r, LOG_EXTRA_EVENT_TYPE) == "chat_turn_complete"
    assert getattr(r, "verified") is True
    assert getattr(r, "verify_retry_count") == 0
    assert getattr(r, "patient_id") == "p1"
    assert getattr(r, "session_id") == "s1"
    assert "agent_event" in r.getMessage()


def test_log_agent_event_empty_optionals(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    log_agent_event(log, "minimal")
    assert len(caplog_events.records) == 1
    r = caplog_events.records[0]
    assert getattr(r, LOG_EXTRA_EVENT) == "minimal"
    assert getattr(r, LOG_EXTRA_EVENT_TYPE) == "minimal"


def test_log_agent_event_extra_passthrough(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    log_agent_event(
        log,
        "with_extra",
        trace_id="abc",
        extra={"langfuse_trace": "lf-1", "nested": {"k": 1}},
    )
    r = caplog_events.records[0]
    assert getattr(r, "trace_id") == "abc"
    assert getattr(r, "langfuse_trace") == "lf-1"
    assert getattr(r, "nested") == {"k": 1}
    assert getattr(r, LOG_EXTRA_EVENT) == "with_extra"


def test_log_agent_event_reserved_keys_win(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    log_agent_event(
        log,
        "canonical",
        extra={"event": "spoof", "event_type": "spoof_type"},
    )
    r = caplog_events.records[0]
    assert getattr(r, LOG_EXTRA_EVENT) == "canonical"
    assert getattr(r, LOG_EXTRA_EVENT_TYPE) == "canonical"


def test_agent_event_emit_happy_path(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    ev = AgentEvent(
        event="turn_start",
        fields={"session_id": "s2"},
        extra={"source": "unit"},
    )
    ev.emit(log)
    r = caplog_events.records[0]
    assert getattr(r, LOG_EXTRA_EVENT) == "turn_start"
    assert getattr(r, "session_id") == "s2"
    assert getattr(r, "source") == "unit"


def test_agent_event_empty_fields_and_extra(caplog_events: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("agent.tests.unit.events_under_test")
    AgentEvent(event="noop").emit(log)
    r = caplog_events.records[0]
    assert getattr(r, LOG_EXTRA_EVENT) == "noop"
    assert getattr(r, LOG_EXTRA_EVENT_TYPE) == "noop"


def test_demo_bypass_active_constant_exists() -> None:
    """``DEMO_BYPASS_ACTIVE`` is the stable taxonomy key for demo-mode auth bypass.

    Operators grep on ``event_type=auth_demo_bypass`` in ``fly logs``; the
    constant value MUST stay ``"auth_demo_bypass"`` for that contract.
    """
    from agent.observability.taxonomy import DEMO_BYPASS_ACTIVE

    assert DEMO_BYPASS_ACTIVE == "auth_demo_bypass"
