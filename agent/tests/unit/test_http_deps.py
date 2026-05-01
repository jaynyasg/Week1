"""Unit tests for ``agent.http.deps`` helpers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from agent.http.deps import _client_request_id, get_openemr_base_url
from agent.observability.events import LOG_EXTRA_EVENT
from agent.observability.taxonomy import OPENEMR_MISCONFIGURATION


def test_get_openemr_base_url_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "")
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


@pytest.mark.parametrize(
    "value",
    ["   ", "\t\n  ", "///"],
)
def test_get_openemr_base_url_raises_when_whitespace_or_slash_only(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", value)
    with pytest.raises(HTTPException) as exc_info:
        get_openemr_base_url()
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OPENEMR_BASE_URL is not configured"


def test_get_openemr_base_url_strips_trailing_slashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com/")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_multiple_trailing_slashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://openemr.example.com///")
    assert get_openemr_base_url() == "https://openemr.example.com"


def test_get_openemr_base_url_strips_outer_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "  https://host/openemr/  ")
    assert get_openemr_base_url() == "https://host/openemr"


def test_get_openemr_base_url_unchanged_without_trailing_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENEMR_BASE_URL", "https://host/path")
    assert get_openemr_base_url() == "https://host/path"


def test_client_request_id_prefers_first_header() -> None:
    req = MagicMock()
    req.headers.get = lambda name, default=None: {
        "X-Request-ID": "rid",
        "X-Correlation-ID": "cid",
    }.get(name, default)
    assert _client_request_id(req) == "rid"


def test_get_openemr_base_url_misconfig_includes_client_request_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("OPENEMR_BASE_URL", raising=False)
    caplog.set_level(logging.INFO)
    req = MagicMock()
    req.headers.get = lambda name, default=None: {"X-Request-ID": "unit-req-7"}.get(name, default)
    with pytest.raises(HTTPException):
        get_openemr_base_url(req)
    mis = [
        r
        for r in caplog.records
        if r.name == "agent.http.deps" and getattr(r, LOG_EXTRA_EVENT, None) == OPENEMR_MISCONFIGURATION
    ]
    assert mis and getattr(mis[0], "client_request_id") == "unit-req-7"
